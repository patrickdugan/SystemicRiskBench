"""SRB-REV-01: information-matched evidence-revision eval for JSON adapters.

Public synthetic development-only 12-slot, six-revision ECA-style environment.
Two bounded *declared* memory codecs, each validated against the initial public
history. Adapter processes are operator-trusted and NOT sandboxed. Model roots,
token usage, physical memory and source authenticity remain external.

The goal is to test state update under a later evidence correction. No agent
actions, wallets, trades, authorization gates or independent model roots.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
from hashlib import sha256
import hashlib
import hmac
import json
import math
from math import comb
import random

from .runner import execute, sha as canonical_sha

SCHEMA = "srb.agent_revision.v1"
DOMAIN = "srb-agent-revision/public-development-v1"
N, J = 12, 6
PRIORS = (Q(9, 20), Q(7, 20), Q(1, 5))
MATCH = (Q(19, 20), Q(13, 20), Q(3, 20))
MODES = ("count", "bitmap")
MAX_CASES = 256


def _integer(value: int, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("out-of-range integer or boolean masquerading as an integer")


def _weights_to_posterior(weights) -> tuple[Q, Q, Q]:
    denominator = sum(weights, Q(0))
    if denominator <= 0:
        raise ValueError("zero-probability observation")
    return tuple(weight / denominator for weight in weights)


def _binomial(n: int, x: int, p: Q) -> Q:
    return Q(0) if x < 0 or x > n else Q(comb(n, x)) * p**x * (1-p)**(n-x)


def valid_posterior(matches: int, n: int=N) -> tuple[Q, Q, Q]:
    _integer(n, 1, N)
    _integer(matches, 0, n)
    return _weights_to_posterior(
        prior * p**matches * (1-p)**(n-matches)
        for prior, p in zip(PRIORS, MATCH)
    )


def initial_posterior(old_count: int) -> tuple[Q, Q, Q]:
    """The schedule is hidden and uniform before the first stage."""
    _integer(old_count, 0, N)
    return _weights_to_posterior(
        prior * sum((_binomial(N-J, u, p) *
                     _binomial(J, old_count-u, Q(1, 2))
                     for u in range(N-J+1)), Q(0))
        for prior, p in zip(PRIORS, MATCH)
    )


def count_posterior(old_count: int, new_count: int) -> tuple[Q, Q, Q]:
    """Optimal FINAL posterior when all the prior state retained was sum(old).

    The six provisional bits in corrected positions were iid fair. Accepted
    replacements and uncorrected old reports are regime-dependent.
    """
    _integer(old_count, 0, N)
    _integer(new_count, 0, J)
    return _weights_to_posterior(
        prior * _binomial(J, new_count, p) *
        sum((_binomial(N-J, u, p) * _binomial(J, old_count-u, Q(1, 2))
             for u in range(N-J+1)), Q(0))
        for prior, p in zip(PRIORS, MATCH)
    )


def bitmap_posterior(old_mask: int, corrections: tuple[tuple[int, int], ...]) -> tuple[Q, Q, Q]:
    _integer(old_mask, 0, (1 << N)-1)
    if (type(corrections) is not tuple or len(corrections) != J or
            any(type(s) is not tuple or len(s) != 2 or
                type(s[0]) is not int or type(s[1]) is not int or
                not 0 <= s[0] < N or s[1] not in (0, 1)
                for s in corrections)):
        raise ValueError("exactly six canonical corrected slots required")
    slots = [slot for slot, _ in corrections]
    if slots != sorted(set(slots)):
        raise ValueError("slots must be distinct and ascending")
    mask = old_mask
    for slot, new in corrections:
        mask = (mask & ~(1 << slot)) | (new << slot)
    return valid_posterior(mask.bit_count())


def _root_seed(index: int) -> bytes:
    _integer(index, 0, MAX_CASES-1)
    return sha256(f"{DOMAIN}/{index}".encode()).digest()


@dataclass(frozen=True)
class Fixture:
    """Private host fixture, never included verbatim in an agent packet."""
    case_id: str
    regime: int
    old: tuple[int, ...]
    slots: tuple[int, ...]
    replacements: tuple[int, ...]
    host_key: bytes

    @property
    def old_count(self) -> int:
        return sum(self.old)

    @property
    def old_mask(self) -> int:
        return sum(value << i for i, value in enumerate(self.old))

    @property
    def accepted_count(self) -> int:
        return sum(self.old[i] for i in range(N) if i not in self.slots) + sum(self.replacements)

    @property
    def exact_full(self) -> tuple[Q, Q, Q]:
        return valid_posterior(self.accepted_count)

    @property
    def exact_count(self) -> tuple[Q, Q, Q]:
        return count_posterior(self.old_count, sum(self.replacements))


def fixture(index: int) -> Fixture:
    seed = _root_seed(index)
    rng = random.Random(int.from_bytes(seed, "big"))
    regime_roll = rng.randrange(20)
    regime = 0 if regime_roll < 9 else 1 if regime_roll < 16 else 2
    schedule_rng = random.Random(int.from_bytes(sha256(seed+b"/schedule").digest(), "big"))
    slots = tuple(sorted(schedule_rng.sample(range(N), J)))
    old = tuple(rng.randrange(2) if i in slots else
                int(rng.randrange(20) < int(MATCH[regime]*20)) for i in range(N))
    replacements = tuple(int(rng.randrange(20) < int(MATCH[regime]*20)) for _ in slots)
    return Fixture(seed.hex(), regime, old, slots, replacements,
                   sha256(seed + b"/host-only-synthetic-key").digest())


def _event_body(case_id: str, slot: int, new_match: int) -> bytes:
    return json.dumps({"case_id":case_id,"slot":slot,"old_version":0,
                       "new_version":1,"new_match":new_match},
                      separators=(",", ":"), sort_keys=True).encode()


def signed_events(world: Fixture) -> list[dict]:
    return [{
        "slot": slot, "new_match": bit, "old_version": 0, "new_version": 1,
        "synthetic_receipt_hmac": hmac.new(
            world.host_key, _event_body(world.case_id, slot, bit), sha256).hexdigest()
    } for slot, bit in zip(world.slots, world.replacements)]


def verify_events(world: Fixture, events: list[dict]) -> bool:
    """Host-only verification; a public deterministic key is not real authority."""
    if type(events) is not list or len(events) != J:
        return False
    for expected_slot, expected_bit, event in zip(world.slots, world.replacements, events):
        if (type(event) is not dict or
                set(event) != {"slot","new_match","old_version","new_version",
                               "synthetic_receipt_hmac"} or
                type(event["slot"]) is not int or
                type(event["new_match"]) is not int or
                event["slot"] != expected_slot or event["new_match"] != expected_bit or
                type(event["old_version"]) is not int or
                type(event["new_version"]) is not int or
                event["old_version"] != 0 or event["new_version"] != 1 or
                type(event["synthetic_receipt_hmac"]) is not str):
            return False
        sig = hmac.new(world.host_key,
                       _event_body(world.case_id, expected_slot, expected_bit),
                       sha256).hexdigest()
        if not hmac.compare_digest(event["synthetic_receipt_hmac"], sig):
            return False
    return True


def initial_packet(world: Fixture, mode: str) -> dict:
    if mode not in MODES:
        raise ValueError("unknown memory codec")
    return {
        "schema": SCHEMA, "phase": "initial", "case_id": world.case_id,
        "memory_codec": mode, "memory_contract":
            "Return integer sum(old) 0..12" if mode=="count" else
            "Return integer sum(old[slot] << slot) 0..4095",
        "memory_max": N if mode=="count" else (1 << N)-1,
        "old": [{"slot":i,"match":bit} for i,bit in enumerate(world.old)],
        "correction_schedule": "hidden_until_update",
        "known_correction_count": J,
        "likelihood": {
            "priors": [[9,20],[7,20],[1,5]],
            "match_probabilities": [[19,20],[13,20],[3,20]],
            "provisional_model": "six hidden slots have iid fair old bits"
        },
        "reply_contract": {"memory":"bounded integer","posterior":"three normalized probabilities"},
        "authority": "synthetic_read_only_eval_no_action",
    }


def update_packet(world: Fixture, mode: str, memory: int) -> dict:
    if mode not in MODES:
        raise ValueError("unknown memory codec")
    events=signed_events(world)
    if not verify_events(world, events):
        raise AssertionError("host evidence integrity failure")
    return {
        "schema": SCHEMA, "phase": "update", "case_id": world.case_id,
        "memory_codec": mode, "memory": memory, "old": "not_replayed",
        "prior_responses": "not_replayed", "corrections": events,
        "known_correction_count": J,
        "likelihood": {
            "priors": [[9,20],[7,20],[1,5]],
            "match_probabilities": [[19,20],[13,20],[3,20]],
            "provisional_model": "six corrected old bits were iid fair"
        },
        "reply_contract": {"posterior":"three normalized probabilities"},
        "authority": "synthetic_read_only_eval_no_action",
    }


def parse_forecast(response: dict, phase: str) -> tuple[float, float, float]:
    if type(response) is not dict:
        raise ValueError("adapter response must be an object")
    expected={"posterior","memory"} if phase=="initial" else {"posterior"}
    if set(response) != expected:
        raise ValueError("unexpected agent response fields or missing forecast")
    values=response["posterior"]
    if (type(values) is not list or len(values)!=3 or
            any(type(x) not in (float,int) or not math.isfinite(x) or
                not 0<=x<=1 for x in values) or
            abs(math.fsum(values)-1)>1e-6):
        raise ValueError("posterior must be finite normalized 3-class distribution")
    return tuple(float(x) for x in values)


def validate_memory(response: dict, world: Fixture, mode: str) -> int:
    parse_forecast(response, "initial")
    memory=response["memory"]
    _integer(memory, 0, N if mode=="count" else (1 << N)-1)
    expected=world.old_count if mode=="count" else world.old_mask
    if memory != expected:
        raise ValueError("initial memory did not encode the declared old state")
    return memory


def squared(p, q) -> float:
    return math.fsum((float(a)-float(b))**2 for a,b in zip(p,q))


def run_agent_revision(adapter_argv: list[str], experiment: dict, *,
                       mode: str, cases: int=16, timeout: float=30) -> dict:
    """Two independent adapter subprocess calls per case.

    The executor intentionally sends NO prior responses at the update call.
    A model's persistent state is the explicitly reported bounded integer.
    Adapter code could nevertheless use out-of-band state; isolation requires
    an independent deployment boundary and is not certified by this harness.
    """
    _integer(cases,1,MAX_CASES)
    if mode not in MODES:
        raise ValueError("mode must be count or bitmap")
    if (type(experiment) is not dict or
            type(experiment.get("experiment_id")) is not str or
            not experiment["experiment_id"]):
        raise ValueError("experiment needs a nonempty experiment_id")
    if (type(timeout) not in (int,float) or
            not math.isfinite(timeout) or not 0 < timeout <= 3600):
        raise ValueError("timeout must be a positive finite number")
    rows=[]
    for index in range(cases):
        world=fixture(index)
        first_packet=initial_packet(world,mode)
        first=execute(adapter_argv,first_packet,[],timeout,experiment)
        initial_error=None
        memory=None
        if first["status"]=="ok":
            try:
                memory=validate_memory(first["response"],world,mode)
            except (ValueError,TypeError) as exc:
                initial_error=str(exc)
        else:
            initial_error=first["status"]
        row={
            "case_id":world.case_id,"index":index, "mode":mode,
            "initial_packet_sha256":canonical_sha(first_packet),
            "initial_status":first["status"],
            "initial_error":initial_error,
            "initial_receipt":first, "update_receipt":None,
            "status":"initial_invalid" if initial_error else "pending",
            "input_matched_reference":None,
            "forecast":None,"excess_brier":None,"sample_brier":None,
            "information_loss_sq":None,
        }
        if initial_error is None:
            later=update_packet(world,mode,memory)
            second=execute(adapter_argv,later,[],timeout,experiment)
            row["update_packet_sha256"]=canonical_sha(later)
            row["update_receipt"]=second
            if second["status"]=="ok":
                try:
                    forecast=parse_forecast(second["response"],"update")
                    reference=world.exact_count if mode=="count" else world.exact_full
                    row.update(forecast=list(forecast),
                               input_matched_reference=list(map(float,reference)),
                               excess_brier=squared(forecast,reference),
                               sample_brier=squared(forecast,
                                   tuple(int(k==world.regime) for k in range(3))),
                               information_loss_sq=squared(world.exact_count,world.exact_full),
                               status="scored")
                except (ValueError,TypeError) as exc:
                    row.update(status="invalid_forecast",update_error=str(exc))
            else:
                row["status"]="update_"+second["status"]
        rows.append(row)
    scored=[row for row in rows if row["status"]=="scored"]
    return {
        "schema":SCHEMA,"evidence_class":"public_deterministic_development_only",
        "model_evaluation_claim":True, "scientific_confirmation_claim":False,
        "physical_memory_enforced":False, "adapter_process_sandboxed":False,
        "authority":"read_only_no_execution",
        "experiment":experiment,"experiment_sha256":canonical_sha(experiment),
        "mode":mode,"n_cases":cases,"n_scored":len(scored),
        "coverage":len(scored)/cases,"model_calls_attempted":
            sum(1+(row["update_receipt"] is not None) for row in rows),
        "memory_logical_bits":4 if mode=="count" else 12,
        "mean_excess_brier_with_missing_penalty":
            sum(row["excess_brier"] if row["status"]=="scored" else 2.0
                for row in rows)/cases,
        "mean_sample_brier_with_missing_penalty":
            sum(row["sample_brier"] if row["status"]=="scored" else 2.0
                for row in rows)/cases,
        "mean_information_loss_sq_for_scored":
            (sum(row["information_loss_sq"] for row in scored)/len(scored)
             if scored else None),
        "private_regimes_excluded_from_packets":True,
        "initial_old_history_excluded_from_update_packets":True,
        "prior_responses_suppressed":True,
        "rows":rows,
    }
