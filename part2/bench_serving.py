"""
Part 2 · 서빙 벤치마크 — 동시 요청 수를 늘리며 '첫 토큰 시간'과 '처리량'이 어떻게 변하는지 측정한다.

OpenAI 호환 엔드포인트면 무엇이든 측정 가능 (Ollama, vLLM, 클라우드).
  - 첫 토큰까지 시간(TTFT): 입력을 처리하는 prefill 단계의 비용 → 사용자가 체감하는 '반응 속도'
  - 처리량(토큰/초): 생성하는 decode 단계의 효율 → 서버가 감당하는 '총량'

실행:
  python part2/bench_serving.py                                    # 로컬 Ollama (.env 의 LOCAL_LLM_*)
  python part2/bench_serving.py --model llama3.2 --levels 1,2,4,8
  python part2/bench_serving.py --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-7B-Instruct --levels 1,4,16,32

해석 포인트:
  - Ollama 는 동시 처리 수(OLLAMA_NUM_PARALLEL)가 작아 동시 요청이 늘면 대기열이 생김 → TTFT 급증
  - vLLM 은 연속 배칭 + PagedAttention 으로 동시 요청이 늘수록 총 처리량이 올라감
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm_backends import LOCAL_BASE_URL, LOCAL_MODEL  # noqa: E402  (.env 로드 포함)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PROMPT = "대규모 언어 모델을 기업 내부에 배포할 때 고려할 점을 5가지로 설명해 주세요."


def one_request(base_url: str, model: str, max_tokens: int) -> dict:
    body = json.dumps({
        "model": model, "stream": True, "temperature": 0, "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": PROMPT}],
        "stream_options": {"include_usage": True},
    }).encode()
    req = urllib.request.Request(f"{base_url}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft, chunks, usage_tokens = None, 0, None
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            obj = json.loads(data)
            if obj.get("usage"):
                usage_tokens = obj["usage"].get("completion_tokens")
            for ch in obj.get("choices", []):
                if (ch.get("delta") or {}).get("content"):
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    chunks += 1
    total = time.perf_counter() - t0
    return {"ttft": ttft or total, "total": total, "tokens": usage_tokens or chunks}


def run_level(base_url: str, model: str, n: int, max_tokens: int) -> dict:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as ex:
        results = list(ex.map(lambda _: one_request(base_url, model, max_tokens), range(n)))
    wall = time.perf_counter() - t0
    tokens = sum(r["tokens"] for r in results)
    return {
        "n": n,
        "ttft_p50": statistics.median(r["ttft"] for r in results),
        "ttft_max": max(r["ttft"] for r in results),
        "throughput": tokens / wall,
        "per_user": statistics.median(r["tokens"] / max(r["total"] - r["ttft"], 1e-6) for r in results),
        "wall": wall,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=LOCAL_BASE_URL)
    ap.add_argument("--model", default=LOCAL_MODEL)
    ap.add_argument("--levels", default="1,2,4,8", help="동시 요청 수 목록")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--out", default="logs/bench_serving.jsonl")
    a = ap.parse_args()
    base = a.base_url.rstrip("/")

    print(f"[대상] {base} · {a.model} · 요청당 최대 {a.max_tokens} 토큰")
    print("예열 중 …")
    one_request(base, a.model, 16)

    print(f"\n{'동시 요청':>8} | {'첫 토큰 p50':>10} | {'첫 토큰 최대':>10} | {'총 처리량':>12} | {'사용자 1명 체감':>14}")
    print("-" * 72)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    for n in [int(x) for x in a.levels.split(",")]:
        r = run_level(base, a.model, n, a.max_tokens)
        print(f"{r['n']:>8} | {r['ttft_p50']:>8.2f} s | {r['ttft_max']:>8.2f} s | "
              f"{r['throughput']:>8.1f} tok/s | {r['per_user']:>10.1f} tok/s")
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(json.dumps({"base_url": base, "model": a.model, **r}, ensure_ascii=False) + "\n")
    print("\n읽는 법: 동시 요청이 늘 때 '총 처리량'이 같이 늘면 배칭이 잘 되는 서버,")
    print("        '첫 토큰 최대'만 늘면 요청이 줄 서서 기다리는 서버입니다.")


if __name__ == "__main__":
    main()
