# Part 1 · 클라우드 인프라 실습 (노트북 + AWS)

| 실습 | 어디서 | 명령 | 보여줄 것 |
|---|---|---|---|
| ① 같은 코드, 다른 인프라 | 노트북 / AWS Bedrock | `python guardrail_demo.py` ↔ `--backend bedrock` | 온프레미스·클라우드·하이브리드의 차이는 "어디서 실행되고 데이터가 어디로 가는가" |
| ② Docker 로 LLM 서버 | 노트북 GPU | `docker compose -f part1/docker/compose.vllm.yaml up -d` | vLLM 컨테이너와 GPU 연결 |
| ③ Kubernetes 배포 | 노트북 Minikube | 아래 ③ | GPU 요청 Pod 에 vLLM 배포 및 실제 추론 |
| ④ Terraform | AWS 서울 g6.xlarge (L4 24GB) | `terraform plan` (강의) / `apply`·`destroy` (리허설) | 클릭 대신 코드로 GPU 서버 + vLLM 을 만들고 지움 |
| ⑤ Ansible | ④ 에서 만든 서버 | `ansible-playbook ... --check` | 서버 안 설정(드라이버 확인, 컨테이너, 모델 교체)을 코드로 |

## ② Docker

```bash
docker compose -f part1/docker/compose.vllm.yaml up -d
docker logs -f kant-vllm                   # 모델 다운로드·초기화 및 API 준비 확인
curl http://127.0.0.1:8000/v1/models
python guardrail_demo.py --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen2.5-1.5B-Instruct
docker compose -f part1/docker/compose.vllm.yaml stop
```

RTX 5090 Laptop · WSL2에서 vLLM 0.34.0과 Qwen2.5-1.5B GPU 추론을 확인했습니다. 첫 실행은 이미지·모델 다운로드와 GPU 커널 예열이 필요합니다. API는 로컬 호스트에만 열립니다. GPU 메모리 충돌을 막으려면 Ollama 모델과 Kubernetes vLLM Pod를 내린 뒤 실행하세요.

## ③ Kubernetes (Minikube + WSL2 GPU)

```bash
MINIKUBE="$HOME/opt/minikube"              # 이 장비에 설치한 Minikube 1.39.0
"$MINIKUBE" start -p kant-gpu --driver=docker --container-runtime=docker --gpus=all --cpus=4 --memory=8192 --disk-size=30g
"$MINIKUBE" -p kant-gpu kubectl -- --context=kant-gpu patch daemonset nvidia-device-plugin-daemonset -n kube-system --type=strategic --patch-file part1/k8s/nvidia-device-plugin-wsl-patch.yaml
"$MINIKUBE" -p kant-gpu kubectl -- --context=kant-gpu rollout status daemonset/nvidia-device-plugin-daemonset -n kube-system
"$MINIKUBE" -p kant-gpu kubectl -- --context=kant-gpu describe node kant-gpu  # Allocatable: nvidia.com/gpu: 1 확인
"$MINIKUBE" -p kant-gpu image load vllm/vllm-openai:v0.34.0
docker compose -f part1/docker/compose.vllm.yaml stop
"$MINIKUBE" -p kant-gpu kubectl -- --context=kant-gpu apply -f part1/k8s/vllm-minikube-wsl.yaml
"$MINIKUBE" -p kant-gpu kubectl -- --context=kant-gpu rollout status deployment/vllm-local --timeout=10m
"$MINIKUBE" -p kant-gpu kubectl -- --context=kant-gpu port-forward service/vllm-local 8000:8000 --address 127.0.0.1
```

다른 터미널에서 위 Docker 실습과 같은 `curl` 및 `guardrail_demo.py` 명령을 사용합니다. 종료하려면 포트 포워딩을 Ctrl+C로 중지하고 `"$HOME/opt/minikube" -p kant-gpu kubectl -- --context=kant-gpu scale deployment/vllm-local --replicas=0`을 실행하세요. 다시 띄울 때는 `--replicas=1`을 사용합니다. GPU는 한 장이므로 Docker와 Kubernetes vLLM을 동시에 실행하지 않습니다.

WSL2 중첩 컨테이너에서는 NVIDIA 플러그인에 WSL 드라이버 라이브러리를 연결해야 합니다. 위 패치는 이 장비의 Minikube 노드 경로를 사용하므로 다른 환경에서는 경로와 GPU 등록을 확인하세요. Kubernetes 모델 캐시는 Minikube 노드의 `/data/kant-huggingface`에 유지되며 Docker의 호스트 캐시와 별도입니다. 로컬 시연 구성으로 인증이나 외부 네트워크 격리가 갖춰진 운영 환경은 아닙니다.

기존 kind의 GPU Pending 시연은 `kind-config.yaml`, `vllm-deployment.yaml`, `ollama-cpu-deployment.yaml`로 별도로 유지합니다. 디렉터리 전체가 아닌 개별 매니페스트를 적용하세요.

## ④ Terraform (AWS)

```bash
cd part1/terraform
cp terraform.tfvars.example terraform.tfvars     # allowed_cidr = 내 IP/32
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...   # EC2 생성 권한 필요 (Bedrock 키와 별도 권장)
terraform init && terraform validate && terraform plan
terraform apply          # 리허설에서만 · 시간당 과금
terraform output next_steps
terraform destroy        # 반드시
```

- 인스턴스: g6.xlarge (NVIDIA L4 24GB), AMI: AWS Deep Learning Base(드라이버·Docker 포함), 모델: Qwen2.5-7B-Instruct
- 보안: API(8000)·SSH(22)는 `allowed_cidr` 로만 허용, 전체 공개 차단
- 서울 리전 GPU 쿼터가 0이면 Service Quotas 에서 "Running On-Demand G and VT instances" 증설 요청 필요

## ⑤ Ansible

```bash
pip install ansible-core
cp part1/ansible/inventory.ini.example part1/ansible/inventory.ini
ansible-playbook -i part1/ansible/inventory.ini part1/ansible/playbook.yml --check
ansible-playbook -i part1/ansible/inventory.ini part1/ansible/playbook.yml -e model=Qwen/Qwen2.5-1.5B-Instruct
```
