import os
import sys
import json

path = ".."
abs_path = os.path.abspath(path)
sys.path.append(abs_path)
from utils.json_utils import load_json, store_json, load_json_1_line,load_txt
from utils.sparql_execution import get_out_relations_with_odbc, get_out_entities_with_odbc
import logging
from typing import List, Dict
from rank_bm25 import BM25Okapi
from transformers import AutoTokenizer,AutoModel
import torch
import numpy as np
import pandas as pd
import faiss
from transformers import DPRQuestionEncoder, DPRQuestionEncoderTokenizer


# calculate similarity
def compute_similarity(v1,v2):
    sim=v1.dot(v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return sim

# BM25: tokenize->compute similarity
def select_BM25_top_k(label_relation,candidate_relation,k):
    # translate to corpus style
    corpus_relation=[]
    for rel in candidate_relation:
        new_rel=rel.replace("."," ")
        new_rel=new_rel.replace("_"," ")
        corpus_relation.append(new_rel)
    tokenized_corpus = [doc.split(" ") for doc in corpus_relation]
    # search
    bm25 = BM25Okapi(tokenized_corpus)
    query=label_relation
    tokenized_query = query.split(" ")
    doc_scores = bm25.get_scores(tokenized_query)
    # order the relations according to the score
    combined_list=[[candidate_relation[i],doc_scores[i]] for i in range(len(candidate_relation))]
    sorted_combined_list = sorted(combined_list, key=lambda x: x[1],reverse=True)
    # return the top-k relations
    total_list_length=len(sorted_combined_list)
    output_relation=[]
    if k<total_list_length:
        output_relation=sorted_combined_list[:k]
    else:
        output_relation=sorted_combined_list
    return output_relation

# DPR: encode->compute similarity
def select_DPR_top_k(model,tokenizer,label_relation,candidate_relation,k):
    # translate to corpus style
    corpus_relation=[]
    for rel in candidate_relation:
        new_rel=rel.replace("."," ")
        new_rel=new_rel.replace("_"," ")
        corpus_relation.append(new_rel)
    # encode
    encoded_relation=tokenizer(corpus_relation,padding=True,truncation=True,return_tensors="pt")
    encoded_label=tokenizer([label_relation],padding=True,truncation=True,return_tensors="pt")
    with torch.no_grad():
        model_output_relation=model(**encoded_relation)
        model_output_label=model(**encoded_label)
    relation_embeddings=model_output_relation.pooler_output
    label_embedding=model_output_label.pooler_output
    # count similarity
    scores=[]
    for rel_emb in relation_embeddings:
        score=compute_similarity(label_embedding[0],rel_emb)
        scores.append(score)

    # order the relations according to the score
    combined_list=[[candidate_relation[i],float(scores[i])] for i in range(len(candidate_relation))]
    sorted_combined_list = sorted(combined_list, key=lambda x: x[1],reverse=True)
    # return the top-k relations
    total_list_length=len(sorted_combined_list)
    output_relation=[]
    if k<total_list_length:
        output_relation=sorted_combined_list[:k]
    else:
        output_relation=sorted_combined_list
    return output_relation

# sentence BERT: encode->compute similarity
def select_sentence_bert_top_k(model,tokenizer,label_relation,candidate_relation,k):
    # translate to corpus style
    corpus_relation=[]
    for rel in candidate_relation:
        new_rel=rel.replace("."," ")
        new_rel=new_rel.replace("_"," ")
        corpus_relation.append(new_rel)
    # encode
    encoded_relation=tokenizer(corpus_relation,padding=True,truncation=True,return_tensors="pt")
    encoded_label=tokenizer([label_relation],padding=True,truncation=True,return_tensors="pt")
    with torch.no_grad():
        model_output_relation=model(**encoded_relation)
        model_output_label=model(**encoded_label)
    relation_embeddings=model_output_relation.pooler_output
    label_embedding=model_output_label.pooler_output
    # count similarity
    scores=[]
    for rel_emb in relation_embeddings:
        score=compute_similarity(label_embedding[0],rel_emb)
        scores.append(score)

    # order the relations according to the score
    combined_list=[[candidate_relation[i],float(scores[i])] for i in range(len(candidate_relation))]
    sorted_combined_list = sorted(combined_list, key=lambda x: x[1],reverse=True)
    # return the top-k relations
    total_list_length=len(sorted_combined_list)
    output_relation=[]
    if k<total_list_length:
        output_relation=sorted_combined_list[:k]
    else:
        output_relation=sorted_combined_list
    return output_relation

def load_DPR_model(model_path):
    tokenizer = DPRQuestionEncoderTokenizer.from_pretrained(model_path)
    model = DPRQuestionEncoder.from_pretrained(model_path)
    return tokenizer,model

def load_sentence_bert_model(model_path):
    tokenizer=AutoTokenizer.from_pretrained(model_path)
    model=AutoModel.from_pretrained(model_path)
    return tokenizer,model

