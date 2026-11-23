output "public_ip" {
  value = aws_instance.vllm.public_ip
}

output "api_base_url" {
  description = "guardrail_demo.py / bench_serving.py 의 --base-url 로 사용"
  value       = "http://${aws_instance.vllm.public_ip}:8000/v1"
}

output "ami_name" {
  value = data.aws_ami.dlami.name
}

output "next_steps" {
  value = <<-EOT
    1) 로딩 확인 (수 분):  curl http://${aws_instance.vllm.public_ip}:8000/health
    2) 벤치마크:           python part2/bench_serving.py --base-url http://${aws_instance.vllm.public_ip}:8000/v1 --model ${var.model} --levels 1,4,16,32
    3) 지표:               python part2/vllm_metrics.py --url http://${aws_instance.vllm.public_ip}:8000
    4) 끝나면 반드시:      terraform destroy
  EOT
}
