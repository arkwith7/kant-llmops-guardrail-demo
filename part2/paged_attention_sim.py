"""
Part 2 · PagedAttention 시뮬레이터 — GPU 없이 개념을 눈으로 보여준다.

같은 KV 캐시 공간(블록 N개)에 요청을 받을 때
  (A) 기존 방식: 요청마다 '최대 길이'만큼 연속 공간을 미리 예약
  (B) PagedAttention: 16토큰짜리 블록을 필요할 때마다 하나씩 할당 (OS 가상 메모리 페이징과 같은 원리)
두 방식의 동시 처리 건수와 낭비율을 비교한다.

실행:
  python part2/paged_attention_sim.py
  python part2/paged_attention_sim.py --blocks 512 --max-len 2048 --seed 7
"""
from __future__ import annotations

import argparse
import random
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def simulate(blocks: int, block_size: int, max_len: int, lengths: list[int]) -> None:
    capacity = blocks * block_size

    # (A) 최대 길이 예약
    a_admitted, a_used = 0, 0
    for n in lengths:
        if (a_admitted + 1) * max_len > capacity:
            break
        a_admitted += 1
        a_used += n
    a_reserved = a_admitted * max_len

    # (B) 블록 단위 할당
    b_admitted, b_blocks, b_used = 0, 0, 0
    for n in lengths:
        need = -(-n // block_size)  # 올림
        if b_blocks + need > blocks:
            break
        b_admitted += 1
        b_blocks += need
        b_used += n
    b_reserved = b_blocks * block_size

    def bar(used: int, reserved: int, width: int = 50) -> str:
        u = round(width * used / capacity)
        r = round(width * reserved / capacity) - u
        return "█" * u + "░" * max(r, 0) + "·" * (width - u - max(r, 0))

    print(f"\nKV 캐시 공간: 블록 {blocks}개 × {block_size}토큰 = {capacity:,} 토큰 · 요청 최대 길이 {max_len:,}")
    print("█ 실제 사용  ░ 예약했지만 빈 공간(낭비)  · 남은 공간\n")
    print(f"(A) 최대 길이 예약    {bar(a_used, a_reserved)}")
    print(f"    동시 요청 {a_admitted:>3}건 · 낭비 {1 - a_used / max(a_reserved, 1):.0%}")
    print(f"(B) PagedAttention    {bar(b_used, b_reserved)}")
    print(f"    동시 요청 {b_admitted:>3}건 · 낭비 {1 - b_used / max(b_reserved, 1):.0%} (마지막 블록의 빈칸만)")
    if a_admitted:
        print(f"\n→ 같은 GPU 메모리로 {b_admitted / a_admitted:.1f}배 많은 요청을 동시에 처리")
    print("→ 동시 처리 건수가 늘면 배치가 커지고, GPU 처리량(토큰/초)이 올라갑니다.\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, default=1024)
    ap.add_argument("--block-size", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=4096)
    ap.add_argument("--requests", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    random.seed(a.seed)
    # 실제 채팅 요청은 대부분 짧고 가끔 길다 (로그정규 분포로 근사)
    lengths = [min(a.max_len, max(32, int(random.lognormvariate(6.3, 0.8)))) for _ in range(a.requests)]
    print(f"요청 길이: 평균 {sum(lengths) // len(lengths)} 토큰, 최대 {max(lengths)} 토큰 (모의 데이터)")
    simulate(a.blocks, a.block_size, a.max_len, lengths)


if __name__ == "__main__":
    main()
