# Part 1 · IaC — AWS 서울 리전에 GPU 인스턴스(g6.xlarge, NVIDIA L4 24GB)를 만들고 vLLM 을 자동 기동
#
#   cd part1/terraform
#   cp terraform.tfvars.example terraform.tfvars   # allowed_cidr 에 내 공인 IP/32 입력
#   terraform init
#   terraform plan        # ← 강의에서는 여기까지 (비용 없음)
#   terraform apply       # ← 실제 생성 (시간당 과금 시작)
#   terraform destroy     # ← 실습 끝나면 반드시 삭제
#
# 인증: 프로젝트 루트 .env 의 AWS 키를 export 하거나 aws configure (EC2 생성 권한 필요)

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "kant-private-llm-lecture"
      ManagedBy = "terraform"
    }
  }
}

# NVIDIA 드라이버·Docker·NVIDIA Container Toolkit 이 포함된 AWS Deep Learning Base AMI
data "aws_ami" "dlami" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "vllm" {
  name_prefix = "kant-vllm-"
  description = "vLLM API and SSH from my IP only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "vLLM OpenAI-compatible API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  ingress {
    description = "SSH (Ansible)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "vllm" {
  ami                    = data.aws_ami.dlami.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.vllm.id]

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
  }

  # 부팅 시 vLLM 컨테이너 자동 기동 (모델 다운로드·로딩에 수 분 소요)
  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    vllm_image    = var.vllm_image
    model         = var.model
    max_model_len = var.max_model_len
  })

  tags = {
    Name = "kant-vllm-demo"
  }
}
