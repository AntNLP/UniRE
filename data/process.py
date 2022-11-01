import json
import fire

import numpy as np
from transformers import AutoTokenizer


def add_cross_sentence(sentences, tokenizer, max_length=200):
    """add_cross_sentence add cross sentences with adding equal number of
    left and right context tokens.
    """

    new_sents = []
    all_tokens = []
    sent_lens = []
    last_id = sentences[0]['sentId'] - 1
    article_id = sentences[0]['articleId']

    for s in sentences:
        assert s['articleId'] == article_id
        assert s['sentId'] > last_id
        last_id = s['sentId']
        tokens = s['sentText'].split(' ')
        all_tokens.extend(tokens)
        sent_lens.append(len(tokens))

    cur_pos = 0
    for sent, sent_len in zip(sentences, sent_lens):
        if max_length > sent_len:
            context_len = (max_length - sent_len) // 2
            left_context = all_tokens[max(cur_pos - context_len, 0):cur_pos]
            right_context = all_tokens[cur_pos + sent_len:cur_pos + sent_len + context_len]
        else:
            left_context = []
            right_context = []

        cls = tokenizer.cls_token
        sep = tokenizer.sep_token

        wordpiece_tokens = [cls]
        for token in left_context:
            tokenized_token = list(tokenizer.tokenize(token))
            wordpiece_tokens.extend(tokenized_token)

        for token in right_context:
            tokenized_token = list(tokenizer.tokenize(token))
            wordpiece_tokens.extend(tokenized_token)
        wordpiece_tokens.append(sep)

        context_len = len(wordpiece_tokens)
        wordpiece_segment_ids = [0] * context_len

        wordpiece_tokens_index = []
        cur_index = len(wordpiece_tokens)
        for token in sent['sentText'].split(' '):
            tokenized_token = list(tokenizer.tokenize(token))
            wordpiece_tokens.extend(tokenized_token)
            wordpiece_tokens_index.append([cur_index, cur_index + len(tokenized_token)])
            cur_index += len(tokenized_token)
        wordpiece_tokens.append(sep)

        wordpiece_segment_ids += [1] * (len(wordpiece_tokens) - context_len)

        new_sent = {
            'articleId': sent['articleId'],
            'sentId': sent['sentId'],
            'sentText': sent['sentText'],
            'entityMentions': sent['entityMentions'],
            'relationMentions': sent['relationMentions'],
            'wordpieceSentText': " ".join(wordpiece_tokens),
            'wordpieceTokensIndex': wordpiece_tokens_index,
            'wordpieceSegmentIds': wordpiece_segment_ids
        }
        new_sents.append(new_sent)

        cur_pos += sent_len

    return new_sents


def add_joint_label(sent, ent_rel_info):
    """add_joint_label add joint labels for sentences
    """
    ent_rel_id = ent_rel_info['id']
    none_id = ent_rel_id['None']
    if 'tokens' in sent:
        sentence_length = len(sent['tokens'])
    else:
        sentence_length = len(sent['sentText'].split(' '))
    
    label_matrix = [[none_id for j in range(sentence_length)] for i in range(sentence_length)]
    label_matrix = np.array(label_matrix)
    ent2offset = {}
    for ent in sent['entityMentions']:
        ent2offset[ent['emId']] = ent['offset']
        label_matrix[ent['offset'][0]: ent['offset'][1]][ent['offset'][0]: ent['offset'][1]] = ent_rel_id[ent['label']]

    for rel in sent['relationMentions']:
        label_matrix[ent2offset[rel['em1Id']][0]: ent2offset[rel['em1Id']][1]][ent2offset[rel['em2Id']][0]: ent2offset[rel['em2Id']][1]] = ent_rel_id[rel['label']]
        if ent_rel_id[rel['label']] in ent_rel_info['symmetric']:
            label_matrix[ent2offset[ent2offset[rel['em2Id']][0]: ent2offset[rel['em2Id']][1]][rel['em1Id']][0]: ent2offset[rel['em1Id']][1]] = ent_rel_id[rel['label']]

        # for i in range(ent2offset[rel['em1Id']][0], ent2offset[rel['em1Id']][1]):
        #     for j in range(ent2offset[rel['em2Id']][0], ent2offset[rel['em2Id']][1]):
        #         label_matrix[i][j] = ent_rel_id[rel['label']]
        #         if ent_rel_id[rel['label']] in ent_rel_info['symmetric']:
        #             label_matrix[j][i] = ent_rel_id[rel['label']]

    sent['jointLabelMatrix'] = label_matrix.tolist()

def add_joint_label_with_BItag(sent, ent_rel_info):
    """add_joint_label add joint labels table for sentences
    """

    none_id = ent_rel_info['id']['None']
    if 'tokens' in sent:
        sentence_length = len(sent['tokens'])
    else:
        sentence_length = len(sent['sentText'].split(' '))

    label_matrix = [[none_id for j in range(sentence_length)] for i in range(sentence_length)]
    label_matrix = np.array(label_matrix)
    ent2offset = {}
    for ent in sent['entityMentions']:
        ent2offset[ent['emId']] = ent['offset']
        st, end = ent['offset'][0], ent['offset'][1] 
        label_matrix[st][st] = ent_rel_info['id']["B-" + ent['label']]
        for i in range(st + 1, end):
            label_matrix[i][i] = ent_rel_info['id']["I-" + ent['label']]
        ent['label'] = "B-" + ent['label']

    for rel in sent['relationMentions']:
        # for i in range(ent2offset[rel['em1Id']][0], ent2offset[rel['em1Id']][1]):
        #     for j in range(ent2offset[rel['em2Id']][0], ent2offset[rel['em2Id']][1]):
        #         #assert label_matrix[i][j] == 0, "Exist relation overlapping!"
        #         label_matrix[i][j] = ent_rel_info['id'][rel['label']]
        #         if ent_rel_info['id'][rel['label']] in ent_rel_info['symmetric']:
        #             label_matrix[j][i] = ent_rel_info['id'][rel['label']]
                
        label_matrix[ent2offset[rel['em1Id']][0]: ent2offset[rel['em1Id']][1]][ent2offset[rel['em2Id']][0]: ent2offset[rel['em2Id']][1]] = ent_rel_info['id'][rel['label']]
        if ent_rel_info['id'][rel['label']] in ent_rel_info['symmetric']:
            label_matrix[ent2offset[ent2offset[rel['em2Id']][0]: ent2offset[rel['em2Id']][1]][rel['em1Id']][0]: ent2offset[rel['em1Id']][1]] = ent_rel_info['id'][rel['label']]

    sent['jointLabelMatrix'] = label_matrix.tolist()

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

def get_ent_rel_file(ent_rel_file, data_file_path, data_parts=['train.json', 'dev.json', 'test.json', 'val.json']):
    ent_rel_labels = dict()
    ent_labels = defaultdict(int)
    rel_labels = defaultdict(int)
    
    for data_part in data_parts:
        data_file = os.path.join(data_file_path, data_part)
        if os.path.exists(data_file):
            with open(data_file, "r") as fin:
                for line in fin:
                    ins = json.loads(line.strip())
                    entityMentions, relationMentions = ins['entityMentions'], ins['relationMentions']
                    for entity in entityMentions:
                        ent_labels[entity['label']] += 1
                    for rel in relationMentions:
                        rel_labels[rel['label']] += 1

    with open(ent_rel_file, "w", encoding='utf-8') as fout:
        ent_rel_labels['id'] = {}
        ent_rel_labels['entity'] = []
        ent_rel_labels['relation'] = []
        ent_rel_labels['symmetric'] = []
        ent_rel_labels['asymmetric'] = []
        ent_rel_labels['count'] = []

        # process None type
        ent_rel_labels['id']['None'] = 0
        ent_rel_labels['count'].append(0)
        if "None" in ent_labels:
            ent_rel_labels['count'][0] += ent_labels['None']
            del ent_labels['None']
        if "None" in rel_labels:
            ent_rel_labels['count'][0] += rel_labels['None']
            del rel_labels['None']

        # default: all entity types are symmetric
        cnt = 1
        for ent_label, ent_count in ent_labels.items():
            ent_rel_labels['id'][ent_label] = cnt
            ent_rel_labels['entity'].append(cnt)
            ent_rel_labels['symmetric'].append(cnt)
            ent_rel_labels['count'].append(ent_count)
            cnt += 1
        
        # default: all relation types are asymmetric
        relabel_labels = {}
        for rel_label, rel_count in rel_labels.items():
            # rename the same rel label with the entity 
            if rel_label in ent_rel_labels['id']:
                relabel_labels[rel_label] = rel_label + "_关系类型"
                rel_label = relabel_labels[rel_label]

            ent_rel_labels['id'][rel_label] = cnt
            ent_rel_labels['relation'].append(cnt)
            ent_rel_labels['asymmetric'].append(cnt)
            ent_rel_labels['count'].append(rel_count)
            cnt += 1

        print(json.dumps(ent_rel_labels, indent=4, ensure_ascii=False), file=fout)

    # regenerate the data file because of the homonymous label
    if relabel_labels:
        for data_part in data_parts:
            data_file = os.path.join(data_file_path, data_part)
            if os.path.exists(data_file):
                relabel_data_file = os.path.join(data_file_path, data_part.rsplit('.json')[0]+'_relabel.json')
                with open(data_file, "r") as fin, open(relabel_data_file, "w") as fout:
                    for line in fin:
                        ins = json.loads(line.strip())
                        relationMentions = ins['relationMentions']
                        for rel in relationMentions:
                            if rel['label'] in relabel_labels:
                                rel['label'] = relabel_labels[rel['label']]
                        
                        print(json.dumps(ins, ensure_ascii=False), file=fout)

def process(source_file, ent_rel_file, target_file, pretrained_model, max_length=200, standard=True):
    auto_tokenizer = AutoTokenizer.from_pretrained(pretrained_model)
    print("Load {} tokenizer successfully.".format(pretrained_model))

    if not os.path.exists(ent_rel_file):
        data_file_path = os.path.dirname(source_file)
        get_ent_rel_file(ent_rel_file, data_file_path)

    with open(ent_rel_file, 'r', encoding='utf-8') as f:
        ent_rel_info = json.load(f)
    
    if not os.path.exists(os.path.dirname(target_file)):
        os.mkdir(os.path.dirname(target_file))

    with open(source_file, 'r', encoding='utf-8') as fin, open(target_file, 'w', encoding='utf-8') as fout:
        # given datasets should conform to the standard setting, such as ACE2005, SciERC
        if standard:
            sentences = []
            for line in fin:
                sent = json.loads(line.strip())

                if len(sentences) == 0 or sentences[0]['articleId'] == sent['articleId']:
                    sentences.append(sent)
                else:
                    for new_sent in add_cross_sentence(sentences, auto_tokenizer, max_length):
                        add_joint_label(new_sent, ent_rel_info)
                        print(json.dumps(new_sent), file=fout)
                    sentences = [sent]

            for new_sent in add_cross_sentence(sentences, auto_tokenizer, max_length):
                add_joint_label(new_sent, ent_rel_info)
                print(json.dumps(new_sent), file=fout)
       
        # processing other datasets
        else:
            for i, line in enumerate(fin):
                print(f"Process Line{i + 1}")
                sent = json.loads(line.strip())
                
                add_wordpiece_fields(sent, auto_tokenizer)
                add_joint_label(sent, ent_rel_id)
                
                print(json.dumps(sent, ensure_ascii=False), file=fout)
                

if __name__ == '__main__':
    fire.Fire({"process": process})
