#!/bin/python

import json
import os
import sys
import itertools
import logging
import re
import argparse

from record import Record
from util import is_span_overlapped, load_schema
from re_extractor import totalpledgedshares_re_extractor

'''
input: sentence-level entity relation annotations of a document
output: event records of the document

notations: binary relations (head, dependent)

algorithm
    1. when meeting a trigger, init a record
    2. when meeting a primary arg with a head, recursively assign it to the record of its head 
        (given the DAG structure of event relation definition). 
        If that record already contains such argument, we fork a new record.
    3. when meeting a primary arg without head, find the nearest triger before it, assign it to
        that trigger's record
    4. when meeting a non-primary arg with a head, do condition 2
    5. when meeting a non-primary arg without a head, do condition 3 except the distance to that
        record should be constrained by a distance (e.g., 1)
    6. after gererating all records remove those missing primary args
'''

def is_trigger(arg):
    '''
    the first primary arguments is the trigger of the event
    return true if arg is a trigger of one event
    '''
    return any(arg == evt_schema[evt_type]["primary_args"][0] 
            for evt_type in evt_schema)

def is_primary_arg(arg):
    '''
    return true if arg is a primary argument of an event
    '''
    return any(arg in evt_schema[evt_typ]["primary_args"] 
            for evt_type in primary_arg)
    
def has_record(ent):
    return "record" in ent
   
def _find_heads(ent, sent):
    heads = []
    for rel in sent["relation"]:
        if rel["args"][1] == ent["ent_id"]:
            # get head entity from relation 
            # (in the form of (head ent_id, tail ent_id))
            #heads.append(sent["entity"][rel["args"][0]])
            for h_ent in sent["entity"]:
                if h_ent["ent_id"] == rel["args"][0]:
                    heads.append(h_ent)
                    break
    return heads

def find_head(ent, sent, sents):
    '''
        find heads in sent following relation chains,
        if not found, find them in other sentences:
        if ent is a primary argument, find a nearest trigger
        if not, find a nearest trigger within a range
        return a list of (head_entity, head_sentences)
    '''

    if is_trigger(ent["type"]) is True:
        return heads

    heads = [(h_ent, sent) for h_ent in _find_heads(ent, sent)]

    if len(heads) != 0:
        return heads

    sent_id = sents.index(sent)
    h_ent = None
    i = sent_id - 1
    while i > 0:
        p_sent = sents[i]
        for p_ent in p_sent["entity"]:
            # find the nearest one
            # it is possible p_ent is from another event type
            # when the classifier is wrong
            # i.e.,  (p_ent["type"], ent["type"]) is a not a legal relation.
            # Here we just return a head ignoring compatiability of relation,
            # the following fill_record will check compatible 
            # TODO: find compatible head
            if not is_trigger(p_ent["type"]): # and not is_compatible(ent, p_ent["record"]):
                continue
            if h_ent is None or p_ent["offset"][0] > h_ent["offset"][0]:
                h_ent = p_ent
        if h_ent is not None:
            heads.append((h_ent, sents[i]))
            break
        else:
            i -= 1

    return heads

def find_head2(ent, sent):
    '''
    find root of ent in sent
    '''
    heads = []
    if is_trigger(ent["type"]) is True:
        return heads

    heads = _find_heads(ent, sent)
    return heads

def find_fill_record2(ent, sent):
    '''
    return whether we find a record
    '''
    if has_record(ent):
        return True

    # multiple heads (DAG, not tree)
    heads = find_head2(ent, sent)

    if len(heads) == 0:
        record = Record(evt_schema)
        record.fill(ent)
        return True
    success = False

    for h_ent in heads:
        rc = find_fill_record2(h_ent, sent) 
        if rc is False:
            continue
        h_record = h_ent["record"]
        if ent["type"] not in h_record.items or \
                h_record.items[ent["type"]]["occupied"] is False:
            s = h_record.fill(ent)
            success = success or (rc and s)
        elif h_record.items[ent["type"]]["entity"] == ent:
            # it is possible ent has been in h_record 
            # (i.e., filled in other heads)
            continue
        else:
            # set occupied in the forked record
            # decendants of this entity will only fill/fork this forked record,
            # due to the DAG structure of event2relation, future actions 
            # won't touch ancesters of the current entity,
            # therefore, we are safe to leave "occupied" field of ancestors being False
            # instead of setting them properly (need traveral of relations).
            record = h_record.fork()
            s = record.fill(ent)
            success = success or (rc and s)
    return success

def find_fill_record(ent, sent, sents):
    '''
    return whether we find a record
    '''
    #logging.debug("ent: {}\n has_record: {}\n is_trigger: {}".format(
    #    ent, has_record(ent), is_trigger(ent["type"])))
    if has_record(ent):
        return True

    if is_trigger(ent["type"]):
        record = Record(evt_schema)
        record.fill(ent)
        return True

    # multiple heads (DAG, not tree)
    heads = find_head(ent, sent, sents)
    if len(heads) == 0:
        return False
    success = False
    for h_ent, h_sent in heads:
        rc = find_fill_record(h_ent, h_sent, sents) 
        if rc is False:
            continue

        h_record = h_ent["record"]
        if ent["type"] not in h_record.items or \
                h_record.items[ent["type"]]["occupied"] is False:
            s = h_record.fill(ent)
            success = success or (rc and s)
        elif h_record.items[ent["type"]]["entity"] == ent:
            # it is possible ent has been in h_record 
            # (i.e., filled in other heads)
            continue
        else:
            # set occupied in the forked record
            # decendants of this entity will only fill/fork this forked record,
            # due to the DAG structure of event2relation, future actions 
            # won't touch ancesters of the current entity,
            # therefore, we are safe to leave "occupied" field of ancestors being False
            # instead of setting them properly (need traveral of relations).
            record = h_record.fork()
            s = record.fill(ent)
            success = success or (rc and s)
    return success

def merge_records2(sents):
    if len(sents) == 0:
        return []
    is_entity_equal = lambda x, y: compare_entity(x, y, sents[0]["coref_spans"])
    records = deduplicate_records(
        [ent["record"] for sent in sents for ent in sent["entity"] if has_record(ent)],
        is_entity_equal)

    merged_records = []
    if len(records) == 0:
        return merged_records 
    if len(records) == 1:
        merged_records.append(records[0])
        return merged_records 
        
    # gready strategy: only merge adjacent records
    i = 0
    while i < len(records):
        m = records[i]
        j = i+1
        while j < len(records):
            n = m.merge(records[j], is_entity_equal)
            if n is None:
                merged_records.append(m)
                i = j if j < len(records) - 1 else j+1
                break
            elif j == len(records) - 1:
                merged_records.append(n)
                i = j+1
                break
            else:
                m = n
                j += 1

    merged_records = deduplicate_records(merged_records, is_entity_equal)
    return merged_records

def merge_records(sents):
    '''
    a greedy merge strategy
    1. starting from records with one occupied field
    2. try to merge them with other records.
    3. continue with records with two occupied field
    future work
    we may deploy document-level RE models to connect 
    records cross sentences.
    '''
    if len(sents) == 0:
        return []

    is_entity_equal = lambda x, y: compare_entity(x, y, sents[0]["coref_spans"])
    records = deduplicate_records(
        [ent["record"] for sent in sents for ent in sent["entity"] if has_record(ent)],
        is_entity_equal)

    if len(records) == 0:
        return []

    merged_records = []
    while True:
        _records = []
        logging.debug("start merge, length of records {}".format(len(records)))
        logging.debug("\n"+"\n-------\n".join(map(str, records)))
        if len(records) == 0:
            break
        if len(records) == 1:
            merged_records.append(records[0])
            break
        
        can_merge = [False]*len(records)
        for i, rec1 in enumerate(records):
            for j in range(i+1, len(records)):
                if j - i >= cmds.window_size:
                    break
                rec2 = records[j]
                m = rec1.merge(rec2, is_entity_equal)
                if m is None: 
                    continue
                can_merge[i], can_merge[j] = True, True
                _records.append(m)

        logging.debug("len(can_merge) {}, len(records) {}".format(len(can_merge), len(records)))
        # find records which can not be merged with others 
        # and put them in the final output list
        for i, rec in enumerate(records):
            if not can_merge[i] and rec.is_complete():
                logging.debug("can_merge is False and complete {}".format(str(rec)))
                merged_records.append(rec)

        # deduplicate
        # TODO removing rec1 \subset rec2
        records = deduplicate_records(_records, is_entity_equal)

    # deduplicate
    merged_records = deduplicate_records(merged_records, is_entity_equal)
    logging.debug("merged record {}".format(len(merged_records)))
    logging.debug("\n"+"\n*******\n".join(map(str, merged_records)))
    return merged_records

def compare_entity(ent1, ent2, coref_spans):
    if (ent1 is None) ^ (ent2 is None):
        return False
    elif ent1 is None and ent2 is None:
        return True
    elif ent1["text"] == ent2["text"] or \
            (ent1["text"] in coref_spans and 
                    ent2["text"] in coref_spans[ent1["text"]]) or \
            (ent2["text"] in coref_spans and 
                    ent1["text"] in coref_spans[ent2["text"]]):
        return True
    else:
        return False

def deduplicate_records(records, is_entity_equal):
    flags = [False]*len(records)
    for i in range(len((records))):
        rec1 = records[i]
        if flags[i]:
            continue
        for j in range(i+1, len(records)):
            rec2 = records[j]
            if rec1.compare(rec2, is_entity_equal):
                flags[j] = True
    return [records[i] for i in range(len(flags)) if not flags[i]]


def sort_entities(sents):
    '''
    sort entity spans in sents with their left endpoints
    later merge_record() calls may rely on the adjacent information
    to filter out distant records
    '''
    pass

def build_event_from_rel(sents):
    for sent in sents:
        for ent in sent["entity"]:
            if ent["type"] in cmds.filter_type:
                continue
            find_fill_record(ent, sent, sents)
            #find_fill_record2(ent, sent)
    evt_records = merge_records(sents)
    #evt_records = merge_records2(sents)
    return evt_records

def find_relation(ent1, ent2, sent):
    for rel in sent["relation"]:
        if rel["args"] == [ent1["ent_id"], ent2["ent_id"]]:
            return rel
    return None

def break_cycles(sent):
    for ent in sent["entity"]:
        # (entity, its head)
        q = [(None, ent)]
        visit = set()
        while len(q) != 0:
            _, c_ent = q.pop(0)
            h_ents = _find_heads(c_ent, sent)
            for h_ent in h_ents:
                if h_ent is ent:
                    # drop relation
                    rel = find_relation(c_ent, h_ent, sent)
                    #logging.debug("remove relation {}".format(rel))
                    if rel is not None:
                        sent["relation"].remove(rel)
                elif h_ent["ent_id"] not in visit:
                    q.append((c_ent, h_ent))
                    visit.add(h_ent["ent_id"])

def filter_entities(sent):
    entities = []
    for ent in sent["entity"]:
        if ent["offset"][1] - ent["offset"][0] >= cmds.filter_len:
            entities.append(ent)
        else:
            logging.debug("filtered entity: {}".format(ent))
            sent["relation"] = [rel for rel in sent["relation"] 
                    if rel["args"][0] != ent["ent_id"]
                    and rel["args"][1] != ent["ent_id"]]
    sent["entity"] = entities

def add_entities(sent):
    re_extractors = {"TotalPledgedShares":totalpledgedshares_re_extractor}
    for ent_type in re_extractors:
        matches = re_extractors[ent_type](sent["text"])
        for m in matches:
            found = False
            for ent in sent["entity"]:
                # if the two spans overlapped, update the entity span and type
                # but relations are not updated 
                ent_span = ent["offset"]
                if is_span_overlapped(ent_span, m.span()):
                    logging.debug("ent_span {}, m.span {}".format(ent_span, m.span()))
                    logging.debug("update entity: old entity {}".format(ent))
                    ent["offset"] = [m.start(), m.end()]
                    ent["type"] = ent_type
                    logging.debug("update entity: new entity {}".format(ent))
                    found = True
                    break
            if not found:
                ent_id = 0 if len(sent["entity"]) == 0 else max(
                        sent["entity"], key=lambda x:x["ent_id"])["ent_id"] + 1
                sent["entity"].append({
                    "ent_id" : ent_id,
                    "type": ent_type,
                    "offset": [m.start(), m.end()],
                    "text": m.group()})
                logging.debug("append new entity: {}".format(sent["entity"][-1]))
    
def main():
    docs = []
    with open(cmds.input_file, 'r') as f:
        for line in f:
            sent = json.loads(line)
            if len(docs) == 0 or sent["doc_id"] != docs[-1][0]["doc_id"]:
                docs.append([])
            break_cycles(sent)
            filter_entities(sent)
            add_entities(sent)
            docs[-1].append(sent)

    for sents in docs:
        evt_records = build_event_from_rel(sents)
        data = {}
        data["doc_id"] = sents[0]["doc_id"]
        data["coref_spans"] = {k:[v for v in sents[0]["coref_spans"][k]] 
                for k in sents[0]["coref_spans"]}
        data["event"] = []
        for rec in evt_records:
            ann = {}
            ann["type"] = rec.types
            ann["args"] = {arg:rec.items[arg]["entity"]["text"] for arg in rec.items}
            # filter events with less arguments
            #if ann["type"] == ["EquityUnderweight", "EquityOverweight"] or len(ann["args"]) > 2:
            if len(ann["args"]) > cmds.filter_num:
                data["event"].append(ann)
        print(json.dumps(data, ensure_ascii=False)) 

cmds = None
evt_schema = None
if __name__ == '__main__':
    cmd_parser = argparse.ArgumentParser(description="a script aggregates \
            sentence-level entity relation annotations to  document-level \
            event annotations.")
    cmd_parser.add_argument("input_file", help="file with sentence-level annotations")
    cmd_parser.add_argument("schema_file", help="event schema file")
    cmd_parser.add_argument("-n", "--filter_num", metavar="NUM",
            help="discard events with number less than filter_num (default 2)",
            default=2)
    cmd_parser.add_argument("-l", "--filter_len", metavar="LEN",
            help="discard entities with length less than filter_len (default 2)",
            default=2)
    cmd_parser.add_argument("-t", "--filter_type", metavar="TYPE",
            help="discard entities belong to those types (default None)",
            nargs="*",
            default=[])
    #default=["StartDate", "EndDate", "ReleasedDate"]
    cmd_parser.add_argument("-w", "--window_size", metavar="SIZE",
            help="hyper parameter of the heuristic merging algorithm: \
                only merge records within window_size (default 3)",
            default=3)
    cmds = cmd_parser.parse_args()

    # TODO check whether relation and entity types match
    logging.basicConfig(filename=os.path.basename(cmds.input_file)+'_rel2evt.log', 
            encoding='utf-8', level=logging.DEBUG, filemode="w")

    evt_schema = load_schema(cmds.schema_file)

    main()

