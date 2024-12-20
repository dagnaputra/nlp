docker run -d --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 9898:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model Qwen/Qwen2.5-7B-Instruct --max_model_len 1024 --api-key "test_api_key" --gpu_memory_utilization 0.7