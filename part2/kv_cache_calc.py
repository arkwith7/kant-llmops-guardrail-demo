"""
Part 2 · KV 캐시 계산기 — "서빙 병목은 왜 메모리에서 생기는가"를 숫자로 보여준다.

  KV 캐시(토큰 1개) = 2(K,V) × 레이어 수 × KV 헤드 수 × 헤드 차원 × 바이트
  GPU 메모리 = 모델 가중치 + KV 캐시(동시 요청 × 문장 길이) + 기타

실행:
  python part2/kv_cache_calc.py                         # 기본: Llama-3.1-8B, 24GB GPU
  python part2/kv_cache_calc.py --model qwen2.5-7b --vram 24 --ctx 4096
  python part2/kv_cache_calc.py --model llama3.1-8b --weights int4
"""
from __future__ import annotations

import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 공개된 모델 설정(config.json) 기준. 파라미터 수는 가중치 메모리 계산용(10억 단위)
MODELS = {
    "llama3.1-8b": {"params_b": 8.0, "layers": 32, "kv_heads": 8, "head_dim": 128},
    "qwen2.5-7b": {"params_b": 7.6, "layers": 28, "kv_heads": 4, "head_dim": 128},
    "llama3.2-3b": {"params_b": 3.2, "layers": 28, "kv_heads": 8, "head_dim": 128},
}
BYTES = {"fp16": 2.0, "bf16": 2.0, "fp8": 1.0, "int8": 1.0, "int4": 0.5}
GIB = 1024 ** 3


def kv_bytes_per_token(cfg: dict, kv_dtype: str) -> float:
    return 2 * cfg["layers"] * cfg["kv_heads"] * cfg["head_dim"] * BYTES[kv_dtype]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, default="llama3.1-8b")
    ap.add_argument("--vram", type=float, default=24, help="GPU 메모리(GB)")
    ap.add_argument("--util", type=float, default=0.9, help="vLLM --gpu-memory-utilization")
    ap.add_argument("--weights", choices=BYTES, default="bf16", help="가중치 정밀도")
    ap.add_argument("--kv", choices=BYTES, default="fp16", help="KV 캐시 정밀도")
    ap.add_argument("--ctx", type=int, default=8192, help="요청 1건의 최대 길이(토큰)")
    ap.add_argument("--overhead", type=float, default=1.5, help="활성값·CUDA 등 기타(GB)")
    a = ap.parse_args()

    cfg = MODELS[a.model]
    per_tok = kv_bytes_per_token(cfg, a.kv)
    weights = cfg["params_b"] * 1e9 * BYTES[a.weights] / GIB
    budget = a.vram * a.util
    kv_room = budget - weights - a.overhead
    per_req = per_tok * a.ctx / GIB

    print(f"\n[모델] {a.model}  레이어 {cfg['layers']} · KV 헤드 {cfg['kv_heads']} · 헤드 차원 {cfg['head_dim']}")
    print(f"[KV 캐시] 토큰 1개 = 2 × {cfg['layers']} × {cfg['kv_heads']} × {cfg['head_dim']} × {BYTES[a.kv]}바이트 "
          f"= {per_tok / 1024:.0f} KB")
    print(f"[요청 1건] {a.ctx:,} 토큰 × {per_tok / 1024:.0f} KB = {per_req:.2f} GB\n")

    print(f"GPU {a.vram:.0f} GB × 사용률 {a.util:.0%}      = {budget:6.1f} GB")
    print(f"  - 모델 가중치 ({a.weights})        = {weights:6.1f} GB")
    print(f"  - 기타(활성값·CUDA)             = {a.overhead:6.1f} GB")
    print(f"  = KV 캐시에 쓸 수 있는 공간     = {kv_room:6.1f} GB")
    if kv_room <= 0:
        print("\n→ 가중치만으로 GPU가 가득 찹니다. 양자화하거나 더 큰 GPU가 필요합니다.")
        return
    full = int(kv_room // per_req)
    tokens = int(kv_room * GIB // per_tok)
    print(f"\n→ 최대 길이({a.ctx:,})를 통째로 예약하면 동시 요청 {full}건")
    print(f"→ 실제로 쓴 만큼만 잡으면(PagedAttention) 총 {tokens:,} 토큰을 여러 요청이 나눠 씀")
    print(f"   예) 평균 1,000 토큰 요청이면 약 {tokens // 1000}건 동시 처리\n")


if __name__ == "__main__":
    main()
