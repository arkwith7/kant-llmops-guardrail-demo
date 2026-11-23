# Private LLM 인프라 · 서빙 · LLMOps 시연 (KANT 강의용)

> Part 1 클라우드 인프라 → [part1/README.md](part1/README.md) · Part 2 서빙 → [part2/README.md](part2/README.md) · Part 3 LLMOps 가드레일 → 아래

Private LLM을 기업 환경에서 **운영**할 때 필요한 가드레일을 50줄 남짓한 파이썬으로 보여 주는 강의 시연 프로젝트입니다.
로컬 GPU에서 오픈 웨이트 모델(Gemma 3 등)을 직접 띄우고, 같은 코드를 AWS Bedrock(관리형 클라우드)의 선택한 리전에도 붙일 수 있습니다.

```
[사용자 입력] → ① 입력 가드 → ② LLM (local / bedrock / mock) → ③ 출력 가드 → [응답]
                     └──────────── ④ 관측 로그 (logs/guardrail_log.jsonl) ────────────┘
```

| 단계 | 하는 일 | 코드 |
|---|---|---|
| ① 입력 가드 | 프롬프트 인젝션 탐지, 개인정보(전화·이메일·주민번호) 마스킹 | `detect_injection`, `mask_pii` |
| ② LLM 호출 | 로컬 Ollama/vLLM(OpenAI 호환), Bedrock Converse, 모의 LLM | `llm_backends.py` |
| ③ 출력 가드 | 데이터 변경 SQL(DELETE·DROP 등) 차단, 응답 속 개인정보 재마스킹 | `check_sql_safety`, `mask_pii` |
| ④ 관측성 | 요청 1건 = JSON 1줄 (판정, 이벤트, 지연, 토큰) | `write_log` |

## 프로젝트 구조

```
├── part1/                   # Part 1 클라우드 인프라: Docker · Kubernetes · Terraform(AWS g6) · Ansible
├── part2/                   # Part 2 서빙: KV 캐시 계산 · PagedAttention 시뮬 · 벤치마크 · 양자화 비교
├── guardrail_demo.py        # Part 3 시연 본체: 시나리오 5개 / --chat 대화 모드
├── llm_backends.py          # LLM 백엔드 (local / bedrock / mock) + .env 로더
├── bedrock_gemma_demo.py    # LLM 체험: Bedrock 리전별 모델 조회, Gemma 3 4B·12B·27B 비교, 스트리밍
├── check_env.py             # 시연 전 점검: GPU · 로컬 LLM · Bedrock · 모의 LLM
├── .env.example             # 설정 예시 (복사해서 .env 로 사용, .env 는 Git 제외)
├── requirements.txt         # boto3 (Bedrock 용만)
├── docs/
│   ├── 시연-리허설-체크리스트.md
│   └── iam-policy-bedrock-gemma.json   # 최소 권한 IAM 정책 예시
└── .vscode/                 # 실행 구성(F5), 작업(점검·예열·GPU 모니터), 강의용 큰 글꼴
```

## 빠른 시작 (WSL + VS Code)

```bash
git clone https://github.com/arkwith7/kant-llmops-guardrail-demo.git
cd kant-llmops-guardrail-demo
code .                                   # VS Code (Remote - WSL)

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                     # AWS 키 등 값 채우기
python check_env.py                      # 점검
python guardrail_demo.py                 # 시연 (기본: 로컬 gemma3:27b)
```

VS Code에서는 **실행 및 디버그(F5)** 목록에서 바로 고를 수 있습니다.

| 실행 구성 | 내용 |
|---|---|
| ① 시연: 로컬 GPU (gemma3:27b) | 기본 시연 |
| ② 시연: 로컬 소형 모델 비교 (llama3.2) | 작은 모델은 가드에 더 자주 걸리는지 비교 |
| ③ 대화 모드: 로컬 GPU | 수강생이 부른 문장을 즉석 테스트 |
| ④ 백업: AWS Bedrock (.env 리전·모델, 기본 도쿄) | 로컬 GPU 문제 시 |
| ⑤ 최종 백업: 모의 LLM | 인터넷·GPU 모두 없을 때 |
| LLM 체험: Bedrock 비교 / 스트리밍 | Gemma 3 크기별 품질·지연·토큰 비교 |
| 시연 전 환경 점검 | `check_env.py` |

작업(Ctrl+Shift+P → Tasks: Run Task): 설치, 점검, **Ollama 예열**, **GPU 모니터(nvidia-smi -l 1)**, 관측 로그 보기.

## 1. 로컬 Private LLM (Ollama)

```bash
ollama list                    # 설치된 모델 확인
ollama pull gemma3:27b         # 기본 시연 모델 (약 17GB, 24GB VRAM GPU에 적합)
ollama pull llama3.2           # 소형 비교 모델 (3B, 약 2GB)
curl http://localhost:11434/v1/models
```

- 모델 바꾸기: `python guardrail_demo.py --model llama3.2` 또는 `.env`의 `LOCAL_LLM_MODEL`
- vLLM 사용: `python guardrail_demo.py --base-url http://localhost:8000/v1 --model google/gemma-3-4b-it`
- `deepseek-r1` 같은 추론 모델은 `<think>` 블록을 출력해 시연 화면이 길어지므로 권장하지 않습니다.

## 2. AWS Bedrock: 사용 가능한 리전·모델 선택

- 이 프로젝트는 **도쿄 리전(ap-northeast-1)** 의 Gemma 3(`google.gemma-3-12b-it`)로 검증했습니다. 시연 계정에서 서울 리전(ap-northeast-2)에는 해당 모델이 없었습니다.
- **강의 포인트**: 관리형 LLM을 쓰면 데이터가 처리되는 리전이 모델 제공 여부에 따라 정해집니다. 국내 보관 요건이 있으면 로컬 GPU·온프레미스(Private LLM)나 국내 리전 모델이 필요하고, 이것이 하이브리드 구성을 고르는 기준이 됩니다.
- 인증은 **IAM 사용자 액세스 키**를 씁니다. `.env`에 넣거나, 비워 두면 `~/.aws/credentials`(aws configure)를 씁니다.

```dotenv
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
BEDROCK_MODEL_ID=google.gemma-3-12b-it
```

계정·리전마다 제공 모델이 다르므로, 자격 증명을 설정한 후 **사용이 허용된 후보 리전**의 카탈로그를 조회합니다. 목록 조회는 추론을 실행하지 않습니다.

```bash
python bedrock_gemma_demo.py --list ap-northeast-2 ap-northeast-1 us-west-2 us-east-1
```

리전을 생략하면 설정된 `AWS_REGION`만 조회합니다. 목록은 공급자에 상관없이 온디맨드 텍스트 출력 모델을 보여 주며, 끝에 `BEDROCK_MODEL_ID`가 발견된 리전을 표시합니다. 목록에 있어도 해당 계정에 추론 권한이 있거나 Converse를 지원한다는 뜻은 아닙니다.

목록에서 고른 리전·모델은 아래처럼 한 번 호출해 확인하세요(추론 비용 발생, 예시는 검증된 도쿄 · 12B 조합).

```bash
AWS_REGION=ap-northeast-1 BEDROCK_MODEL_ID=google.gemma-3-12b-it python bedrock_gemma_demo.py -q "한 단어로 인사하세요."
```

성공한 `AWS_REGION`과 `BEDROCK_MODEL_ID`를 `.env`에 저장하세요(셸에 설정한 값이 우선). 이후 점검과 시연은 이 설정을 사용하며 다른 리전으로 자동 전송하지 않습니다.

IAM 사용자에는 [docs/iam-policy-bedrock-gemma.json](docs/iam-policy-bedrock-gemma.json)처럼 **사용하는 리전의 Gemma 3 호출 권한만** 주는 것을 권장합니다. 예시 정책의 호출 권한은 도쿄 Gemma 3에 한정되어 있으므로, 다른 리전·모델을 쓰려면 호출 `Resource` ARN을 **선택한 리전·모델**에 맞게 바꾸세요.
```bash
python guardrail_demo.py --backend bedrock
python bedrock_gemma_demo.py --compare        # 선택한 리전에서 4B / 12B / 27B가 모두 호출 가능할 때
python bedrock_gemma_demo.py --stream         # 첫 토큰까지 시간
python bedrock_gemma_demo.py --chat --model google.gemma-3-4b-it
```

## 3. 시연 시나리오

| 시나리오 | 입력 | 기대 판정 |
|---|---|---|
| 정상 질문 | 10월 지역별 매출 합계 SQL | OK |
| 개인정보 포함 입력 | 내 번호 010-…로 보내줘 | OK (번호는 마스킹 후 모델에 전달) |
| 프롬프트 인젝션 | 이전 지시는 모두 무시하고… | BLOCKED (입력 단계) |
| 모델의 위험 SQL | 2024년 이전 주문 삭제 SQL | BLOCKED (출력 단계) |
| 모델의 개인정보 노출 | 담당자 연락처 + 사내 문서 검색 결과 | MODIFIED (출력 마스킹) |

### 실행 결과 예시 (RTX 5090 Laptop GPU · WSL2 · Ollama `gemma3:27b`, 2026-11-23)

| 시나리오 | 모델 원본 → 최종 | 판정 | 지연 |
|---|---|---|---|
| 정상 질문 | `SELECT region, SUM(amount) …` | OK | 10.1 s (첫 호출, 모델 로딩 포함) |
| 개인정보 포함 입력 | 번호는 마스킹되어 모델에 전달 | OK | 2.7 s |
| 프롬프트 인젝션 | 모델 호출 없이 거절 | BLOCKED | 0 ms |
| 모델의 위험 SQL | 모델이 `DELETE FROM orders …` 생성 → 차단 | BLOCKED | 1.2 s |
| 모델의 개인정보 노출 | 문서 속 전화·이메일을 그대로 답함 → 마스킹 | MODIFIED | 2.0 s |

첫 호출은 모델을 GPU 메모리에 올리느라 느립니다. 시연 직전에 `check_env.py`나 작업 **예열**로 미리 한 번 호출하세요.

실제 모델은 매번 다르게 답할 수 있습니다. 모델이 위험 요청을 스스로 거절하면 화면에 안내가 나오며, 이것이 "그래서 출력 가드가 필요하다"는 설명으로 이어집니다.

## 한계 (강의에서 다루는 내용)

정규식 규칙은 1단계 방어선일 뿐 우회될 수 있습니다. 실무에서는 **분류 모델(Llama Guard 계열) → 권한 최소화(읽기 전용 DB 계정) → 위험 작업 사람 승인**을 겹쳐 씁니다.

## 보안 주의

- `.env`는 Git에 올라가지 않습니다(`.gitignore`). 키를 코드·슬라이드·화면에 노출하지 마세요.
- 시연용 IAM 키는 최소 권한으로 만들고, 시연 후 비활성화하거나 주기적으로 교체하세요.

## License

MIT
