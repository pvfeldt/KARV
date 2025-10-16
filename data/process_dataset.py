import os
import sys

path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
import re
import sqlite3
import random
import numpy as np
import time
import torch
import json
import itertools
import pandas as pd
import argparse
from utils.json_utils import load_json, store_json
from utils.convert_sparql import convert_sparql_to_s_expression, convert_s_expression_to_logical_form
from generation.search_in_freebase import convert_to_query_
from utils.sparql_execution import get_label_with_odbc, execute_query_with_odbc


def search_answers(query, name_dict):
    answer_set = execute_query_with_odbc(query)
    # convert set() to list()
    answer_list = list(answer_set)
    answers = []
    if len(answer_list) != 0:
        for i in range(len(answer_list)):
            if answer_list[i] != None:
                entity_id = answer_list[i].replace("http://rdf.freebase.com/ns/", "")
                if entity_id.startswith("m.") or entity_id.startswith("g."):
                    if entity_id in name_dict:
                        entity_name = name_dict[entity_id]
                        answers.append(entity_name)
                    else:
                        entity_name = get_label_with_odbc(entity_id)
                        if entity_name != None or entity_name != "":
                            answers.append(entity_name)
                        else:
                            answers.append(entity_id)
                else:
                    answers.append(entity_id)
    return answers


# entry={entity,relations,path-lf}
def generate_logical_forms(entry):
    lfs = []
    entity_value = get_label_with_odbc(entry["entity"])
    if entity_value != None:
        topic_entity = "[ " + entity_value + " ]"
        lf = topic_entity
        for i in range(len(entry["relation"])):
            relation = entry["relation"][i].replace(".", " , ")
            relation = relation.replace("_", " ")
            lf = "( JOIN ( R [ " + relation + " ] ) " + lf + " )"
            lfs.append(lf)
    return lfs


# reverse key and value in dict
def reverse_dict(dict):
    new_dict = {}
    keys = list(dict.keys())
    values = list(dict.values())
    for i in range(len(keys)):
        new_dict[values[i]] = keys[i]
    return new_dict


# entry=[{entity,relations,path-lf}]
def group_entities(entries):
    grouped_index = {}
    for i in range(len(entries)):
        entity_value = get_label_with_odbc(entries[i]["entity"])
        if entity_value != None:
            if entity_value.lower() in grouped_index:
                grouped_index[entity_value.lower()].append(i)
            elif entity_value.lower().replace(" ", "") in grouped_index:
                grouped_index[entity_value.lower().replace(" ", "")].append(i)
            else:
                grouped_index[entity_value.lower()] = [i]
    return grouped_index


def combine_logical_forms(grouped_index, entries):
    logical_forms = []
    entity_indices = grouped_index.values()
    for combination in itertools.product(*entity_indices):
        single_logical_form = []
        combination = list(combination)
        for index in combination:
            single_logical_form.append(entries[index]["intermediate_LFs"][-1])
        logical_forms.append(single_logical_form)
    return logical_forms


# logical_forms=[lf]
def intersect_logical_forms(logical_forms):
    intersected_logical_form = logical_forms[0]
    for i in range(1, len(logical_forms)):
        intersected_logical_form = "( AND " + logical_forms[i] + " " + intersected_logical_form + " )"
    return intersected_logical_form


# dataset_type= "WQSP" or "CWQ" or "FreebaseQA"
# split="train" or "test"
def extract_information(data, dataset_type, split):
    output_entries = []
    if dataset_type == 'WebQSP':
        data = data["Questions"]
        for i in range(len(data)):
            print("i=", i)
            question = data[i]["ProcessedQuestion"]
            # add topic entities
            topic_entity_label = data[i]["Parses"][0]["TopicEntityName"]
            topic_entity_id = data[i]["Parses"][0]["TopicEntityMid"]
            if topic_entity_label == None or topic_entity_id == None:
                continue
            golden_entities = {}
            golden_entities[topic_entity_id] = topic_entity_label
            if data[i]["Parses"][0]["Constraints"] != []:
                for j in range(len(data[i]["Parses"][0]["Constraints"])):
                    if data[i]["Parses"][0]["Constraints"][j]["ArgumentType"] == "Entity":
                        constraint_entity_id = data[i]["Parses"][0]["Constraints"][j]["Argument"]
                        constraint_entity_label = data[i]["Parses"][0]["Constraints"][j]["EntityName"]
                        golden_entities[constraint_entity_id] = constraint_entity_label
            # add answer entities
            answer_entities = {}
            for j in range(len(data[i]["Parses"][0]["Answers"])):
                if data[i]["Parses"][0]["Answers"][j]["AnswerType"] == "Entity":
                    answer_entities[data[i]["Parses"][0]["Answers"][j]["AnswerArgument"]] = \
                        data[i]["Parses"][0]["Answers"][j]["EntityName"]
                else:
                    answer_entities["value"] = data[i]["Parses"][0]["Answers"][j]["AnswerArgument"]
            sparql_query = data[i]["Parses"][0]["Sparql"]
            ns_golden_entities = {}
            golden_keys = golden_entities.keys()
            s_expression=""
            logical_form=""
            for key in golden_keys:
                ns_golden_entities["ns:" + key] = golden_entities[key]
            try:
                s_expression = convert_sparql_to_s_expression(sparql_query, ns_golden_entities)
            except Exception as e:
                print("Error:", e)
                s_expression = None
            if s_expression != None:
                logical_form, _ = convert_s_expression_to_logical_form(s_expression, {})
            if logical_form=="" and split=="train":
                continue
            entry = {"question": question, "sparql": sparql_query, "logical_form": logical_form,
                     "golden_entities": golden_entities, "answer_entities": answer_entities}
            output_entries.append(entry)

    elif dataset_type == 'CWQ':
        for i in range(len(data)):
            print("i=", i)
            question = data[i]["question"]
            # sparql=sparql query
            sparql_query = data[i]["sparql"]
            pattern_str_1 = r'ns:m\.0\w*'
            pattern_str_2 = r'ns:g\.\w*'
            mid_list_1 = [mid.strip() for mid in re.findall(pattern_str_1, sparql_query)]
            mid_list_2 = [mid.strip() for mid in re.findall(pattern_str_2, sparql_query)]
            mid_list = mid_list_1 + mid_list_2
            # add topic entities
            golden_entities = {}
            for ent_id in mid_list:
                ent_id = ent_id.replace("ns:", "")
                ent_label = get_label_with_odbc(ent_id)
                golden_entities[ent_id] = ent_label
            # add answer entities
            answer_entities = {}
            if split == "train" or split == "dev":
                for j in range(len(data[i]["answers"])):
                    answer_entities[data[i]["answers"][j]["answer_id"]] = data[i]["answers"][j]["answer"]
            elif split == "test":
                for ans_id in data[i]["answer"]:
                    ans_label = get_label_with_odbc(ans_id)
                    answer_entities[ans_id] = ans_label
            logical_form = ""
            try:
                s_expression = convert_sparql_to_s_expression(sparql_query, mid_list)
            except Exception as e:
                print("Error:", e)
                if split == "train":
                    continue
                elif split == "test":
                    s_expression = None
            if s_expression == None:
                if split == "train":
                    continue
            elif s_expression != None:
                logical_form, _ = convert_s_expression_to_logical_form(s_expression, golden_entities)
            entry = {"question": question, "sparql": sparql_query, "logical_form": logical_form,
                     "golden_entities": golden_entities, "answer_entities": answer_entities}
            output_entries.append(entry)
    elif dataset_type == 'FreebaseQA':
        data = data["Questions"]
        for i in range(len(data)):
            print("i=", i)
            question = data[i]["RawQuestion"]
            golden_entities = {}
            reasoning_information = []
            answer_entities = {}
            for j in range(len(data[i]["Parses"])):
                tmp_golden_entities = {}
                entity_key = data[i]["Parses"][j]["TopicEntityMid"]
                entity_value = get_label_with_odbc(entity_key)
                golden_entities[entity_key] = entity_value
                tmp_golden_entities[entity_key] = entity_value
                relation_for_one_entity = data[i]["Parses"][j]["InferentialChain"].split("..")
                direction = []
                for k in range(len(relation_for_one_entity)):
                    direction.append("forward")
                entry = {"entity": entity_key, "relation": relation_for_one_entity, "direction": direction}
                path_lf = generate_logical_forms(entry)
                entry["intermediate_LFs"] = path_lf
                reasoning_information.append(entry)
                for k in range(len(data[i]["Parses"][j]["Answers"])):
                    answer_key = data[i]["Parses"][j]["Answers"][k]["AnswersMid"]
                    answer_value = get_label_with_odbc(answer_key)
                    answer_entities[answer_key] = answer_value
            # decide logical form
            logical_forms = []
            grouped_index = group_entities(reasoning_information)
            combined_logical_forms = combine_logical_forms(grouped_index, reasoning_information)
            # lf=[lf]
            for lf in combined_logical_forms:
                intersected_logical_form = intersect_logical_forms(lf)
                logical_forms.append(intersected_logical_form)
            reversed_golden_entities = reverse_dict(golden_entities)
            executed_answers = []
            for lf in logical_forms:
                try:
                    query = convert_to_query_(lf, reversed_golden_entities, {})
                    executed_answer = search_answers(query, {})
                    executed_answers.append(executed_answer)
                except Exception as e:
                    print("Error:", e)
            entry = {"question": question, "golden_entities": golden_entities, "answer_entities": answer_entities,
                     "logical_forms": logical_forms, "executed_answers": executed_answers}
            output_entries.append(entry)
    return output_entries


# for FreebaseQA
def refine_logical_forms(data):
    # filter non-executable
    for i in range(len(data)):
        print("i=", i)
        new_executed_answers = []
        new_logical_forms = []
        for j in range(len(data[i]["executed_answers"])):
            if data[i]["executed_answers"][j] != []:
                new_executed_answers.append(data[i]["executed_answers"][j])
                new_logical_forms.append(data[i]["logical_forms"][j])
        data[i]["executed_answers"] = new_executed_answers
        data[i]["logical_forms"] = new_logical_forms
    # get min answer number
    for i in range(len(data)):
        print("i=", i)
        new_executed_answers = []
        new_logical_forms = []
        if data[i]["executed_answers"] != []:
            min_answer_count = len(data[i]["executed_answers"][0])
            for j in range(len(data[i]["executed_answers"])):
                if len(data[i]["executed_answers"][j]) < len(data[i]["executed_answers"]):
                    min_answer_count = len(data[i]["executed_answers"][j])
            for j in range(len(data[i]["executed_answers"])):
                if len(data[i]["executed_answers"][j]) == min_answer_count and data[i]["logical_forms"][
                    j] not in new_logical_forms:
                    new_executed_answers.append(data[i]["executed_answers"][j])
                    new_logical_forms.append(data[i]["logical_forms"][j])
        data[i]["executed_answers"] = new_executed_answers
        data[i]["logical_forms"] = new_logical_forms
        data[i]["topic_entities"] = data[i]["golden_entities"]
    return data


def generate_train_dataset(data, dataset_type):
    output_entries = []
    instruction = "Please generate logical form queries according to the given question."
    if dataset_type == "FreebaseQA":
        for i in range(len(data)):
            if data[i]["logical_forms"] != []:
                input = "Question: " + data[i]["question"]
                for lf in data[i]["logical_forms"]:
                    entry = {"instruction": instruction, "input": input, "output": lf, "history": []}
                    output_entries.append(entry)
    else:
        for i in range(len(data)):
            if data[i]["logical_form"] != "":
                input = "Question: " + data[i]["question"]
                entry = {"instruction": instruction, "input": input, "output": data[i]["logical_form"], "history": []}
                output_entries.append(entry)
    random.shuffle(output_entries)
    return output_entries


if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Process dataset.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--split', type=str, default="train", required=True, choices=['train', 'test', 'dev'],
                        help="Dataset split (train or test).")
    args = parser.parse_args()

    # load data
    if args.dataset_type == "WebQSP":
        path = "../data/original/" + args.dataset_type + "/" + args.dataset_type + "." + args.split + ".json"
        path = os.path.abspath(path)
    elif args.dataset_type == "CWQ":
        path = "../data/original/" + args.dataset_type + "/ComplexWebQuestions_" + args.split + ".json"
        path = os.path.abspath(path)
    elif args.dataset_type == "FreebaseQA":
        if args.split == "test":
            path = "../data/original/" + args.dataset_type + "/" + args.dataset_type + "-eval.json"
        else:
            path = "../data/original/" + args.dataset_type + "/" + args.dataset_type + "-" + args.split + ".json"
    data = load_json(path)

    # extract data
    extracted_data = extract_information(data, args.dataset_type, args.split)
    if args.dataset_type == "FreebaseQA":
        extracted_data = refine_logical_forms(extracted_data)

    # output extracted data
    output_extracted_path = "../data/processed/" + args.dataset_type + "/" + args.dataset_type + "_" + args.split + "_extracted.json"
    output_extracted_path = os.path.abspath(output_extracted_path)
    store_json(extracted_data, output_extracted_path)

    # output train dataset
    if args.split == "train":
        train_data = generate_train_dataset(extracted_data, args.dataset_type)
        output_dataset_path = "../generation/input/" + args.dataset_type + "/train_data/train_data_entries.json"
        output_dataset_path = os.path.abspath(output_dataset_path)
        store_json(train_data, output_dataset_path)
