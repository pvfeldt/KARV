import os
import sys
import json
import re
import argparse

path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json, store_json, load_json_1_line, load_txt


def FindstrInList(entry, elist):
    for item in elist:
        if entry in item:
            return True
    return False


def Find_P_R_F_HIT(fp, tp, fn):
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)

    f1 = (2 * precision * recall) / (precision + recall)

    if tp > 1e-40:
        hit = 1
    else:
        hit = 0

    return [precision, recall, f1, hit]


def ans_acc(predict, gold):
    tp = 1e-40  # numerical trick
    fp = 0.0
    fn = 0.0
    predict_list = predict[0]
    for x in gold:
        if FindstrInList(x, predict_list):
            tp += 1
        else:
            # print(x)
            fn += 1

    for x in predict_list:
        x = x.strip()
        if not FindstrInList(x, gold):
            # print(x)
            fp += 1

    precision, recall, f1, hit = Find_P_R_F_HIT(fp, tp, fn)
    return [precision, recall, f1, hit]


def evaluate_results_non(data):
    p_mean = 0
    r_mean = 0
    f1_mean = 0
    hit1_mean = 0
    count_unavailable = 0
    for i in range(len(data)):
        if data[i]["golden_answer"] == [] or None in data[i]["golden_answer"]:
            count_unavailable += 1
            continue
        predict_data = [data[i]["final_answer"]]
        golden_data = data[i]["golden_answer"]
        p, r, f1, hit1 = ans_acc(predict_data, golden_data)
        p_mean += p
        r_mean += r
        f1_mean += f1
        hit1_mean += hit1
    count = len(data)-count_unavailable
    print("available:",count)
    print("f1_mean:", f1_mean, f1_mean / count)
    print("hit1_mean:", hit1_mean, hit1_mean / count)
    return [hit1_mean/count,f1_mean/count,count]

def evaluate_results_logical_form(data):
    p_mean = 0
    r_mean = 0
    f1_mean = 0
    hit1_mean = 0
    count_unavailable = 0
    non_ex_index = calculate_non_ex(data)
    non_ex_count = len(non_ex_index)
    for i in range(len(data)):
        if i in non_ex_index:
            continue
        if data[i]["golden_answer"] == [] or None in data[i]["golden_answer"]:
            count_unavailable += 1
            continue
        predict_data=[]
        for j in range(len(data[i]["searched_answers"])):
            if None not in data[i]["searched_answers"][j]:
                predict_data+=data[i]["searched_answers"][j]
        predict_data=[predict_data]
        golden_data = data[i]["golden_answer"]
        p, r, f1, hit1 = ans_acc(predict_data, golden_data)
        p_mean += p
        r_mean += r
        f1_mean += f1
        hit1_mean += hit1
    ex_count=len(data)-non_ex_count-count_unavailable
    print("available:", ex_count)
    print("f1 mean:", f1_mean, f1_mean / ex_count)
    print("hit1 mean:", hit1_mean, hit1_mean / ex_count)
    return [hit1_mean/ex_count, f1_mean/ex_count, ex_count]

def calculate_mean(inexecutable,executable):
    # inexecutable=[hit1,f1,num], executable=[hit1,f1,num]
    total_num=inexecutable[2]+executable[2]
    final_hit1=inexecutable[0]*inexecutable[2]/total_num+executable[0]*executable[2]/total_num
    final_f1=inexecutable[1]*inexecutable[2]/total_num+executable[1]*executable[2]/total_num
    print("final_hit1:",final_hit1)
    print("final_f1:",final_f1)

def calculate_non_ex(data):
    count=0
    non_ex_index=[]
    for i in range(len(data)):
        if "searched_answers" in data[i]:
            searched_answers = []
            for j in range(len(data[i]["searched_answers"])):
                searched_answers += data[i]["searched_answers"][j]
            if searched_answers == []:
                count+=1
                non_ex_index.append(i)
    print("non executable:",count)
    print("non executable rate:",count/len(data))
    return non_ex_index


if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Evaluate results.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    args = parser.parse_args()

    # load file
    ex_path="../evaluation/final/"+args.dataset_type+"/"+args.dataset_type+"_eval_ex_"+args.model_type+".json"
    ex_path=os.path.abspath(ex_path)
    ex_data=load_json(ex_path)
    non_ex_path="../evaluation/final/"+args.dataset_type+"/"+args.dataset_type+"_eval_non_"+args.model_type+".json"
    non_ex_path=os.path.abspath(non_ex_path)
    non_ex_data=load_json(non_ex_path)
    # evaluate
    ex_list=evaluate_results_logical_form(ex_data)
    non_ex_list=evaluate_results_non(non_ex_data)
    calculate_mean(ex_list, non_ex_list)
