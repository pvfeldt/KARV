import json
import os
import sys
import argparse
path = "../utils"
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from json_utils import load_json_1_line, load_json, store_json

##### refine #####

# delete the repeated context (path)
# data=one path
def delete_repeated_context(data):
    data=list(set(data))
    return data

# delete loop
def delete_loop(data):
    new_context=[]
    for i in range(len(data)):
        split_context=data[i].split("->")
        ent_split=[]
        for split in split_context:
            if split.count(".")<2:
                ent_split.append(split)
        processed_split=list(set(ent_split))
        # if length!=, a loop exists
        if len(processed_split)==len(ent_split):
            new_context.append(data[i])
    return new_context

# delete the start entity in the tail entity(if exists)
def delete_repeated_entity(data):
    for i in range(len(data)):
        start_entity=data[i].split("->")[0]
        tail_entity=data[i].split("->")[-1]
        new_tail_entity=""
        if start_entity in tail_entity:
            if start_entity+"#" in tail_entity and " "+start_entity+"#" not in tail_entity:
                new_tail_entity=tail_entity.replace(start_entity+"#","")
            elif "#"+start_entity in tail_entity and "#"+start_entity+" " not in tail_entity:
                new_tail_entity=tail_entity.replace("#"+start_entity,"")
            else:
                break
            data[i]=data[i].replace(tail_entity,new_tail_entity)
    return data

# delete the repeated last relation
def delete_repeated_relation(data):
    for i in range(len(data)):
        split_context=data[i].split("->")
        last_relation=split_context[-2]
        last_entity=split_context[-1]
        test_split_context=split_context[:-2]
        if last_relation in test_split_context:
            repeated_context="->"+last_relation+"->"+last_entity
            data[i]=data[i].replace(repeated_context,"")
    return data

def delete_repeated_from_question(data,question):
    new_context=[]
    for i in range(len(data)):
        tail_entity = data[i].split("->")[-1]
        split_tail_entity=tail_entity.split(" ")
        # if repeated,flag=1
        flag=0
        for ans in split_tail_entity:
            if ans.lower() in question:
                flag=1
        if flag==0:
            new_context.append(data[i])
    return new_context


# data=all questions
def post_process(data):
    for i in range(len(data)):
        print("i=",i)
        # data[i]["context"][j]=one logical form
        for j in range(len(data[i]["context"])):
            # data[i]["context"][j][k]=one path
            new_context_list=[]
            for k in range(len(data[i]["context"][j])):
                new_context=delete_repeated_context(data[i]["context"][j][k])
                new_context=delete_loop(new_context)
                new_context=delete_repeated_entity(new_context)
                new_context=delete_repeated_relation(new_context)
                # new_context=delete_repeated_from_question(new_context,data[i]["question"])
                if new_context!=[]:
                    new_context_list.append(new_context)
            data[i]["context"][j]=new_context_list
    return data

##### intersect & vote #####

def get_most_frequent_element(data):
    most_common=[]
    items=list(set(data))
    # equal frequency, return the original list
    if len(items)==len(data):
        most_common=data
    # not equal, return the most frequent item
    else:
        count=[]
        for item in items:
            count_item=data.count(item)
            count.append(count_item)
        max_value=max(count)
        indexes = [i for i, value in enumerate(count) if value == max_value]
        for index in indexes:
            most_common.append(items[index])
    return most_common

# data=one path
def extract_entities(data):
    output_entries=[]
    for i in range(len(data)):
        split_context=data[i].split("->")
        start_entity=split_context[0]
        tail_entity=split_context[-1]
        mid_entity=[]
        for split in split_context[1:-2]:
            if split.count(".")<2:
                mid_entity.append(split)
            if split.count(".")>=2 and "#" in split:
                mid_entity.append(split)
        entity={"start_entity":start_entity,"tail_entity":tail_entity,"mid_entity":mid_entity}
        output_entries.append(entity)
    return output_entries

# data=one question
def extract_entities_for_one_logical_form(data):
    output_entries=[]
    for i in range(len(data)):
        entity_list=extract_entities(data[i])
        output_entries.append(entity_list)
    return output_entries

# data=one logical form
def intersect_context(data):
    # the items in it [path 0,index 0,path 1,index 1]
    intersection=[]
    # 0. first compare the tail entities
    for i in range(len(data)):
        for j in range(len(data[i])):
            entity_1=data[i][j]["tail_entity"]
            for k in range(i+1,len(data)):
                for m in range(len(data[k])):
                    entity_2=data[k][m]["tail_entity"]
                    if entity_1 in entity_2 or entity_2 in entity_1:
                        indexes=[i,j,k,m]
                        intersection.append(indexes)
    if intersection==[]:
        # 1. if no intersection between tail entities, compare the mid entities
        for i in range(len(data)):
            for j in range(len(data[i])):
                tail_entity_1=data[i][j]["tail_entity"]
                mid_entity_1=data[i][j]["mid_entity"]
                for k in range(i+1,len(data)):
                    for m in range(len(data[k])):
                        tail_entity_2=data[k][m]["tail_entity"]
                        mid_entity_2=data[k][m]["mid_entity"]
                        # condition 1: one tail entity in mid entities
                        if tail_entity_1 in mid_entity_2 or tail_entity_2 in mid_entity_1:
                            indexes = [i, j, k, m]
                            intersection.append(indexes)
                        # condition 2: multiple tail entities in mid entities or multiple tail entities have intersection
                        split_tail_1=tail_entity_1.split("#")
                        split_tail_2=tail_entity_2.split("#")
                        inter=list(set(split_tail_1)&set(mid_entity_2))
                        if inter!=[]:
                            indexes=[i,j,k,m]
                            intersection.append(indexes)
                        inter=list(set(split_tail_2)&set(mid_entity_1))
                        if inter!=[]:
                            indexes=[i,j,k,m]
                            intersection.append(indexes)
                        inter = list(set(split_tail_1) & set(split_tail_2))
                        if inter != []:
                            indexes = [i, j, k, m]
                            intersection.append(indexes)
    return intersection

# data=all questions
def reorganize_context(data):
    for i in range(len(data)):
        print("i=",i)
        for j in range(len(data[i]["context"])):
            if len(data[i]["context"][j])>1:
                entity_entry=extract_entities_for_one_logical_form(data[i]["context"][j])
                intersection=intersect_context(entity_entry)
                new_context_list=[]
                for index in intersection:
                    [index_x1,index_y1,index_x2,index_y2]=index
                    new_context_list.append(data[i]["context"][j][index_x1][index_y1])
                    new_context_list.append(data[i]["context"][j][index_x2][index_y2])
                    new_context_list=list(set(new_context_list))
                data[i]["context"][j]=new_context_list
            elif len(data[i]["context"][j])==1:
                data[i]["context"][j]=data[i]["context"][j][0]
    return data

# data=all questions
def select_answers(data):
    for i in range(len(data)):
        print("i=",i)
        answers=[]
        for j in range(len(data[i]["context"])):
            answer_list=[]
            for con in data[i]["context"][j]:
                tail_entity=con.split("->")[-1]
                split_ans_list=[]
                # multiple answers
                if "#" in tail_entity:
                    split_ent=tail_entity.split("#")
                    for ent in split_ent:
                        if ent.startswith("g.") or ent.startswith("m."):
                            continue
                        elif ent.lower() in data[i]["question"]:
                            continue
                        split_ans_list.append(ent)
                    split_ans_list=list(set(split_ans_list))
                    answer_list+=split_ans_list
                # single answer
                else:
                    if tail_entity.lower() not in data[i]["question"]:
                        if not tail_entity.startswith("m.") and not tail_entity.startswith("g."):
                            answer_list.append(tail_entity)
            new_answer_list=get_most_frequent_element(answer_list)
            answers.append(new_answer_list)
        data[i]["initial_answer"]=answers
    return data

def generate_final_answer(data):
    for i in range(len(data)):
        print("i=",i)
        final_answers=[]
        for j in range(len(data[i]["initial_answer"])):
            final_answers+=data[i]["initial_answer"][j]
        final_answers=get_most_frequent_element(final_answers)
        new_final=[]
        for ans in final_answers:
            if ans.startswith("g.") or ans.startswith("m."):
                continue
            else:
                new_final.append(ans)
        final_answers=new_final
        data[i]["final_answer"]=final_answers
    return data

if __name__ == '__main__':
    # add args
    parser = argparse.ArgumentParser(description="Perform intersection and voting.")
    parser.add_argument('--dataset_type', type=str, default="WebQSP", required=True,
                        help="Type of dataset (e.g., 'WebQSP').")
    parser.add_argument('--model_type', type=str, required=True,
                        help="Model type (e.g., 'llama27').")
    args = parser.parse_args()

    # load data
    path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_paths_"+args.model_type+".jsonl"
    path=os.path.abspath(path)
    data=load_json_1_line(path)

    # refine the reasoning paths
    refined_data=post_process(data)
    refined_path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_refined_paths_"+args.model_type+".json"
    refined_path=os.path.abspath(refined_path)
    store_json(refined_data,refined_path)

    # intersect and vote
    new_data=reorganize_context(refined_data)
    new_data=select_answers(new_data)
    new_data=generate_final_answer(new_data)
    output_path="../retrieval/output/"+args.dataset_type+"/"+args.dataset_type+"_final_results_"+args.model_type+".json"
    output_path=os.path.abspath(output_path)
    store_json(new_data,output_path)
