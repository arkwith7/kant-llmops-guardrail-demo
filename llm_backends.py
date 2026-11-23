"""
LLM 백엔드 모음 — 가드레일 로직과 분리해, 같은 파이프라인을 여러 LLM에 붙일 수 있게 한다.

  local   : 로컬 Private LLM (Ollama / vLLM) — OpenAI 호환 /v1/chat/completions, 표준 라이브러리만 사용
  bedrock : AWS Bedrock (리전은 .env 의 AWS_REGION, 기본 도쿄 ap-northeast-1) — boto3 Converse API, IAM 자격 증명(.env 또는 aws configure)
  mock    : 모의 LLM — 인터넷·GPU 없이 항상 같은 결과

설정은 프로젝트 루트의 .env 에서 읽는다 (.env.example 참고).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ─────────────────────────────────────────────
# .env 로더 (python-dotenv 없이 동작)
# ─────────────────────────────────────────────
def load_env(path: Path = ROOT / ".env") -> None:
    """KEY=VALUE 형식만 읽는다. 이미 설정된 환경변수와 빈 값은 덮어쓰지 않는다."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value and not os.environ.get(key):
            os.environ[key] = value


load_env()

LOCAL_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")  # Ollama (vLLM: :8000/v1)
LOCAL_MODEL = os.getenv("LOCAL_LLM_MODEL", "gemma3:27b")
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-1"
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL_ID", "google.gemma-3-12b-it")


class LLMError(RuntimeError):
    pass


# ─────────────────────────────────────────────
# 공통 인터페이스: chat(system, user) -> (text, usage)
#   usage = {"input_tokens", "output_tokens", "model_ms"} 중 알 수 있는 값
# ─────────────────────────────────────────────
class MockLLM:
    name = "mock"

    def __init__(self, model: str | None = None):
        self.model = "mock"

    def describe(self) -> str:
        return "모의 LLM (mock)"

    def chat(self, system: str, user: str, max_tokens: int = 300) -> tuple[str, dict]:
        """시연용 — 실제 모델이 '실수'하는 상황을 재현"""
        if "삭제" in user or "정리" in user:
            return "```sql\nDELETE FROM orders WHERE order_date < '2024-01-01';\n```", {}
        if "[참고 문서]" in user and "담당자" in user:
            return "영업 담당자는 김철수 과장(010-1234-5678, cs.kim@example.com)입니다.", {}
        return ("```sql\nSELECT region, SUM(amount) FROM sales "
                "WHERE month = '2026-10' GROUP BY region;\n```"), {}


class LocalLLM:
    """Ollama / vLLM 의 OpenAI 호환 엔드포인트"""
    name = "local"

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or LOCAL_MODEL
        self.base_url = (base_url or LOCAL_BASE_URL).rstrip("/")

    def describe(self) -> str:
        return f"local · {self.model} · {self.base_url}"

    def chat(self, system: str, user: str, max_tokens: int = 300) -> tuple[str, dict]:
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            raise LLMError(f"로컬 LLM 호출 실패 HTTP {e.code}: {e.read().decode(errors='ignore')[:300]}")
        except urllib.error.URLError as e:
            raise LLMError(f"로컬 LLM 서버에 연결할 수 없습니다 ({self.base_url}): {e.reason}")
        u = data.get("usage") or {}
        return data["choices"][0]["message"]["content"].strip(), {
            "input_tokens": u.get("prompt_tokens"),
            "output_tokens": u.get("completion_tokens"),
            "model_ms": round((time.perf_counter() - t0) * 1000),
        }

    def list_models(self) -> list[str]:
        with urllib.request.urlopen(f"{self.base_url}/models", timeout=10) as r:
            return [m["id"] for m in json.load(r).get("data", [])]


class BedrockLLM:
    """AWS Bedrock Converse API — IAM 자격 증명(SigV4) 사용"""
    name = "bedrock"

    def __init__(self, model: str | None = None, region: str | None = None):
        try:
            import boto3  # noqa: F401
        except ImportError:
            raise LLMError("boto3 가 필요합니다:  pip install -r requirements.txt")
        import boto3
        self.model = model or BEDROCK_MODEL
        self.region = region or AWS_REGION
        # 자격 증명 탐색 순서: 환경변수(.env의 AWS_ACCESS_KEY_ID/SECRET) → ~/.aws/credentials(aws configure) → IAM 역할
        self.client = boto3.client("bedrock-runtime", region_name=self.region)
        self._system_ok = True

    def describe(self) -> str:
        return f"bedrock · {self.model} · {self.region}"

    def _converse(self, system: str, user: str, max_tokens: int):
        kwargs = dict(
            modelId=self.model,
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
        )
        if self._system_ok:
            kwargs["system"] = [{"text": system}]
        else:  # 시스템 프롬프트를 지원하지 않는 모델이면 사용자 메시지 앞에 붙인다
            kwargs["messages"][0]["content"][0]["text"] = f"{system}\n\n{user}"
        return self.client.converse(**kwargs)

    def chat(self, system: str, user: str, max_tokens: int = 300) -> tuple[str, dict]:
        from botocore.exceptions import BotoCoreError, ClientError
        try:
            try:
                res = self._converse(system, user, max_tokens)
            except ClientError as e:
                msg = e.response.get("Error", {}).get("Message", "")
                if e.response.get("Error", {}).get("Code") == "ValidationException" and "system" in msg.lower():
                    self._system_ok = False
                    res = self._converse(system, user, max_tokens)
                else:
                    raise
        except ClientError as e:
            err = e.response.get("Error", {})
            hint = ""
            if err.get("Code") in ("AccessDeniedException", "UnrecognizedClientException"):
                hint = " → IAM 권한(bedrock:InvokeModel)과 .env 의 AWS 키를 확인하세요 (docs/iam-policy-bedrock-gemma.json)."
            raise LLMError(f"Bedrock 오류 {err.get('Code')}: {err.get('Message')}{hint}")
        except BotoCoreError as e:
            raise LLMError(f"Bedrock 연결/자격 증명 오류: {e} → .env 의 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 를 확인하세요.")
        u = res.get("usage", {})
        return res["output"]["message"]["content"][0]["text"].strip(), {
            "input_tokens": u.get("inputTokens"),
            "output_tokens": u.get("outputTokens"),
            "model_ms": res.get("metrics", {}).get("latencyMs"),
        }


def make_llm(backend: str, model: str | None = None, base_url: str | None = None):
    if backend == "mock":
        return MockLLM()
    if backend == "local":
        return LocalLLM(model, base_url)
    if backend == "bedrock":
        return BedrockLLM(model)
    raise ValueError(f"알 수 없는 백엔드: {backend}")
