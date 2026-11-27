# Part 2 · Private LLM 서빙 실습 (노트북 RTX 5090)

## 비교 장표

- [Ollama와 Kubernetes vLLM 비교 PDF](Ollama_vs_Kubernetes_vLLM_비교.pdf) · [편집용 PPTX](Ollama_vs_Kubernetes_vLLM_비교.pptx)
- [장표 생성 스크립트](make_ollama_vllm_slides.js) · [vLLM 단독 스모크 결과](ollama-vllm-smoke-result.json)

장표에는 동일 Qwen3 GGUF 소규모 비교 결과가 포함되어 있습니다. [실험 결과와 한계](qwen3-비교-실험결과.md)를 함께 확인하세요. 장표 재생성에는 Node.js, `pptxgenjs` 4.0.1, PDF 변환에는 LibreOffice가 필요합니다.

Gemma 3 27B의 Ollama Q4_K_M과 Kubernetes vLLM GPTQ 비교는 [Gemma 실험 결과](gemma3-비교-실험결과.md)를 참고하세요.

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
3. `bench_serving.py` — Ollama 와 로컬 Docker 또는 Kubernetes vLLM의 동시 요청·첫 토큰 시간·처리량 비교
4. `quant_compare.py` — 16비트 → 8비트 → 4비트: 메모리·속도·답변 비교

## vLLM 으로 측정하기

```bash
# 노트북: Part 1의 Docker vLLM 또는 Kubernetes 포트 포워딩
docker compose -f part1/docker/compose.vllm.yaml up -d
python part2/vllm_metrics.py --url http://localhost:8000            # 터미널 A
python part2/bench_serving.py --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen2.5-1.5B-Instruct --levels 1,4,16,32             # 터미널 B
```

결과는 `logs/bench_serving.jsonl` 에 쌓여 Ollama 와 vLLM 을 나란히 비교할 수 있습니다. Kubernetes GPU 설정과 Docker 전환 방법은 [Part 1 안내](../part1/README.md)를 참고하세요. 같은 GPU에서 두 서버를 동시에 실행하지 마세요. 비교할 때는 같은 모델·입력·출력 길이·동시성 설정을 사용해야 합니다.
