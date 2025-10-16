import json
import os
import re
import sys
import argparse
path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json_1_line, load_json, store_json
from evaluation.evaluate import calculate_non_ex

def extract_non_executable_entries(data):
    non_ex_entries=[]
    non_ex_index=calculate_non_ex(data)
    for i in range(len(data)):
        if i in non_ex_index:
            non_ex_entries.append(data[i])
    return non_ex_entries

# split the JOIN R and JOIN lines
def split_join(logical_form):
    pattern = r'JOIN\s*\[.*?\]\s*(?:\[[^\]]*\])?|\bJOIN\s*\(.*?\)(?:\s*\[[^\]]*\])?'
    matches = re.findall(pattern, logical_form)
    matches = [match.strip() for match in matches if match.strip()]
    return matches


# group the split lines into paths
def group_path(matches):
    grouped_paths = []
    path = []
    for line in matches:
        path.append(line)
        if line.count("[") >= 2 and line.count("]") >= 2:
            grouped_paths.append(path)
            path = []
    return grouped_paths


# process paths into dict format
def process_grouped_paths(grouped_paths):
    path_list=[]
    for path in grouped_paths:
        relations=[]
        entity=""
        direction=[]
        for rel in path:
            # direction
            if "R" in rel:
                direction.append("forward")
            else:
                direction.append("back")
            pattern = r'\[(.*?)\]'
            matches = re.findall(pattern, rel)
            matches = [match.strip() for match in matches if match.strip()]
            for match in matches:
                match=match.strip()
                if match.count(",")>=2:
                    split_match=match.split(",")
                    relation=""
                    for sp_m in split_match:
                        sp_m=sp_m.strip()
                        sp_m=sp_m.replace(" ","_")
                        relation+=sp_m+"."
                    relation=relation[:-1]
                    relations.append(relation)
                else:
                    entity=match
        direction.reverse()
        relations.reverse()
        entry={"entity":entity,"relations":relations,"direction":direction}
        path_list.append(entry)
    return path_list

def process_all_logical_form(data):
    for i in range(len(data)):
        path_list=[]
        for j in range(len(data[i]["predict_logical_form"])):
            splitted_lf=split_join(data[i]["predict_logical_form"][j])
            grouped_paths=group_path(splitted_lf)
            path=process_grouped_paths(grouped_paths)
            path_list.append(path)
        data[i]["predict_paths"]=path_list
    return data


if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Process non-executable logical form.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    args = parser.parse_args()

    # load data
    path="../generation/output/"+args.dataset_type+"/"+args.dataset_type+"_searched_"+args.model_type+".jsonl"
    path=os.path.abspath(path)
    data=load_json_1_line(path)

    # extract non-executable entries
    non_ex_entries=extract_non_executable_entries(data)

    # extract information from generate logical forms
    extracted_entries=process_all_logical_form(non_ex_entries)
    output_path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_extracted_"+args.model_type+".json"
    output_path=os.path.abspath(output_path)
    store_json(extracted_entries, output_path)