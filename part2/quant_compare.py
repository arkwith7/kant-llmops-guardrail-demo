"""
Part 2 · 양자화 비교 — 같은 모델의 정밀도별 버전을 GPU 메모리·속도·답변으로 비교한다 (Ollama).

기본 비교 대상 (Llama 3.2 3B, 다운로드 합계 약 12GB):
  llama3.2:3b-instruct-fp16   16비트 (원본에 가까움)
  llama3.2:3b-instruct-q8_0   8비트
  llama3.2:3b-instruct-q4_K_M 4비트

준비:  ollama pull <위 태그 3개>   (강의 전날 미리)
실행:
  python part2/quant_compare.py
  python part2/quant_compare.py --tags gemma3:12b-it-fp16,gemma3:12b-it-q8_0,gemma3:12b-it-q4_K_M

선택 기준(강의 포인트):
  메모리가 빠듯하면 4비트 → 속도·용량 이득이 크지만 품질 저하를 업무 평가셋으로 반드시 확인
  품질이 최우선이면 8비트 또는 16비트 → 같은 GPU에 올릴 수 있는 동시 요청 수가 줄어듦
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm_backends import LOCAL_BASE_URL  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_TAGS = "llama3.2:3b-instruct-fp16,llama3.2:3b-instruct-q8_0,llama3.2:3b-instruct-q4_K_M"
PROMPT = "다음 문장을 한 문장으로 요약하세요: 기업이 대규모 언어 모델을 내부에 직접 배포하면 데이터가 외부로 나가지 않지만, GPU 인프라와 운영 인력이 필요하다."
GIB = 1024 ** 3


def post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def vram_of(native: str, tag: str) -> float | None:
    with urllib.request.urlopen(f"{native}/api/ps", timeout=10) as r:
        for m in json.load(r).get("models", []):
            if m.get("name") == tag or m.get("model") == tag:
                return m.get("size_vram", 0) / GIB
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default=DEFAULT_TAGS)
    ap.add_argument("--native-url", default=LOCAL_BASE_URL.rstrip("/").removesuffix("/v1"))
    ap.add_argument("--max-tokens", type=int, default=120)
    a = ap.parse_args()

    rows = []
    for tag in [t.strip() for t in a.tags.split(",") if t.strip()]:
        print(f"\n=== {tag} ===")
        try:
            post(f"{a.native_url}/api/generate", {"model": tag, "prompt": "hi", "stream": False,
                                                  "options": {"num_predict": 1}, "keep_alive": "2m"})  # 로딩
            r = post(f"{a.native_url}/api/generate", {
                "model": tag, "prompt": PROMPT, "stream": False, "keep_alive": "2m",
                "options": {"temperature": 0, "num_predict": a.max_tokens}})
        except Exception as e:
            print(f"  실패: {e}  → ollama pull {tag}")
            continue
        tps = r["eval_count"] / (r["eval_duration"] / 1e9)
        prompt_ms = r.get("prompt_eval_duration", 0) / 1e6
        vram = vram_of(a.native_url, tag)
        print(f"  답변: {' '.join(r['response'].split())[:160]}")
        rows.append((tag, vram, tps, prompt_ms))
        # 다음 모델을 위해 GPU 에서 내림
        post(f"{a.native_url}/api/generate", {"model": tag, "prompt": "", "keep_alive": 0, "stream": False})

    if rows:
        print(f"\n{'모델':<34} | {'GPU 메모리':>9} | {'생성 속도':>11} | {'입력 처리':>9}")
        print("-" * 74)
        for tag, vram, tps, pms in rows:
            v = f"{vram:6.1f} GB" if vram is not None else "   -   "
            print(f"{tag:<34} | {v:>9} | {tps:7.1f} tok/s | {pms:6.0f} ms")
        print("\n읽는 법: 비트 수가 줄면 메모리는 줄고 속도는 대체로 오릅니다. 답변 품질은 직접 비교하세요.")


if __name__ == "__main__":
    main()
