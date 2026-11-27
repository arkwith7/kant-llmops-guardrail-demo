# Gemma 3 27B: Ollama와 Kubernetes vLLM 비교

## 조건

- GPU: NVIDIA RTX 5090 Laptop, 24,463 MiB. 두 서버는 동일 GPU에서 순차 실행했다.
- Ollama: `gemma3:27b`의 Gemma 3 27B Instruct, GGUF Q4_K_M. 측정에는 원본을 참조하는 임시 태그를 사용했다.
- Kubernetes vLLM: `ISTA-DASLab/gemma-3-27b-it-GPTQ-4b-128g`, GPTQ 4비트, revision `9c5f61a23e1ccf3921173c2b32f6ff0af1bffd1b`. vLLM 0.34.0에 Protobuf 7.36.1을 적용했다.
- 같은 Gemma 3 27B Instruct 계열이지만 양자화와 실행 환경이 다르므로 수치 차이를 엔진만의 효과로 볼 수 없다. vLLM은 `--language-model-only`로 실행했으며 이미지 입력은 시험하지 않았다.
- 문맥 길이 2,048, 출력 최대 64토큰, temperature 0, 동일 한국어 프롬프트, 사전 예열 1회. 동시성별로 동시 요청 수의 10배를 전송했다. 매 요청에 같은 프롬프트를 반복하므로 프롬프트 캐시가 결과에 영향을 줄 수 있다.
- vLLM 실행 시 GPU 사용량은 19,134 MiB로 관찰했다. 이는 한 시점의 값이며 최대 사용량이 아니다. Ollama 동시 실행 설정과 최대 GPU 메모리 사용량은 이 기록에서 확인되지 않았다.

## 성능

TTFT는 첫 텍스트 응답까지의 시간이다. 처리량은 측정 구간 전체의 완료 토큰 수를 경과 시간으로 나눈 값이다.

| 동시 요청 | 요청 성공 Ollama / vLLM | TTFT p50 Ollama / vLLM (초) | TTFT p95 Ollama / vLLM (초) | 처리량 Ollama / vLLM (토큰/초) |
|---:|---:|---:|---:|---:|
| 1 | 10/10 / 10/10 | 0.158 / 0.066 | 0.176 / 0.093 | 24.7 / 27.9 |
| 2 | 20/20 / 20/20 | 2.558 / 0.104 | 2.575 / 0.117 | 25.4 / 54.6 |
| 4 | 40/40 / 40/40 | 7.640 / 0.177 | 7.688 / 0.181 | 25.2 / 104.9 |
| 8 | 80/80 / 80/80 | 17.234 / 0.292 | 17.779 / 0.302 | 25.8 / 194.8 |

이번 조건에서 동시 8 요청의 vLLM 처리량은 Ollama의 약 7.6배였다. Ollama의 동시 처리 설정을 확인하지 못했으므로 이를 Ollama 일반의 성능으로 해석해서는 안 된다. 특히 동시 1의 p95는 표본 10건에 불과하다. 별도의 장애 복구 및 장시간 가용성 시험은 하지 않았다.

## 품질

동일한 다섯 질문에서 양쪽 모두 수도, 산술, 근거 부족에 적절하게 답했다. SQL은 양쪽 모두 `month = '10월'`을 생성했으므로 실제 열 타입과 저장 형식에 맞는지는 확인이 필요하다. JSON 배열 요청에는 양쪽 모두 올바른 배열을 마크다운 코드 펜스로 감싸서 응답했으므로 엄격한 JSON 전용 출력 조건에는 실패했다. 다섯 사례만으로 일반적인 품질이나 양자화에 따른 품질 우열은 판단할 수 없다. 원본 JSON의 `ok`는 요청 성공 여부이며 정답 판정이 아니다.

## 원본

- [Ollama 성능 기록](gemma3-ollama-benchmark.ndjson) · [vLLM 성능 기록](gemma3-vllm-benchmark.ndjson)
- [Ollama 품질 응답](gemma3-ollama-quality.json) · [vLLM 품질 응답](gemma3-vllm-quality.json)
- [vLLM 실험 Deployment](../part1/k8s/vllm-gemma3-compare.yaml) · [이미지 정의](../part1/docker/Dockerfile.vllm-gemma3)