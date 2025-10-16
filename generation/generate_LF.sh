CUDA_VISIBLE_DEVICES=1 nohup python -u  generate_logical_form.py \
--dataset_type WebQSP \
--model_name_or_path ../llm_model/llama-2-7b-chat-hf \
--model_type llama27 \
--template llama2  \
--adapter_name_or_path ../checkpoint/WebQSP/llama2-7b \
--num_beams 8 >> response_WebQSP.log
