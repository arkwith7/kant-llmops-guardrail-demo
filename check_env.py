"""
시연 전 점검 — 강의장 도착 후 가장 먼저 실행
  python check_env.py
1) GPU (nvidia-smi)  2) 로컬 LLM 서버와 모델  3) Bedrock 자격 증명·호출  4) 모의 LLM
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from llm_backends import AWS_REGION, BEDROCK_MODEL, LOCAL_BASE_URL, LOCAL_MODEL, BedrockLLM, LLMError, LocalLLM, MockLLM

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OK, NG = "[ OK ]", "[실패]"


def check_gpu() -> None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        print(f"{NG} nvidia-smi 를 찾을 수 없습니다 (WSL이면 Windows NVIDIA 드라이버 설치 확인)")
        return
    out = subprocess.run([exe, "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    print(f"{OK} GPU: {out}")


def check_local() -> None:
    llm = LocalLLM()
    try:
        models = llm.list_models()
    except Exception as e:
        print(f"{NG} 로컬 LLM 서버 연결 안 됨 ({LOCAL_BASE_URL}): {e}  → 'ollama serve' 실행 여부 확인")
        return
    mark = OK if LOCAL_MODEL in models else NG
    print(f"{mark} 로컬 LLM 서버 {LOCAL_BASE_URL} · 모델 {len(models)}개 · 기본 모델 {LOCAL_MODEL} {'있음' if mark == OK else '없음 → ollama pull ' + LOCAL_MODEL}")
    if mark == OK:
        try:
            text, u = llm.chat("한 단어로 답하세요.", "대한민국의 수도는?", max_tokens=20)
            print(f"{OK} 로컬 추론(예열): '{text[:30]}' · {u.get('model_ms')} ms")
        except LLMError as e:
            print(f"{NG} 로컬 추론 실패: {e}")


def check_bedrock() -> None:
    has_env = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    print(f"{'[정보]'} AWS 자격 증명: {'.env/환경변수' if has_env else '환경변수 없음 → ~/.aws/credentials 사용 시도'} · 리전 {AWS_REGION}")
    try:
        text, u = BedrockLLM().chat("한 단어로 답하세요.", "대한민국의 수도는?", max_tokens=20)
        print(f"{OK} Bedrock {BEDROCK_MODEL}: '{text[:30]}' · 모델 {u.get('model_ms')} ms · 토큰 {u.get('input_tokens')}→{u.get('output_tokens')}")
    except LLMError as e:
        print(f"{NG} Bedrock: {e}")


def check_mock() -> None:
    text, _ = MockLLM().chat("", "테스트")
    print(f"{OK} 모의 LLM 동작")


if __name__ == "__main__":
    print("== 시연 환경 점검 ==")
    check_gpu()
    check_local()
    check_bedrock()
    check_mock()
