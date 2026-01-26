# KARV

The repository of paper **Optimizing KBQA by Correcting LLM-Generated Non-Executable Logical Form through Knowledge-Assisted Path Reconstruction [TKDE]**.

## 0 Setup

### 0.1 Knowledge Base Setup

Freebase serves as the knowledge base background for the two datasets (WebQSP, CWQ, FreebaseQA) used in this study. Detailed instructions for downloading and setting it up in Virtuoso are available [here](https://github.com/dki-lab/Freebase-Setup). 

Clone the setup repository and start up the service with the following instruction.

```
cd Freebase-Setup
python3 virtuoso.py start 3001 -d [/path/to/virtuoso/db/files]
```

Close the service as follows.

```
python3 virtuoso.py stop 3001
```

### 0.2 FACC1 Annotation Download

FACC1 annotation serves the function of mapping generated entities to existing entities in Freebase, which can be downloaded [here](https://github.com/HXX97/GMT-KBQA/tree/main/data/common_data/facc1).

### 0.3 Environment Setup

The versions specified in the requirements are primarily intended to ensure compatibility with the latest version of Llamafactory for further LLM fine-tuning and generation within this framework.

```
conda create -n KARV python=3.10
conda activate KARV
pip install -r requirements.txt
```

### 0.4 Dataset and Models

The datasets used in this work include WebQSP, CWQ and FreebaseQA.

| Dataset    | Download Link                                                |
| ---------- | ------------------------------------------------------------ |
| WebQSP     | [WebQSP Link](https://aka.ms/WebQSP)                         |
| CWQ        | [CWQ Link](https://www.dropbox.com/scl/fo/nqujvpg2gc4y0ozkw3wgr/AOzjVEsdUhv2Fx2pamfJlSw?rlkey=746t7xehfqxf1zr867nxiq8aq&e=1&st=n9e0fa7f) |
| FreebaseQA | [FreebaseQA Link](https://github.com/kelvin-jiang/FreebaseQA) |

The LLM backbones include Llama-based and DeepSeek-based models. 

| LLM Backbone                 | Download Link                                                |
| ---------------------------- | ------------------------------------------------------------ |
| Llama 2 7B                   | [Llama 2 7B Link](https://huggingface.co/meta-llama/Llama-2-7b-chat) |
| Llama 2 13B                  | [Llama 2 13B Link](https://huggingface.co/meta-llama/Llama-2-13b-chat) |
| DeepSeek LLM 7B              | [DeepSeek LLM 7B Link](https://huggingface.co/deepseek-ai/deepseek-llm-7b-chat) |
| DeepSeek R1 Distill Llama 8B | [DeepSeek R1 Distill Llama 8B Link](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B) |

The PLM retriever for comparison is the BERT-based DPR.

| PLM  | Download Link                                                |
| ---- | ------------------------------------------------------------ |
| DPR  | [DPR Link](https://huggingface.co/facebook/dpr-question_encoder-single-nq-base) |

## 1 Dataset Processing

Run `process.sh` to extract information from the original WebQSP, CWQ and FreebaseQA datasets, and generate (question, logical form) pairs for further fine-tuning. 

```
cd data
bash process.sh
```

Please refer to the following instructions to adjust the settings in `process.sh`.

```
python process_dataset.py --dataset_type [dataset] -- split [split]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [split]="train" or "dev" or "test"
```

## 2 LLM Fine-Tuning

Run `train.sh` to perform fine-tuning.

```
cd generation
bash train.sh
```

An example is demonstrated in the `train.sh`. To specify other relevant hyperparameters, please vary the contents in the box with the following instructions.

```
CUDA_VISIBLE_DEVICES=0 nohup python -u train_bash.py \
--stage sft \
--model_name_or_path [/path/to/LLM] \
--do_train  \
--dataset_dir input/[dataset] \
--dataset train_data \
--template [template] \
--finetuning_type lora \
--lora_rank [rank] \
--lora_target [PEFT modules] \
--output_dir [/path/to/output/checkpoint/]  \
--overwrite_cache \
--per_device_train_batch_size [train batch size] \
--gradient_accumulation_steps 4  \
--lr_scheduler_type cosine \
--logging_steps 10 \
--save_steps 1000 \
--learning_rate [learning rate]  \
--num_train_epochs [epoch] \
--plot_loss >> [/path/to/log/file]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [template]="llama2" (for Llama 2 models) or "deepseek" (for DeepSeek LLM 7B model) or "deepseek3" (for DeepSeek R1 Distill Llama 8B model)
# [PEFT modules]="q_proj,v_proj" (for query and value projection layers, default)
```

## 3 Logical Form Generation

Run `generate_LF.sh` to perform logical form generation.

```
cd generation
bash generate_LF.sh
```

An example is demonstrated in the `generate_LF.sh`. To specify other relevant hyperparameters, please vary the contents in the box with the following instructions.

```
CUDA_VISIBLE_DEVICES=0 nohup python -u  generate_logical_form.py \
--dataset_type [dataset] \
--model_name_or_path [/path/to/LLM] \
--model_type [model type] \
--template [template] \
--adapter_name_or_path [/path/to/stored/checkpoint/] \
--num_beams [beam size] >> [/path/to/log/file]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
# [template]="llama2" (for Llama 2 models) or "deepseek" (for DeepSeek LLM 7B model) or "deepseek3" (for DeepSeek R1 Distill Llama 8B model)
# [beam size]={3,5,8} 
```

Execute the generated logical forms with `execute.sh`.

```
bash execute.sh
```

An example is demonstrated in the `execute.sh`. To specify other relevant hyperparameters, please vary the contents in the box with the following instructions.

```
python search_in_freebase.py \
--dataset_type [dataset] \
--model_type [model type] \
--facc1_path [/path/to/downloaded/FACC1/annotation]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
```

## 4 Retrieval

Run `process_non_ex.sh` to extract non-executable entries from all generated logical forms.

```
cd retrieval
bash process_non_ex.sh
```

To change the setting, please edit:

```
python process_non_executable.py --dataset_type [dataset] --model_type [model type]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
```

Then,  run `compare.sh` to compare the extracted elements.

```
bash compare.sh
```

To change the setting, please edit:

```
python compare_elements.py \
--dataset_type [dataset] \
--model_type [model type] \
--top_k [top-k value] \
--keys [key number] \
--retriever_path [/path/to/retriever]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
# [top-k value]={1,2,3}
# [key number]={2,3,...} (<=97)
```

Next, reconstruct the reasoning paths with `reconstruct.sh`.

```
bash reconstruct.sh
```

To change the setting, please edit:

```
python reconstruct_path.py --dataset_type [dataset] --model_type [model type]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
```

Finally, perform intersection and hierarchical voting via `vote.sh`.

```
bash vote.sh
```

To vary the setting, please edit:

```
python intersect_and_vote.py --dataset_type [dataset] --model_type [model type]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
```

## 5 Evaluation

Run evaluate.sh to perform the final evaluation.

```
cd evaluation
bash evaluate.sh
```

For separate steps in evaluate.sh, please follow:

Append golden answers.

```
python process_results.py --dataset_type [dataset] --model_type [model type]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
```

Perform the evaluation.

```
python evaluate.py --dataset_type [dataset] --model_type [model type]

# [dataset]="WebQSP" or "CWQ" or "FreebaseQA"
# [model type]="llama27" or "llama213" or "deepseekllm" or "deepseekr1" (only for the purpose of specifying the model type in the generated file name)
```

## Note

We leave some empty folders in `KARV/generation/output`, `KARV/retrieval/output`, and `KARV/evaluation/final` to prevent errors caused by missing file storage paths.

## Acknowledgements

This work benefits from [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory), [ChatKBQA](https://github.com/LHRLAB/ChatKBQA), [DPR](https://huggingface.co/facebook/dpr-question_encoder-single-nq-base) and [Freebase-Setup](https://github.com/dki-lab/Freebase-Setup). The authors would like to express their gratitude for the resources provided.
