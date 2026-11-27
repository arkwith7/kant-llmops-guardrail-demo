# Qwen3 30B: Ollama와 Kubernetes vLLM 비교

## 결론

동일한 Q4_K_M GGUF로 이 장비에서 시험한 결과, 동시 1건은 Ollama가 빠르고 동시 8건의 총 처리량은 vLLM이 높았다. 다만 단일 질문 반복, 실험용 GGUF 플러그인 패치, 서로 다른 엔진 설정의 소규모 결과이며 일반적인 제품 성능 순위가 아니다.

## 조건

- 2026-11-27, WSL2, NVIDIA RTX 5090 Laptop GPU 24,463 MiB. GPU 하나를 순차 사용.
- 모델: `qwen3:30b-a3b-instruct-2507-q4_K_M`, 18,556,685,856바이트. Ollama 원본과 Minikube 복사본은 `cmp`로 바이트 동일 확인. 원본 레이어 SHA-256: `78b329e716e7e9775973d392cd132b1f1ff1c8287a992887caeb6fd6c56ba9cc`.
- Ollama 0.13.5: 원본 가중치를 참조하는 `kant-qwen3-compare`, 컨텍스트 2,048, 100% GPU. 서비스에 `OLLAMA_NUM_PARALLEL` 별도 지정 없음.
- Kubernetes vLLM 0.34.0: Minikube 단일 GPU Pod, GGUF 플러그인 0.0.5 및 Qwen3 MoE 가중치 이름 호환성 실험 패치, `--max-model-len 2048`, `--max-num-seqs 8`, `--gpu-memory-utilization 0.90`, `--enforce-eager`. 기본 모델의 Hugging Face 토크나이저·설정 사용.
- 같은 질문, temperature 0, 출력 상한 64토큰, 예열 후 동시 수별 10배 요청. 개별 요청으로 볼 때 표본 수는 각각 10·20·40·80개. 양 서버 모두 응답별 usage 토큰 수를 제공했다.
- GPU 메모리 스냅샷: Ollama 적재 직후 18,553 MiB, vLLM 준비 후 22,228 MiB. 시스템 전체 사용량이며 최대값이나 동일 시점의 메모리 부하 측정은 아니다.

## 성능

TTFT는 요청 시작부터 첫 텍스트까지의 시간이다. p95는 해당 요청 표본의 nearest-rank 값이다. 동시 1의 p95는 10개 표본뿐이다.

| 동시 요청 | 요청 성공: Ollama / vLLM | TTFT p50 초: Ollama / vLLM | TTFT p95 초: Ollama / vLLM | 총 출력 tok/s: Ollama / vLLM |
|---:|---:|---:|---:|---:|
| 1 | 10/10 / 10/10 | 0.055 / 0.114 | 0.059 / 0.128 | 110.9 / 26.7 |
| 2 | 20/20 / 20/20 | 0.546 / 0.132 | 0.566 / 0.215 | 118.1 / 48.9 |
| 4 | 40/40 / 40/40 | 1.628 / 0.247 | 1.647 / 7.212 | 118.4 / 76.0 |
| 8 | 80/80 / 80/80 | 3.824 / 0.434 | 3.862 / 0.459 | 117.4 / 177.2 |

동시 8의 vLLM 총 처리량은 약 1.51배이고, 사용자별 생성 속도 중앙값은 Ollama 119.3, vLLM 26.1 tok/s였다. 사용자는 총 처리량과 별도로 개별 생성 속도를 체감한다. 동시 4의 vLLM p95가 7.212초로 튄 원인은 확인되지 않았으며 재측정이 필요하다.

두 엔진은 스케줄링, 병렬 설정, 캐시, GGUF 커널과 실행 모드가 다르다. 특히 vLLM의 GGUF 지원은 실험적이며 `--enforce-eager`를 사용했다. 동일 질문 반복으로 캐시 영향이 발생할 수 있다. 실제 동시 사용자나 다양한 입력 분포를 재현한 결과가 아니다.

## 품질

동일 시스템 메시지와 temperature 0으로 지식·계산·SQL·근거·JSON 형식 5건을 시험했다. 4건은 텍스트가 같았고 계산 응답은 표현만 다르며 양쪽 모두 51,000원을 제시했다. 입력 토큰 수는 다섯 건 각각 일치했다. 5건은 사람이 확인한 소규모 예시로, 업무 정확도나 안전성 우열을 보장하지 않는다.

## 가용성 및 다음 단계

Qwen3 모델 파일·이미지가 이미 캐시된 상태에서 실험 Pod를 0개에서 1개로 올렸을 때, Kubernetes가 기록한 Pod 생성부터 Ready까지 159초가 걸렸다. 해당 Pod를 강제 삭제하자 새 Pod가 생성돼 삭제 요청 시각부터 Ready까지 145초가 걸렸고 이후 실제 추론에서 `서울` 응답을 확인했다. 둘 다 각 1회이며, Ready 시각 기준으로 실제 외부 요청의 중단 구간을 연속 측정한 값은 아니다.

Ollama는 모델을 내린 상태에서 예열 요청을 보냈을 때 모델 로딩 9.82초, 요청 완료 10.54초였다. Pod 생성·Ready와 측정 범위가 다르므로 위 수치와 동등한 복구 시간 비교는 아니다. Ollama 프로세스 장애 복구와 GPU·노드 장애는 시험하지 않았다.

현재 Minikube 노트북 1대·GPU 1장·Pod 1개는 고가용성이 아니다. Qwen3 실험 Pod를 0개로 내리고 기존 Qwen2.5 1.5B 서버와 8000번 API를 복구했다. 2026-11-27에 Minikube의 실험용 모델 복사본 두 개를 삭제해 약 37.1GB를 확보했다. Ollama 원본은 유지했으며, 실험을 다시 실행하려면 모델을 노드에 다시 전달해야 한다.

재시험 시 서로 다른 입력 길이·출력 길이·부하 패턴을 사용하고, 각 조건을 여러 번 반복해 p95와 이상치를 확인한다. Ollama 병렬 설정을 명시적으로 바꾼 결과는 기본 설정과 별도로 표시하고, vLLM의 최적화된 비GGUF 양자화 실험은 다른 가중치이므로 별도 비교로 기록한다.

## 원자료

- [Ollama 요청별 결과](qwen3-ollama-benchmark.ndjson) · [vLLM 요청별 결과](qwen3-vllm-benchmark.ndjson)
- [Ollama 품질 응답](qwen3-ollama-quality.json) · [vLLM 품질 응답](qwen3-vllm-quality.json)
- [Kubernetes 가용성 실험 기록](qwen3-availability.json)
- [성능 측정 코드](bench_serving.py) · [품질 측정 코드](eval_qwen3_quality.py)
- [실험용 Kubernetes 매니페스트](../part1/k8s/vllm-qwen3-compare.yaml) · [실험용 이미지](../part1/docker/Dockerfile.vllm-gguf)