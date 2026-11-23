# Part 1 · 클라우드 인프라 실습 (노트북 + AWS)

| 실습 | 어디서 | 명령 | 보여줄 것 |
|---|---|---|---|
| ① 같은 코드, 다른 인프라 | 노트북 / AWS Bedrock | `python guardrail_demo.py` ↔ `--backend bedrock` | 온프레미스·클라우드·하이브리드의 차이는 "어디서 실행되고 데이터가 어디로 가는가" |
| ② Docker 로 LLM 서버 | 노트북 GPU | `docker compose -f part1/docker/compose.ollama.yaml up -d` | 컨테이너로 패키징 → 어디서나 같은 환경, `--gpus` 로 GPU 연결 |
| ③ Kubernetes 배포 | 노트북 kind | 아래 ③ | GPU 요청 Pod 는 Pending, CPU Pod 는 Running → 자원 요청이 배치를 결정 |
| ④ Terraform | AWS 서울 g6.xlarge (L4 24GB) | `terraform plan` (강의) / `apply`·`destroy` (리허설) | 클릭 대신 코드로 GPU 서버 + vLLM 을 만들고 지움 |
| ⑤ Ansible | ④ 에서 만든 서버 | `ansible-playbook ... --check` | 서버 안 설정(드라이버 확인, 컨테이너, 모델 교체)을 코드로 |

## ② Docker

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi   # 컨테이너에서 GPU 보이는지
docker compose -f part1/docker/compose.ollama.yaml up -d
python guardrail_demo.py --base-url http://localhost:11435/v1                # 같은 데모를 컨테이너 Ollama 로
```

`compose.vllm.yaml` 은 vLLM 버전입니다. **RTX 50 시리즈(Blackwell)는 공식 vLLM 이미지 버전에 따라 동작하지 않을 수 있어**, 노트북에서는 Ollama 컨테이너를 기본으로 쓰고 vLLM 은 ④ AWS L4 에서 실행합니다.

## ③ Kubernetes (kind)

```bash
kind create cluster --name kant --config part1/k8s/kind-config.yaml
kubectl apply -f part1/k8s/vllm-deployment.yaml          # GPU 요청
kubectl apply -f part1/k8s/ollama-cpu-deployment.yaml    # GPU 요청 없음
kubectl get pods                                         # llm-serving: Pending / ollama-cpu: Running
kubectl describe pod -l app=llm-serving | grep -A3 Events   # "Insufficient nvidia.com/gpu"
kubectl exec deploy/ollama-cpu -- ollama pull llama3.2:1b
kind delete cluster --name kant                          # 정리
```

GPU 노드에서 실제로 띄우려면 EKS GPU 노드 그룹이나 k3s + NVIDIA device plugin 이 필요합니다. 매니페스트는 그대로 씁니다.

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
