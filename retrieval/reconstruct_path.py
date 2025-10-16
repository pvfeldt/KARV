import os
import sys
import json
import time
import argparse
path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json, store_json, load_json_1_line, load_txt
from utils.sparql_execution import get_label_with_odbc, get_out_relations_with_odbc, get_out_entities_with_odbc, \
    get_in_entities_with_odbc

##### search triplets ######

# path_data=one path
def search_triplets_for_one_path(path_data):
    start_entity = [path_data["entity_id"]]
    relations = path_data["relations"]
    direction = path_data["direction"]
    if len(relations)!=len(direction):
        return {}
    else:
        triplets_dict = {}
        for i in range(len(relations)):
            new_start_entities = []
            triplets_one_hop = []
            for ent in start_entity:
                for rel in relations[i]:
                    if rel[-1]==".":
                        continue
                    if ":" in rel:
                        continue
                    tail_entities = []
                    # define direction
                    if direction[i] == "back":
                        tail_entities = get_in_entities_with_odbc(ent, rel)
                    elif direction[i] == "forward":
                        tail_entities = get_out_entities_with_odbc(ent, rel)
                    if tail_entities != []:
                        new_start_entities += tail_entities
                        triplet = [ent, rel, tail_entities]
                        triplets_one_hop.append(triplet)
            start_entity = new_start_entities
            triplets_dict[i] = triplets_one_hop
        return triplets_dict

# path_data=one question(many logical forms, many paths)
def search_triplets_for_one_question(path_data):
    paths = path_data["searched_paths"]
    triplets_one_question = []
    # paths[i]=one logical form
    for i in range(len(paths)):
        triplets_one_lf = []
        # paths[i][j]=one path
        for j in range(len(paths[i])):
            triplets_one_path = search_triplets_for_one_path(paths[i][j])
            triplets_one_lf.append(triplets_one_path)
        triplets_one_question.append(triplets_one_lf)
    return triplets_one_question

# path_data=all questions
def search_triplets_for_all_questions(output_path,path_data):
    with open(output_path, "a",encoding="UTF-8") as file:
        interrupt_num=0
        for i in range(interrupt_num,len(path_data)):
            print("i=", i)
            triplets = search_triplets_for_one_question(path_data[i])
            path_data[i]["triplets"] = triplets
            json.dump(path_data[i], file)
            file.write("\n")
            file.flush()
    return path_data

##### link reasoning paths ######

# dict=name dict
def find_name(entity_id):
    name = get_label_with_odbc(entity_id)
    if name == None:
        name = entity_id
    return name

# link the triplets for one path
def link_triplets(triplets_dict):
    output_entries = {}
    # calculate hop number
    # data["triplets"]={"0":[],"1":[]}
    hop = len(triplets_dict)
    output_entries["0"] = triplets_dict["0"]
    if hop > 1:
        for i in range(1, hop):
            # triplets_dict[i]=[[entity 1,relation 1,[entity 2],...]
            current_triplets = triplets_dict[str(i)]
            previous_triplets = triplets_dict[str(i - 1)]
            triplets_tmp = []
            for j in range(len(current_triplets)):
                for k in range(len(previous_triplets)):
                    if current_triplets[j][0] in previous_triplets[k][2]:
                        triplets_tmp.append([previous_triplets[k], current_triplets[j]])
            output_entries[str(i)] = triplets_tmp
    return output_entries


# generate context for one path
def generate_context(triplets_dict):
    output_entries = {}
    context_entries = {}
    hop = len(triplets_dict)
    # hop=0 (one hop)
    context_one_hop = []
    for i in range(len(triplets_dict["0"])):
        context = triplets_dict["0"][i][0] + "->" + triplets_dict["0"][i][1] + "->"
        end_entity = ""
        for ans in triplets_dict["0"][i][2]:
            end_entity += "#" + ans
        end_entity = end_entity[1:]
        context += end_entity
        context_one_hop.append(context)
    context_entries["0"] = context_one_hop
    output_entries["0"] = context_one_hop
    # hop>=1 (multi hop)
    for i in range(1, hop):
        triplets = triplets_dict[str(i)]
        context_each_hop = []
        # triplets[j]=[[entity 1,relation 1,[entity 2],[entity 2,relation 2,[entity 3]]]
        for j in range(len(triplets)):
            context = triplets[j][0][0] + "->" + triplets[j][0][1] + "->" + triplets[j][1][0] + "->" + triplets[j][1][
                1] + "->"
            end_entity = ""
            for ans in triplets[j][1][2]:
                end_entity += "#" + ans
            end_entity = end_entity[1:]
            context += end_entity
            context_each_hop.append(context)
        context_entries[str(i)] = context_each_hop
        output_entries[str(i)] = context_each_hop

    # link the context with previous,previous context
    if hop > 1:
        for i in range(2, hop):
            current_context = context_entries[str(i)]
            previous_context = context_entries[str(i - 2)]
            new_context = []
            for j in range(len(current_context)):
                split_current_start_entity = current_context[j].split("->")[0]
                for k in range(len(previous_context)):
                    split_previous_end_entity = previous_context[k].split("->")[-1]
                    if split_current_start_entity in split_previous_end_entity:
                        previous_context_copied = previous_context[k].replace(split_previous_end_entity, "")
                        context = previous_context_copied + current_context[j]
                        new_context.append(context)
            output_entries[str(i)] = new_context
    return output_entries


# generate context for one path
# context= entity 1->relation 1->entity 2
def convert_context_id_to_name(context):
    split_context = context.split("->")
    new_context = ""
    for ent_id in split_context:
        # relation
        if ent_id.count(".") >= 2 and "," not in ent_id and "#" not in ent_id:
            ent_name = ent_id
        # entity
        else:
            ent_name = find_name(ent_id)
            if "#" in ent_id:
                split_answer = ent_id.split("#")
                ent_name = ""
                for ans in split_answer:
                    e_name = find_name(ans)
                    ent_name += "#" + e_name
                ent_name = ent_name[1:]
        new_context += "->" + ent_name
    new_context = new_context[2:]
    return new_context


def generate_context_with_name(triplets_dict):
    output_entries = {}
    hop = len(triplets_dict)
    for i in range(hop):
        context_each_hop = triplets_dict[str(i)]
        new_context_each_hop = []
        for con in context_each_hop:
            new_con = convert_context_id_to_name(con)
            new_context_each_hop.append(new_con)
        output_entries[str(i)] = new_context_each_hop
    return output_entries


# extract context for one question
def extract_context_for_one_question(data):
    context_entries = []
    # data[triplets"][i]=one logical form
    for i in range(len(data["triplets"])):
        context_one_path = []
        # data["triplets"][i][j]=one path
        for j in range(len(data["triplets"][i])):
            triplets_dict = data["triplets"][i][j]
            if triplets_dict != {}:
                # 1. link the triplets
                linked_triplets = link_triplets(triplets_dict)
                # 2. generate contexts
                context = generate_context(linked_triplets)
                # 3. replace entity ids with entity name
                new_context = generate_context_with_name(context)
                context_one_path.append(new_context)
            else:
                context_one_path.append([])
        context_entries.append(context_one_path)
    return context_entries


# extract useful context for one question
def filter_context_for_one_question(data):
    # data[i]=one logical form
    context_entries = []
    for i in range(len(data)):
        # data[i][j]=one path
        context_one_lf = []
        for j in range(len(data[i])):
            context_dict = data[i][j]
            len_dict = len(context_dict)
            context_one_path = []
            for num in range(len_dict):
                index = str(len_dict - 1 - num)
                if context_dict[index] != []:
                    context_one_path += context_dict[index]
                    break
            context_one_lf.append(context_one_path)
        context_entries.append(context_one_lf)
    return context_entries


# extract useful context for all questions
def extract_context_for_all_questions(output_path,data):
    output_entries = []
    with open(output_path, "a",encoding="UTF-8") as file:
        interrupt_num =0
        for i in range(interrupt_num, len(data)):
            print("i=", i, "/", len(data))
            sys.stdout.flush()
            if data[i]["triplets"] == []:
                continue
            new_context = extract_context_for_one_question(data[i])
            new_context = filter_context_for_one_question(new_context)
            entry = {"index": data[i]["index"], "question": data[i]["question"], "context": new_context}
            json.dump(entry, file)
            file.write("\n")
            file.flush()
            output_entries.append(entry)
    return output_entries


if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Reconstruct reasoning paths.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    args = parser.parse_args()

    # load data
    path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_compared_"+args.model_type+".jsonl"
    path=os.path.abspath(path)
    data=load_json_1_line(path)

    # search triplets
    time1=time.time()
    output_triplet_path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_triplets_"+args.model_type+".jsonl"
    output_triplet_path=os.path.abspath(output_triplet_path)
    searched_results=search_triplets_for_all_questions(output_triplet_path,data)
    time2=time.time()
    running_time=time2-time1
    print("Running time for retrieval:",running_time)

    # link reasoning paths
    searched_results=load_json_1_line(output_triplet_path)
    output_context_path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_paths_"+args.model_type+".jsonl"
    output_context_path=os.path.abspath(output_context_path)
    context_data=extract_context_for_all_questions(output_context_path,searched_results)