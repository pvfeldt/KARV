import os
import sys
import json
import re
import argparse
path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json, store_json, load_json_1_line, load_txt

def append_golden(predict_data,golden_data):
    for i in range(len(predict_data)):
        gold_index=int(predict_data[i]["index"])
        predict_data[i]["golden_answer"]=list(golden_data[gold_index]["answer_entities"].values())
        predict_data[i]["logical_form"]=golden_data[gold_index]["logical_form"]
    return predict_data

def refine_answers(data):
    for i in range(len(data)):
        filtered_answers=[]
        for j in range(len(data[i]["final_answer"])):
            if "m." not in data[i]["final_answer"][j] and "g." not in data[i]["final_answer"][j]:
                filtered_answers.append(data[i]["final_answer"][j].strip())
        data[i]["final_answer"]=list(set(filtered_answers))
    return data


if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Append golden entities.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    args = parser.parse_args()

    # load data
    path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_final_results_"+args.model_type+".json"
    path=os.path.abspath(path)
    data=load_json(path)
    logical_form_path="../generation/output/"+args.dataset_type+"/"+args.dataset_type+"_searched_"+args.model_type+".jsonl"
    logical_form_path=os.path.abspath(logical_form_path)
    logical_form_data=load_json_1_line(logical_form_path)
    golden_path="../data/processed/"+args.dataset_type+"/"+args.dataset_type+"_test_extracted.json"
    golden_path=os.path.abspath(golden_path)
    golden_data=load_json(golden_path)

    # append golden data
    updated_data=append_golden(data,golden_data)
    updated_data=refine_answers(updated_data)
    output_path="../evaluation/final/"+args.dataset_type+"/"+args.dataset_type+"_eval_non_"+args.model_type+".json"
    output_path=os.path.abspath(output_path)
    store_json(updated_data,output_path)
    updated_logical_form_data=append_golden(logical_form_data,golden_data)
    # updated_logical_form_data=refine_answers(updated_logical_form_data)
    output_lf_path="../evaluation/final/"+args.dataset_type+"/"+args.dataset_type+"_eval_ex_"+args.model_type+".json"
    output_lf_path=os.path.abspath(output_lf_path)
    store_json(updated_logical_form_data,output_lf_path)
