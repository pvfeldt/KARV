import os
import sys
import json
import time
import argparse

path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json, store_json, load_json_1_line, load_txt
from similarity_check.retrieve import load_DPR_model, load_sentence_bert_model, select_BM25_top_k, select_DPR_top_k, \
    select_sentence_bert_top_k


# relation=one relation
# return top-k relations [rel 1, rel 2,...]
def search_relations(relation, all_relations, k):
    processed_relation = relation.replace(".", " ")
    processed_relation = processed_relation.replace("_", " ")
    selected_relations_combined = select_DPR_top_k(model, tokenizer, processed_relation, all_relations, k)
    selected_relations = [row[0] for row in selected_relations_combined]
    return selected_relations


# entity=one entity
# return top-1 entity "ent 1"
def search_entities(entity, entity_dict):
    reverse_entity_dict = {value: key for key, value in entity_dict.items()}
    entity_list = list(entity_dict.values())
    selected_entities_combined = select_DPR_top_k(model, tokenizer, entity, entity_list, 1)
    selected_entity = selected_entities_combined[0][0]
    selected_id = reverse_entity_dict[selected_entity]
    return selected_entity, selected_id


def search_candidate_relation_range(relation, relation_dict, key_num):
    candidate_relations = []
    # search keys
    relation_keys = list(relation_dict.keys())
    candidate_keys = search_relations(relation, relation_keys, key_num)
    # append candidate relations
    for key in candidate_keys:
        candidate_relations += relation_dict[key]
    return candidate_relations


# path=one path={"entity":xxx,"relations":xxx,"direction":xxx}
# return searched_entry={"entity_name":xxx,"entity_id":xxx,"relations":xxx,"direction:xxx}
def search_entities_and_relations(path, all_relations, entity_dict, k, key_num):
    searched_entity, searched_id = search_entities(path["entity"], entity_dict)
    searched_relations = []
    for i in range(len(path["relations"])):
        candidate_relations = search_candidate_relation_range(path["relations"][i], all_relations, key_num)
        searched_relation = search_relations(path["relations"][i], candidate_relations, k)
        searched_relations.append(searched_relation)
    entry = {"entity_name": searched_entity, "entity_id": searched_id, "relations": searched_relations,
             "direction": path["direction"]}
    return entry


# data=one question
def search_for_one_question(data, all_relations, entity_dict, k, key_num):
    # data["predict_paths"][i]=one logical form
    entries_one_question = []
    for i in range(len(data["predict_paths"])):
        # data["predict_paths"][i][j]=one path
        entries_one_lf = []
        for j in range(len(data["predict_paths"][i])):
            entry = search_entities_and_relations(data["predict_paths"][i][j], all_relations, entity_dict, k, key_num)
            entries_one_lf.append(entry)
        entries_one_question.append(entries_one_lf)
    return entries_one_question


# lf_data=all questions
def search_for_all_questions(output_path, lf_data, ref_data, all_relations, k, key_num):
    with open(output_path, "a", encoding="UTF-8") as file:
        interrupt_num = 0
        for i in range(interrupt_num, len(lf_data)):
            print("i=", i)
            sys.stdout.flush()
            ref_index = int(lf_data[i]["index"])
            entity_dict = ref_data[ref_index]["golden_entities"]
            searched_entries = search_for_one_question(lf_data[i], all_relations, entity_dict, k, key_num)
            lf_data[i]["searched_paths"] = searched_entries
            json.dump(lf_data[i], file)
            file.write("\n")
            file.flush()
    return lf_data


if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Compare path elements.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    parser.add_argument('--top_k', type=int, required=True, default=3,
                        help="Top-k value for comparison.")
    parser.add_argument('--keys', type=int, required=True, default=5,
                        help="Category key number to select candidate relation range.")
    parser.add_argument('--retriever_path', type=str, required=True,
                        help="Path of the retriever model.")
    args = parser.parse_args()

    # load data
    ontology_path = "../ontology/domain_dict"
    ontology_path = os.path.abspath(ontology_path)
    relation_data = load_json(ontology_path)
    golden_path = "../data/processed/" + args.dataset_type + "/" + args.dataset_type + "_test_extracted.json"
    golden_path = os.path.abspath(golden_path)
    golden_data = load_json(golden_path)
    path = "../retrieval/output/" + args.dataset_type + "/" + args.dataset_type + "_extracted_" + args.model_type + ".json"
    path = os.path.abspath(path)
    data = load_json(path)

    # load retriever model
    time1 = time.time()
    tokenizer, model = load_DPR_model(args.retriever_path)

    # compare
    output_path = "../retrieval/output/" + args.dataset_type + "/" + args.dataset_type + "_compared_" + args.model_type + ".jsonl"
    output_path=os.path.abspath(output_path)
    compared_results = search_for_all_questions(output_path, data, golden_data, relation_data, args.top_k, args.keys)

    time2 = time.time()
    running_time = time2 - time1
    print("Running time for comparison:", time2 - time1)
