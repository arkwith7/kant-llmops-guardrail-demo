variable "region" {
  description = "AWS 리전 (g6 는 서울 리전 제공)"
  type        = string
  default     = "ap-northeast-2"
}

variable "instance_type" {
  description = "GPU 인스턴스 유형 — g6.xlarge: NVIDIA L4 24GB × 1"
  type        = string
  default     = "g6.xlarge"
}

variable "allowed_cidr" {
  description = "API·SSH 를 허용할 내 공인 IP (예: 203.0.113.10/32). 0.0.0.0/0 금지"
  type        = string
  validation {
    condition     = var.allowed_cidr != "0.0.0.0/0"
    error_message = "전체 공개(0.0.0.0/0)는 허용하지 않습니다. 내 IP/32 를 넣으세요."
  }
}

variable "key_name" {
  description = "SSH 키 페어 이름 (Ansible 실습 시 필요, 없으면 null)"
  type        = string
  default     = null
}

variable "model" {
  description = "vLLM 이 서빙할 Hugging Face 모델 (라이선스 동의 불필요 모델 권장)"
  type        = string
  default     = "Qwen/Qwen2.5-7B-Instruct"
}

variable "vllm_image" {
  description = "vLLM 컨테이너 이미지"
  type        = string
  default     = "vllm/vllm-openai:latest"
}

variable "max_model_len" {
  description = "요청 1건의 최대 토큰 수 (KV 캐시 사용량에 직접 영향)"
  type        = number
  default     = 8192
}

variable "root_volume_gb" {
  description = "루트 디스크 크기(GB) — 컨테이너 이미지 + 모델 파일"
  type        = number
  default     = 150
}
