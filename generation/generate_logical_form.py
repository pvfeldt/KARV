import os
import os
import sys
import json
import re
import itertools
import random
import time
import argparse
path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json, store_json
from llamafactory.chat.chat_model import ChatModel


def wrap_prompt(prompt):
    wrapped_prompt = [{"role": "user", "content": prompt}]
    return wrapped_prompt


# response vector=[[res1,score1],[res2,score2],...],responses=[res1,res2]
def extract_response(response_vector):
    responses = []
    for i in range(len(response_vector)):
        responses.append(response_vector[i][0])
    return responses


def generate_response(data, dataset_type,output_path):
    instruction="Please generate logical form queries according to the given question."
    with open(output_path, "a", encoding="UTF-8") as file:
        for i in range(len(data)):
            print("i=", i, "/", len(data))
            question="Question: "+data[i]["question"]
            wrapped_prompt=wrap_prompt(instruction+question)
            response_vector = chat_model.chat(wrapped_prompt)
            response = extract_response(response_vector)
            if dataset_type=="FreebaseQA":
                entry={"index": i, "question": data[i]["question"], "predicted_logical_forms": response,
                     "label_logical_form": data[i]["logical_forms"]}
            else:
                entry = {"index": i, "question": data[i]["question"], "predicted_logical_forms": response,
                     "label_logical_form": data[i]["logical_form"]}
            json.dump(entry, file)
            file.write("\n")
            file.flush()


if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Generate logical forms with fine-tuned LLM.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_name_or_path', type=str, required=True,
                        help="Path to LLM model.")
    parser.add_argument('--template', type=str, required=True,
                        help="Prompt template (e.g., 'llama2').")
    parser.add_argument('--adapter_name_or_path', type=str, required=True,
                        help="Path to LLM checkpoint.")
    parser.add_argument('--num_beams', type=int, required=True,
                        help="Beam size.")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    args = parser.parse_args()

    # load files and model
    path="../data/processed/"+args.dataset_type+"/"+args.dataset_type+"_test_extracted.json"
    path = os.path.abspath(path)
    data=load_json(path)
    params = {"model_name_or_path": args.model_name_or_path, "template": args.template,
              "adapter_name_or_path": args.adapter_name_or_path, "num_beams": args.num_beams}
    chat_model = ChatModel(params)

    # generate logical forms
    output_path="../generation/output/"+args.dataset_type+"/"+args.dataset_type+"_generated_"+args.model_type+".jsonl"
    output_path=os.path.abspath(output_path)
    generate_response(data,args.dataset_type,output_path)
