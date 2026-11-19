"""Stage-isolated ephemeral llama-server lifecycle for bounded-memory runs.

Starts a fresh local llama-server OS process on an unused loopback port for a
single benchmark stage, binds it to a kill-on-close OS job/session so cleanup
survives parent timeouts, and verifies process exit and socket closure before
returning stage telemetry.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from .artifacts import verify_file
from .llamacpp import check_gpu_window
from systemic_risk_bench.scoring import loads_json

_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _bind_kill_on_close_job(process_handle: int):
    """Attach a Windows child process to a Job Object that kills on handle close."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = kernel32.SetInformationJobObject(
        job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(info), ctypes.sizeof(info),
    )
    if not ok or not kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(process_handle)):
        err = ctypes.get_last_error()
        kernel32.CloseHandle(job)
        raise OSError(err, "failed to bind llama-server to kill-on-close job")
    return job, kernel32.CloseHandle


def _port_accepting_connections(port: int, timeout: float = 0.25) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(timeout)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _reserve_unused_loopback_port() -> int:
    for _ in range(8):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        if not _port_accepting_connections(port, timeout=0.1):
            return port
    raise RuntimeError("could not allocate an unused loopback port")


def check_free_vram(minimum_free_mib: int) -> int:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, encoding="utf-8", timeout=15, shell=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("cannot verify free GPU VRAM via nvidia-smi")
    first_line = result.stdout.strip().splitlines()[0].strip()
    free_mib = int(first_line)
    if free_mib < minimum_free_mib:
        raise RuntimeError(
            f"GPU free VRAM {free_mib} MiB is below registered minimum {minimum_free_mib} MiB"
        )
    return free_mib


def build_server_argv(config: dict, port: int) -> list[str]:
    return [
        str(Path(config["server_exe"]).resolve()),
        "--host", "127.0.0.1",
        "--port", str(port),
        "-m", str(Path(config["base"]["path"]).resolve()),
        "--lora", str(Path(config["adapter"]["path"]).resolve()),
        "--alias", config["model_alias"],
        "-c", str(config.get("context", 8192)),
        "-np", "1",
        "--device", config.get("device", "CUDA0"),
        "-ngl", str(config.get("n_gpu_layers", 99)),
        "-t", str(config.get("threads", 4)),
        "-tb", str(config.get("threads_batch", 4)),
        "-b", str(config.get("batch_size", 128)),
        "-ub", str(config.get("ubatch_size", 64)),
        "-ctk", config.get("cache_type_k", "q8_0"),
        "-ctv", config.get("cache_type_v", "q8_0"),
        "-fa", config.get("flash_attn", "on"),
        "--no-webui",
    ]


class EphemeralLlamaCppSession:
    """Manage one fresh llama-server OS process for a single stage request."""

    def __init__(self, config: dict, *, verify: bool = True, clock=None,
                 opener=urlopen, popen=subprocess.Popen, vram_checker=check_free_vram):
        self.config = config
        self.verify = verify
        self.clock = clock
        self.opener = opener
        self.popen = popen
        self.vram_checker = vram_checker
        self.port: int | None = None
        self.endpoint: str | None = None
        self.server_boot_sha256: str | None = None
        self.startup_seconds: float | None = None
        self.shutdown_seconds: float | None = None
        self.process_reaped: bool = False
        self.port_closed_verified: bool = False
        self._proc = None
        self._job_handle = None
        self._close_job = None
        self._tempdir = None
        self._stdout_file = None
        self._stderr_file = None

    def __enter__(self):
        check_gpu_window(self.config, self.clock() if self.clock else None)
        if self.verify:
            verify_file(self.config["server_exe"], self.config["server_sha256"],
                        self.config.get("server_bytes"))
            for name in ("base", "adapter"):
                artifact = self.config[name]
                verify_file(artifact["path"], artifact["sha256"], artifact["bytes"])
            min_vram = self.config.get("minimum_free_vram_mib")
            if min_vram is not None:
                self.vram_checker(int(min_vram))

        self.port = _reserve_unused_loopback_port()
        self.endpoint = f"http://127.0.0.1:{self.port}/v1"
        self._tempdir = tempfile.TemporaryDirectory(prefix="srb_stage_srv_")
        workdir = Path(self._tempdir.name)
        if any(workdir.iterdir()):
            raise RuntimeError("ephemeral stage working directory was not empty")
        stdout_path = workdir / "server.stdout.log"
        stderr_path = workdir / "server.stderr.log"
        self._stdout_file = stdout_path.open("w+", encoding="utf-8")
        self._stderr_file = stderr_path.open("w+", encoding="utf-8")

        argv = build_server_argv(self.config, self.port)
        if "--slot-save-path" in argv:
            raise ValueError("ephemeral per-stage server forbids slot persistence")

        popen_kwargs = {
            "cwd": str(workdir),
            "stdout": self._stdout_file,
            "stderr": self._stderr_file,
            "stdin": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            popen_kwargs["start_new_session"] = True

        started_perf = time.perf_counter()
        started_ns = time.monotonic_ns()
        try:
            self._proc = self.popen(argv, **popen_kwargs)
            if sys.platform == "win32" and hasattr(self._proc, "_handle"):
                self._job_handle, self._close_job = _bind_kill_on_close_job(
                    int(self._proc._handle))
            nonce = os.urandom(16).hex()
            boot_material = f"{self._proc.pid}:{self.port}:{started_ns}:{nonce}".encode("ascii")
            self.server_boot_sha256 = hashlib.sha256(boot_material).hexdigest()
            self._wait_until_healthy(started_perf)
            self.startup_seconds = time.perf_counter() - started_perf
            return self
        except Exception:
            self.close()
            raise

    def _wait_until_healthy(self, started_perf: float) -> None:
        startup_limit = float(self.config.get("startup_timeout_seconds", 120))
        health_url = f"http://127.0.0.1:{self.port}/health"
        while True:
            if self._proc.poll() is not None:
                raise RuntimeError("ephemeral llama-server exited before becoming healthy")
            if time.perf_counter() - started_perf > startup_limit:
                raise TimeoutError("ephemeral llama-server startup exceeded timeout")
            try:
                with self.opener(health_url, timeout=1.0) as response:
                    payload = loads_json(response.read().decode("utf-8"))
                    if isinstance(payload, dict) and payload.get("status") == "ok":
                        return
            except Exception:
                time.sleep(0.1)

    def close(self) -> None:
        stop_started = time.perf_counter()
        proc = self._proc
        self._proc = None
        try:
            if proc is not None:
                if proc.poll() is None:
                    try:
                        if sys.platform != "win32" and hasattr(os, "killpg"):
                            os.killpg(proc.pid, signal.SIGTERM)
                        else:
                            proc.terminate()
                    except OSError:
                        pass
                    try:
                        proc.wait(timeout=3.0)
                    except subprocess.TimeoutExpired:
                        try:
                            if sys.platform != "win32" and hasattr(os, "killpg"):
                                os.killpg(proc.pid, signal.SIGKILL)
                            else:
                                proc.kill()
                        except OSError:
                            pass
                        proc.wait(timeout=5.0)
                self.process_reaped = proc.poll() is not None
        finally:
            if self._job_handle is not None and self._close_job is not None:
                try:
                    self._close_job(self._job_handle)
                finally:
                    self._job_handle = None
                    self._close_job = None
            for handle in (self._stdout_file, self._stderr_file):
                if handle is not None:
                    try:
                        handle.close()
                    except OSError:
                        pass
            self._stdout_file = None
            self._stderr_file = None
            if self._tempdir is not None:
                try:
                    self._tempdir.cleanup()
                except OSError:
                    pass
                self._tempdir = None
            if self.port is not None:
                for _ in range(20):
                    if not _port_accepting_connections(self.port, timeout=0.1):
                        self.port_closed_verified = True
                        break
                    time.sleep(0.05)
            self.shutdown_seconds = time.perf_counter() - stop_started

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
