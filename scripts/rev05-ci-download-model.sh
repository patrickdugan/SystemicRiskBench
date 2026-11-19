#!/usr/bin/env bash
set -euo pipefail
: "${REV05_TMP:=/tmp/srb-rev05}"
base="$REV05_TMP/models/Bonsai-8B-Q1_0.gguf"
lora="$REV05_TMP/models/bitagent-bonsai8b-dagv2-lora-v3-f16.gguf"
curl -fL --retry 4 --retry-all-errors --connect-timeout 30 --max-time 900 "https://huggingface.co/prism-ml/Bonsai-8B-gguf/resolve/48516770dd04643643e9f9019a2a349cf26c5dbd/Bonsai-8B-Q1_0.gguf" -o "$base"
curl -fL --retry 4 --retry-all-errors --connect-timeout 30 --max-time 480 "https://huggingface.co/AlephFunk/bitagent-bonsai8b-dagv2-lora-v3/resolve/ee2937fb58d87bbd155cd205c43dc8103b51eac2/bitagent-bonsai8b-dagv2-lora-v3-f16.gguf" -o "$lora"
python - <<'PY'
import json,os
from adapters.artifacts import verify_file
spec=json.load(open('configs/rev05-cpu-ci-pilot.json'))
root=os.environ.get('REV05_TMP','/tmp/srb-rev05')+'/models/'
for k,name in [('base','Bonsai-8B-Q1_0.gguf'),('adapter','bitagent-bonsai8b-dagv2-lora-v3-f16.gguf')]:
    reg=spec['model'][k]
    v=verify_file(root+name,reg['sha256'],reg['bytes'])
    print('PASS:',k,'bytes',v['bytes'],'sha256',v['sha256'])
PY
