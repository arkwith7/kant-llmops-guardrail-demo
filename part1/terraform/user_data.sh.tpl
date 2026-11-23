#!/bin/bash
# EC2 부팅 시 1회 실행 — vLLM 컨테이너 기동 (로그: /var/log/cloud-init-output.log)
set -euxo pipefail

# Docker 데몬 준비 대기
for i in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 5; done
nvidia-smi

mkdir -p /opt/hf-cache
docker pull ${vllm_image}
docker run -d --name vllm --restart unless-stopped \
  --gpus all --ipc=host -p 8000:8000 \
  -v /opt/hf-cache:/root/.cache/huggingface \
  ${vllm_image} \
  --model ${model} \
  --max-model-len ${max_model_len} \
  --gpu-memory-utilization 0.90
