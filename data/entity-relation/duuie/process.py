import json
import fire
from collections import defaultdict

import numpy as np
from transformers import AutoTokenizer

def count_sentence_num(source_file):
    sents = set()
    with open(source_file, 'r', encoding='utf-8') as fin:
        for line in fin:
            a_line = json.loads(line.strip())
            sentText = a_line['sentText']
            sents.add(sentText)
        print(f"Sentence Number in {source_file}: {len(sents)}")

# add gold arguments' label info, as a part of input
# 0: Outside, 1: Argument
def add_gold_label_sequence_field(sent):
    if "tokens" in sent:
        seq_len = len(sent['tokens'])
    else:
        seq_len = len(sent['sentText'].split(' '))
    label_sequence = [0] * seq_len
    entityMentions = sent["entityMentions"]

    for entity in entityMentions:
        if entity['label'][0] == 'A':
            start, end = entity['offset']
            for i in range(start, end):
                label_sequence[i] = 1

    sent['arg_label_seq'] = label_sequence

def add_wordpiece_fields(sent, tokenizer):
    """add wordpiece related fields
    """

    cls, sep = tokenizer.cls_token, tokenizer.sep_token
    
    wordpiece_tokens_index, wordpiece_tokens = [], [cls]
    if "tokens" in sent:
        tokens = sent['tokens']
    else:
        tokens = sent['sentText'].split(' ')
    
    cur_index = 0
    for token in tokens:
        tokenized_token = list(tokenizer.tokenize(token))
        wordpiece_tokens.extend(tokenized_token)
        wordpiece_tokens_index.append([cur_index, cur_index + len(tokenized_token)])
        cur_index += len(tokenized_token)
    wordpiece_tokens.append(sep)
    assert len(wordpiece_tokens_index) == len(tokens)

    wordpiece_segment_ids = [0] * len(wordpiece_tokens)
    assert len(wordpiece_tokens) == len(wordpiece_segment_ids)
    
    sent['wordpiece_tokens'] = wordpiece_tokens
    sent['wordpieceTokensIndex'] = wordpiece_tokens_index
    sent['wordpieceSegmentIds'] = wordpiece_segment_ids
    return sent

def add_joint_label(sent, ent_rel_id):
    """add_joint_label add joint labels table for sentences
    """

    none_id = ent_rel_id['None']
    if 'tokens' in sent:
        seq_len = len(sent['tokens'])
    else:
        seq_len = len(sent['sentText'].split(' '))

    label_matrix = [[none_id for j in range(seq_len)] for i in range(seq_len)]
    ent2offset = {}
    for ent in sent['entityMentions']:
        ent2offset[ent['emId']] = ent['offset']
        for i in range(ent['offset'][0], ent['offset'][1]):
            for j in range(ent['offset'][0], ent['offset'][1]):
                #assert label_matrix[i][j] == 0, "Exist entity overlapping!"
                label_matrix[i][j] = ent_rel_id[ent['label']]
        
    for rel in sent['relationMentions']:
        for i in range(ent2offset[rel['em1Id']][0], ent2offset[rel['em1Id']][1]):
            for j in range(ent2offset[rel['em2Id']][0], ent2offset[rel['em2Id']][1]):
                #assert label_matrix[i][j] == 0, "Exist relation overlapping!"
                label_matrix[i][j] = ent_rel_id[rel['label']]
    
    assert len(label_matrix) == seq_len
    sent['jointLabelMatrix'] = label_matrix

def process(source_file, target_file, pretrained_model, ent_rel_file = None, add_gold_label=False):
    auto_tokenizer = AutoTokenizer.from_pretrained(pretrained_model)
    print("Load {} tokenizer successfully.".format(pretrained_model))

    # load label info: ent_type + rel_type
    if ent_rel_file != None:
        ent_rel_id = json.load(open(ent_rel_file, 'r', encoding='utf-8'))["id"]
    else:
        ent_rel_id = {'None': 0}

    with open(source_file, 'r', encoding='utf-8') as fin, open(target_file, 'w', encoding='utf-8') as fout:
        for i, line in enumerate(fin):
            print(f"Process Line{i + 1}")
            sent = json.loads(line.strip())
            
            add_wordpiece_fields(sent, auto_tokenizer)
            add_joint_label(sent, ent_rel_id)
            assert 'jointLabelMatrix' in sent.keys()
            if add_gold_label:
                add_gold_label_sequence_field(sent)
                assert 'arg_label_seq' in sent.keys()
            
            print(json.dumps(sent, ensure_ascii=False), file=fout)
            
if __name__ == '__main__':
    fire.Fire({"process": process})
