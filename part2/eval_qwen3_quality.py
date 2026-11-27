from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm_backends import LocalLLM

SYSTEM = "한국어로 답하세요. 주어진 정보만 사용하고, 지시된 형식을 따르세요."
CASES = [
    ("지식", "대한민국의 수도를 한 단어로 답하세요.", "서울"),
    ("계산", "17개 제품을 개당 3,000원에 팔았습니다. 매출액을 원 단위로 답하세요.", "51000원"),
    ("SQL", "sales(region, month, amount)에서 10월 지역별 매출 합계를 조회하는 SELECT SQL을 작성하세요.", "region 그룹별 SUM(amount), month=10"),
    ("근거", "문서: A팀은 월요일, B팀은 화요일에 회의합니다. C팀의 회의 요일은 무엇입니까?", "주어진 정보에 없음"),
    ("형식", '사과 3개와 배 2개를 fruit 및 count 필드를 가진 JSON 배열로만 출력하세요.', 'fruit/count JSON 배열'),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    llm = LocalLLM(model=args.model, base_url=args.base_url)
    rows = []
    for name, question, expected in CASES:
        started = time.perf_counter()
        try:
            answer, usage = llm.chat(SYSTEM, question, max_tokens=160)
            row = {"case": name, "question": question, "expected": expected, "answer": answer,
                   "ok": True, "usage": usage, "latency_s": round(time.perf_counter() - started, 3)}
            print(f"{name}: {answer}", flush=True)
        except Exception as error:
            row = {"case": name, "question": question, "expected": expected, "ok": False,
                   "error": f"{type(error).__name__}: {error}"}
            print(f"{name}: 실패 {error}", flush=True)
        rows.append(row)
    Path(args.out).write_text(json.dumps({"base_url": args.base_url, "model": args.model,
                                         "system": SYSTEM, "temperature": 0, "max_tokens": 160,
                                         "results": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not all(row["ok"] for row in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()