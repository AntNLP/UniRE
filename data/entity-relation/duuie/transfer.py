###
"""
An example of an instance (as a line):
{"sentId": 17, "articleId": "APW_ENG_20030527.0232", "sentText": "Five Palestinian children , a Palestinian woman and a police officer , were injured Tuesday after accidentally detonating explosives in the West Bank city of Hebron , Palestinian security officials said .", "entityMentions": [{"emId": "E1", "text": "officer", "offset": [10, 11], "label": "PER"}, {"emId": "E2", "text": "children", "offset": [2, 3], "label": "PER"}, {"emId": "E3", "text": "police", "offset": [9, 10], "label": "ORG"}], "relationMentions": [{"em1Id": "E1", "em1Text": "officer", "em2Id": "E3", "em2Text": "police", "label": "ORG-AFF"}]}

necessary fields: sentId, articleId, sentText, tokens, entityMentions, relationMentions
"""
import fire
import json
import argparse
import random
import os
def add_entityMention(emid, text, arg):
    entityMention = {}
    entityMention['emId'] = f"E{emid}"
    entityMention['text'] = text
    entityMention['offset'] = [arg['offset'][0], int(arg['offset'][-1])+1]
    entityMention['label'] = arg['type']
    return entityMention
def split(full_list, shuffle=False,ratio=0.2):
    n_total = len(full_list)
    offset = int(n_total * ratio)
    if n_total==0 or offset<1:
        return [],full_list
    if shuffle:
        random.shuffle(full_list)
    sublist_1 = full_list[:offset]
    sublist_2 = full_list[offset:]
    return sublist_1,sublist_2
def transfer(input, output):
    # parser = argparse.ArgumentParser(description="Usage for OPENIE.")
    # parser.add_argument('--input' , type=str, help="Path to source file.")
    # parser.add_argument('--output', type=str, help="Path to target file.")
    # args_parser = parser.parse_args()
    # input = args_parser.input
    # sent_cnt = 0
    # if not os.path.exists(args_parser.data_dir):
    #     os.makedirs(args_parser.data_dir)
    # input = os.path.join(args_parser.data_dir, args_parser.input)
    # output = os.path.join(args_parser.data_dir, args_parser.output)
    data = {}
    fw = open(output, "w")
    sent_cnt = 0
    with open(input, "r", encoding= 'utf-8') as fin:
        for line in fin:
            new_dic = {}
            dic = json.loads(line)
            new_dic['sentId'] = sent_cnt
            new_dic['sentText'] = dic['text']
            l1 = len(dic['text'])
            l2 = len(dic['tokens'])
            assert(l1 == l2)
            new_dic['entityMentions'] = []
            new_dic['relationMentions'] = []
            new_dic['articleId'] = 'None'
            new_dic['schema'] = dic['schema']
            if dic['schema'] not in data:
                data[dic['schema']] = []
            entities = {}
            # 事件抽取
            if len(dic['event']) != 0:
                event_cnt = 0
                for event in dic['event']:
                    event_cnt += 1
                    text = event['text'] + str((event['offset'][0], int(event['offset'][-1])+1))
                    if text not in entities:
                        entities[text] = len(entities)+1
                        entityMention = add_entityMention(len(entities), event['text'], event)
                        new_dic['entityMentions'].append(entityMention)
                    emid = entities[text]
                    text = event['text']
                    for arg in event['args']:
                        entityMention = {}
                        text = arg['text'] + str((arg['offset'][0], int(arg['offset'][-1])+1))
                        if text not in entities:
                            entities[text] = len(entities)+1
                            entityMention = add_entityMention(len(entities), arg['text'], arg)
                            new_dic['entityMentions'].append(entityMention)
                        emid = entities[text]
                        text = arg['text']
                        args = event['args']
                        relationMention = {}
                        emtext = event['text'] + str((event['offset'][0], int(event['offset'][-1])+1))
                        emid = entities[emtext]
                        relationMention['em1Id'] = f"E{emid}"
                        relationMention['em1Text'] = event['text']
                        emtext = arg['text'] + str((arg['offset'][0], int(arg['offset'][-1])+1))
                        emid = entities[emtext]
                        relationMention['em2Id'] = f"E{emid}"
                        relationMention['em2Text'] = arg['text']
                        relationMention['label'] = 'T-A'
                        new_dic['relationMentions'].append(relationMention)
                if event_cnt <= 0:
                    continue
                new_dic['tokens'] = dic['tokens']
                #fout.write(json.dumps(new_dic,ensure_ascii=False) + '\n')
            # 关系抽取
            elif len(dic['relation']) != 0 or len(dic['entity']) != 0:
                for entity in dic['entity']:
                    text = entity['text']
                    id_text = text + str((entity['offset'][0], int(entity['offset'][-1])+1))
                    entities[id_text] = len(entities) + 1
                    emid = entities[id_text]
                    entityMention = add_entityMention(emid, text, entity)
                    new_dic['entityMentions'].append(entityMention)
                for relation in dic['relation']:
                    relationMention = {}

                    arg = relation['args'][0]
                    relationMention['em1Text'] = arg['text']
                    relationMention['em1Id'] = f"E{entities[arg['text']+str((arg['offset'][0], int(arg['offset'][-1])+1))]}"

                    arg = relation['args'][1]
                    relationMention['em2Text'] = arg['text']
                    relationMention['em2Id'] = f"E{entities[arg['text']+str((arg['offset'][0], int(arg['offset'][-1])+1))]}"

                    relationMention['label'] = relation['type']
                    new_dic['relationMentions'].append(relationMention)
            elif len(dic['event']) == 0:
                continue
            new_dic['tokens'] = dic['tokens']
            fw.write(json.dumps(new_dic,ensure_ascii=False) + '\n')
    
if __name__ == "__main__":
    fire.Fire({'transfer': transfer})
    	

