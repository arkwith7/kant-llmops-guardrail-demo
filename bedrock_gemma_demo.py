"""
LLM 체험 데모 — AWS Bedrock 서울 리전(ap-northeast-2) Gemma 3
-------------------------------------------------------------
로컬 GPU를 쓸 수 없을 때, 같은 오픈 웨이트 계열 모델을 '관리형 클라우드'에서 체험한다.

- 서울 리전 In-Region 제공 Gemma 3: google.gemma-3-4b-it / 12b-it / 27b-it
  (Meta Llama 3.x 는 서울 리전에서 제공되지 않음)
- Converse API: 모델이 바뀌어도 같은 코드
- 응답과 함께 지연 시간·토큰 수 출력 → '관측성'으로 연결
- 인증: IAM 사용자 액세스 키 (.env 의 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY) 또는 aws configure

실행:
  python bedrock_gemma_demo.py                 # 12B 질문 1개
  python bedrock_gemma_demo.py --compare       # 4B / 12B / 27B 비교
  python bedrock_gemma_demo.py --stream        # 첫 토큰까지 시간 측정
  python bedrock_gemma_demo.py --chat --model google.gemma-3-4b-it
  python bedrock_gemma_demo.py --list          # 서울 리전 Google·Meta 모델 목록 (bedrock:ListFoundationModels 권한)
"""
from __future__ import annotations

import argparse
import sys
import time

import llm_backends  # .env 로드
from llm_backends import AWS_REGION, BEDROCK_MODEL

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    sys.exit("boto3 가 필요합니다:  pip install -r requirements.txt")

GEMMA_MODELS = ["google.gemma-3-4b-it", "google.gemma-3-12b-it", "google.gemma-3-27b-it"]
SYSTEM = "당신은 IT 교육 과정의 친절한 조교입니다. 한국어로 핵심만 간결하게 답하세요."
DEFAULT_Q = "Private LLM을 회사 내부에 직접 운영할 때의 장점과 단점을 각각 2가지씩 알려줘."


def list_models() -> None:
    bedrock = boto3.client("bedrock", region_name=AWS_REGION)
    for provider in ("Google", "Meta"):
        models = bedrock.list_foundation_models(byProvider=provider).get("modelSummaries", [])
        print(f"\n[{provider}] {len(models)}개")
        for m in models:
            print(f"  {m['modelId']:<34} {m.get('modelName', ''):<22} {','.join(m.get('inferenceTypesSupported', []))}")


def ask(client, model_id: str, question: str, history: list | None = None) -> tuple[str, dict]:
    messages = (history or []) + [{"role": "user", "content": [{"text": question}]}]
    t0 = time.perf_counter()
    res = client.converse(
        modelId=model_id,
        system=[{"text": SYSTEM}],
        messages=messages,
        inferenceConfig={"maxTokens": 512, "temperature": 0.3},
    )
    usage = res.get("usage", {})
    return res["output"]["message"]["content"][0]["text"], {
        "wall_ms": round((time.perf_counter() - t0) * 1000),   # 네트워크 포함 체감 시간
        "model_ms": res.get("metrics", {}).get("latencyMs"),   # Bedrock 이 보고한 처리 시간
        "in": usage.get("inputTokens"),
        "out": usage.get("outputTokens"),
    }


def ask_stream(client, model_id: str, question: str) -> None:
    t0, first = time.perf_counter(), None
    res = client.converse_stream(
        modelId=model_id,
        system=[{"text": SYSTEM}],
        messages=[{"role": "user", "content": [{"text": question}]}],
        inferenceConfig={"maxTokens": 512, "temperature": 0.3},
    )
    for event in res["stream"]:
        delta = event.get("contentBlockDelta", {}).get("delta", {}).get("text")
        if delta:
            first = first or time.perf_counter()
            print(delta, end="", flush=True)
        if "metadata" in event:
            u = event["metadata"].get("usage", {})
            ttft = round((first - t0) * 1000) if first else "-"
            print(f"\n\n[관측] 첫 토큰까지 {ttft} ms · 전체 {round((time.perf_counter() - t0) * 1000)} ms · "
                  f"입력 {u.get('inputTokens')} / 출력 {u.get('outputTokens')} 토큰")


def print_stats(model_id: str, s: dict) -> None:
    print(f"[관측] {model_id} · 체감 {s['wall_ms']} ms (모델 {s['model_ms']} ms) · 입력 {s['in']} / 출력 {s['out']} 토큰")


def main() -> None:
    ap = argparse.ArgumentParser(description="Bedrock 서울 리전 Gemma 3 체험")
    ap.add_argument("--model", default=BEDROCK_MODEL)
    ap.add_argument("-q", "--question", default=DEFAULT_Q)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--chat", action="store_true")
    args = ap.parse_args()

    try:
        if args.list:
            list_models()
            return
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        print(f"[리전] {AWS_REGION}")
        if args.compare:
            print(f"[질문] {args.question}")
            for m in GEMMA_MODELS:
                text, s = ask(client, m, args.question)
                print(f"\n=== {m} ===\n{text}")
                print_stats(m, s)
        elif args.stream:
            print(f"[모델] {args.model}\n[질문] {args.question}\n")
            ask_stream(client, args.model, args.question)
        elif args.chat:
            print(f"[모델] {args.model} — 빈 줄 또는 q 입력 시 종료")
            history: list = []
            while True:
                try:
                    q = input("\n질문> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not q or q.lower() == "q":
                    break
                text, s = ask(client, args.model, q, history)
                history += [{"role": "user", "content": [{"text": q}]},
                            {"role": "assistant", "content": [{"text": text}]}]
                print(f"응답> {text}")
                print_stats(args.model, s)
        else:
            print(f"[모델] {args.model}\n[질문] {args.question}\n")
            text, s = ask(client, args.model, args.question)
            print(text)
            print_stats(args.model, s)
    except ClientError as e:
        err = e.response.get("Error", {})
        print(f"[Bedrock 오류] {err.get('Code')}: {err.get('Message')}")
        if err.get("Code") in ("AccessDeniedException", "UnrecognizedClientException"):
            print("→ IAM 권한과 .env 의 AWS 키를 확인하세요 (docs/iam-policy-bedrock-gemma.json).")
        sys.exit(1)
    except BotoCoreError as e:
        print(f"[연결/자격 증명 오류] {e}")
        print("→ .env 의 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 또는 aws configure 설정을 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
