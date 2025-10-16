import json
import os
import sys
import itertools
import time
import argparse
path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
path = "../utils"
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json, store_json, load_json_1_line, load_txt
from utils.sparql_execution import execute_query_with_odbc,get_label_with_odbc
from utils.logic_form_util import lisp_to_sparql
from utils.eval_final import denormalize_s_expr_new,denormalize_s_expr_new_,execute_normed_s_expr_from_label_maps
from entity_retrieval import surface_index_memory

def convert_to_query_(logical_form, map, name_dict):
    # logical_form_denormed = denormalize_s_expr_new(logical_form, map, name_dict, surface_index)[0]
    if ", " in logical_form and " , " not in logical_form:
        logical_form = logical_form.replace(", "," , ")
    logical_form_denormed = denormalize_s_expr_new_(logical_form, map, name_dict)[0]
    logical_form_denormed = logical_form_denormed.replace('( ', '(').replace(' )', ')')
    query = lisp_to_sparql(logical_form_denormed)
    return query

def convert_to_query(logical_form, map, name_dict, surface_index):
    if ", " in logical_form and " , " not in logical_form:
        logical_form = logical_form.replace(", "," , ")
    logical_form_denormed = denormalize_s_expr_new(logical_form, map, name_dict, surface_index)[0]
    logical_form_denormed = logical_form_denormed.replace('( ', '(').replace(' )', ')')
    query = lisp_to_sparql(logical_form_denormed)
    return query

def search_in_freebase(data, golden_data, surface_index,output_path):
    with open(output_path, "a", encoding="utf-8") as file:
        for i in range(0, len(data)):
            print("searching i=", i, "/", len(data))
            reversed_dict = {v: k for k, v in golden_data[i]["golden_entities"].items()}
            entity_label_map = reversed_dict
            logical_forms = data[i]["predicted_logical_forms"]
            if logical_forms == []:
                entry = {"index": data[i]["index"], "question": data[i]["question"],
                         "label_logical_form": data[i]["label_logical_form"], "predict_logical_form": logical_forms,
                         "searched_answers": []}
                json.dump(entry, file)
                file.write("\n")
                file.flush()
            else:
                answers = []
                combined_answers = []
                # entity retrieval
                for j in range(len(logical_forms)):
                    if ", " in logical_forms[j] and " , " not in logical_forms[j]:
                        # llama 3 8b
                        logical_forms[j] = logical_forms[j].replace(", ", " , ")
                    count = 0
                    try:
                        _, answer_ids = execute_normed_s_expr_from_label_maps(logical_forms[j], entity_label_map, {},
                                                                              surface_index)
                        answer = []
                        for ans_id in answer_ids:
                            ans_label = ""
                            if ans_id.startswith("m.") or ans_id.startswith("g."):
                                ans_label = get_label_with_odbc(ans_id)
                            else:
                                answer.append(ans_id)
                            if ans_label == None:
                                answer.append(ans_id)
                            else:
                                answer.append(ans_label)
                        answers.append(answer)
                        combined_answers += answer
                    except Exception as e:

                        print("Error:", e)
                        pass
                entry = {"index": data[i]["index"], "question": data[i]["question"],
                         "label_logical_form": data[i]["label_logical_form"], "predict_logical_form": logical_forms,
                         "searched_answers": answers}
                json.dump(entry, file)
                file.write("\n")
                file.flush()

if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Execute generated logical forms.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    parser.add_argument('--facc1_path', type=str, required=True,
                        help="Path to FACC1 annotation.", default="../entity_retrieval/facc1/")
    args = parser.parse_args()

    # load FACC1
    surface_index = surface_index_memory.EntitySurfaceIndexMemory(
        args.facc1_path + "/entity_list_file_freebase_complete_all_mention",
        args.facc1_path + "/surface_map_file_freebase_complete_all_mention",
        args.facc1_path + "/freebase_complete_all_mention")

    # load data
    golden_path="../data/processed/"+args.dataset_type+"/"+args.dataset_type+"_test_extracted.json"
    golden_path=os.path.abspath(golden_path)
    golden_data=load_json(golden_path)
    path="../generation/output/" + args.dataset_type + "/" + args.dataset_type + "_generated_"+args.model_type+".jsonl"
    path=os.path.abspath(path)
    data=load_json_1_line(path)

    # execute
    output_path="../generation/output/"+args.dataset_type+"/"+args.dataset_type + "_searched_"+args.model_type+".jsonl"
    output_path=os.path.abspath(output_path)
    search_in_freebase(data, golden_data, surface_index,output_path)

