# Standalone repository and active jobs

The benchmark was initially implemented under
`patrickdugan/BitAgent/apps/systemic-risk-bench` and is now maintained at
`patrickdugan/SystemicRiskBench`. The standalone export includes the source,
33 historical episodes, four synthetic controls, numerical fixtures, initial
90-call model results, webhook runner and compact-adapter queue. The destination
repository's existing MIT license is preserved.

The already-running signed-plan historical process keeps its original working
directory and frozen source. Moving or replacing that directory during the
campaign would interfere with its source/provenance checks. On this workstation
its artifacts remain in the sibling checkout:

```powershell
python scripts/campaign_status.py ../BitAgent/apps/systemic-risk-bench/artifacts/history-baseline-v1
```

The repaired BitAgent waiter and the next 80-call local-model campaign run from
this standalone checkout. Their input plans are the existing frozen numerical
and historical plans in that sibling artifact directory; the packets are reused
without changing questions, evidence cutoffs or response schemas.

The waiter has a hard not-before time of 2026-11-16 07:35:22 UTC
(15:35:22 Asia/Singapore), followed by free-VRAM and active-compute checks. It
never terminates foreign GPU jobs. Current GPU-wait state is written to
`artifacts/bitagent-dagv3-v1/gpu-wait-status.json`; an append-only `.jsonl`
journal preserves state if Windows temporarily locks the JSON pointer.

Large model weights, local configuration, active receipts and server logs stay
under ignored artifact/work directories. Distilled completed benchmark results
belong in `results/`. The initial numerical results are already committed there;
ongoing historical/local campaigns must not be represented as completed runs.
