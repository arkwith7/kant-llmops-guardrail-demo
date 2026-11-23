# Part 2 · Private LLM 서빙 실습 (노트북 RTX 5090)

| 학습 목표 | 실습 | 명령 | GPU |
|---|---|---|---|
| 서빙 병목은 어디서? | KV 캐시 계산기 | `python part2/kv_cache_calc.py` | 불필요 |
| | 동시 요청 벤치마크 | `python part2/bench_serving.py --levels 1,2,4,8` | 필요 |
| PagedAttention 은 왜 중요? | 메모리 할당 시뮬레이터 | `python part2/paged_attention_sim.py` | 불필요 |
| | vLLM 실시간 KV 캐시 지표 | `python part2/vllm_metrics.py --url http://<vLLM>:8000` | vLLM 서버 |
| 양자화·배포 전략 선택 기준 | 정밀도별 비교 | `python part2/quant_compare.py` | 필요 |

## 준비 (강의 전날)

```bash
ollama pull llama3.2:3b-instruct-fp16
ollama pull llama3.2:3b-instruct-q8_0
ollama pull llama3.2:3b-instruct-q4_K_M
```

## 시연 순서 (15분 교안 기준)

1. `kv_cache_calc.py` — 8B 모델 + 8K 문장 1건 = KV 캐시 1GB, 24GB GPU 에 최대 길이로 예약하면 동시 5건뿐
2. `paged_attention_sim.py` — 같은 공간에서 블록 단위로 잡으면 3배 이상 동시 처리
3. `bench_serving.py` — Ollama 는 동시 요청이 늘면 첫 토큰 시간이 늘어남 (대기열)
   vLLM(AWS g6 또는 Blackwell 지원 이미지)으로 같은 명령을 돌리면 총 처리량이 늘어남 → 연속 배칭 + PagedAttention
4. `quant_compare.py` — 16비트 → 8비트 → 4비트: 메모리·속도·답변 비교

## vLLM 으로 측정하기

```bash
# 노트북 (Blackwell 지원 이미지일 때) 또는 Part 1 의 AWS g6 인스턴스
docker compose -f part1/docker/compose.vllm.yaml up -d
python part2/vllm_metrics.py --url http://localhost:8000            # 터미널 A
python part2/bench_serving.py --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen2.5-1.5B-Instruct --levels 1,4,16,32             # 터미널 B
```

결과는 `logs/bench_serving.jsonl` 에 쌓여 Ollama 와 vLLM 을 나란히 비교할 수 있습니다.
