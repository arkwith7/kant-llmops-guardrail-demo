"""
Part 2 · vLLM 실시간 지표 보기 — 벤치마크를 돌리는 동안 다른 터미널에서 실행한다.

vLLM 은 /metrics 에 Prometheus 형식 지표를 내보낸다. 여기서 세 가지만 1초마다 본다.
  - 실행 중 요청 수 (vllm:num_requests_running)
  - 대기 중 요청 수 (vllm:num_requests_waiting)  → 0보다 크면 KV 캐시나 배치 한도에 걸린 것
  - KV 캐시 사용률 (vllm:kv_cache_usage_perc, 구버전은 vllm:gpu_cache_usage_perc)

실행:
  python part2/vllm_metrics.py --url http://localhost:8000      # 로컬 vLLM
  python part2/vllm_metrics.py --url http://<EC2 공인 IP>:8000   # Part 1 의 AWS g6 인스턴스
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

WANT = {
    "vllm:num_requests_running": "실행",
    "vllm:num_requests_waiting": "대기",
    "vllm:kv_cache_usage_perc": "KV",
    "vllm:gpu_cache_usage_perc": "KV",
}


def scrape(url: str) -> dict:
    out: dict = {}
    with urllib.request.urlopen(f"{url}/metrics", timeout=5) as r:
        for line in r.read().decode().splitlines():
            if line.startswith("#"):
                continue
            name = line.split("{")[0].split(" ")[0]
            if name in WANT:
                out[WANT[name]] = out.get(WANT[name], 0.0) + float(line.rsplit(" ", 1)[-1])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--interval", type=float, default=1.0)
    a = ap.parse_args()
    print(f"[vLLM 지표] {a.url}/metrics  (Ctrl+C 종료)")
    while True:
        try:
            m = scrape(a.url.rstrip("/"))
            kv = m.get("KV", 0.0)
            bar = "█" * round(kv * 30) + "·" * (30 - round(kv * 30))
            print(f"{time.strftime('%H:%M:%S')}  실행 {int(m.get('실행', 0)):>3}  대기 {int(m.get('대기', 0)):>3}  "
                  f"KV 캐시 {bar} {kv:5.1%}", flush=True)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"연결 실패: {e}")
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
