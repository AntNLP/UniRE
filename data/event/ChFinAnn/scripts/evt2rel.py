#!/bin/python

import json
import os
import sys
import itertools
import logging
import argparse

from util import load_schema
from chfinann_reader import *


def is_trigger(arg, evt_type):
    return arg == evt_schema[evt_type]["primary_args"][0]

def is_primary_arg(arg, evt_type):
    return arg in evt_schema[evt_type]["primary_args"]

def build_sent_ent_ann(sent_id, evt_type, evt, evt_offset, ins):
    '''
    sentence-level entity annotation: 
    {
        "type": entity (argument) type
        "ent_id": id of the entity (argument)
        "offset": [start, end] offset of an entity
        "text": text content of the entity
    }
    '''
    ent_ann = []
    for arg in evt:
        arg_str = evt[arg]
        if arg_str is None:
            continue

        # if the arg's offset has been recorded in evt_offset
        # (by solve_arg_overlapping()) 
        if evt_offset[arg] is not None: 
            if evt_offset[arg][0] != sent_id:
                continue
            ent_ann.append({"type":arg, "ent_id":len(ent_ann),
                "offset":evt_offset[arg][1:], "text":arg_str})
        else:
            start_ent_id = len(ent_ann)
            for offset in ins.get_ent_locations(arg_str):
                if offset[0] != sent_id:
                    continue
                ent_ann.append({"type":arg, "ent_id":len(ent_ann),
                    "offset":offset[1:], "text":arg_str})

            # coreference
            for mention in ins.get_coref(arg_str):
                for offset in ins.get_coref(arg_str)[mention]:
                    if offset[0] != sent_id:
                        continue
                    # skip if mention overlaps with arg_str
                    if any(ent["offset"][0] <= offset[1] and 
                            ent["offset"][-1] >= offset[2]-1
                            for ent in ent_ann[start_ent_id:]):
                        continue

                    ent_ann.append({"type":arg, "ent_id":len(ent_ann),
                        "offset": offset[1:], "text":mention})
    return ent_ann

def build_sent_rel_ann(evt_type, ent_ann, evt_rel):
    '''
    enumerate entity pairs and select relations in evt_rel
    sentence-level relation annotation: 
    {
        "type": relation type
        "args": [ent_id_1, ent_id_2], two arguments of the relation 
    }
    '''
    rel_ann = []
    for ent in ent_ann:
        for _ent in ent_ann:
            if _ent is ent:
                continue
            rel = [ent["type"], _ent["type"]]
            if rel in evt_rel:
                rel_ann.append({"type":rel[0]+"-"+rel[1], 
                    "args":[ent["ent_id"], _ent["ent_id"]]})
    return rel_ann

def solve_args_overlapping(evt, evt_type, evt_offset, ins):
    '''
    solve overlapping arguments of ONE event
    it still possible that an entity plays different roles in 
    two events (e.g., ChFinAnn, SZ002118_2014-01-23_63513299).
    One future plan to solve these cases is to introduce 
    entity types instead of using argument type, 
    which makes the formulation of event 
    extraction more close to joint entity relation extraction.
    '''
    overlapped_args = {}
    for arg, _arg in itertools.permutations(evt, 2):
        if arg == _arg or evt[arg] != evt[_arg] or evt[arg] is None:
            continue
        arg_str = evt[arg]

        overlapped_args[(arg, _arg)] = True

        p_arg, np_arg = None, None
        if is_primary_arg(arg, evt_type) and not is_primary_arg(_arg, evt_type):
            p_arg, np_arg = arg, _arg
        elif is_primary_arg(arg, evt_type) and not is_primary_arg(_arg, evt_type):
            p_arg, np_arg = _arg, arg
        elif is_primary_arg(arg, evt_type) and is_primary_arg(_arg, evt_type):
            logging.error("overlapped primary arguments, " + str(evt))
            sys.exit(1)
        else:
            pass

        # sometimes an entity plays different roles in a single event
        # (e.g., ChnFinAnn SZ000673_2013-08-31_63028652)
        # we remove such cases by ignoring the second role 
        # (by setting the offset of the second role illegal [-1, -1, -1])
        # some preprocessing step could help to fill the missing arguments
        offsets = ins.get_ent_locations(arg_str)[:2] \
                    if len(ins.get_ent_locations(arg_str)) > 1 \
                    else [ins.get_ent_locations(arg_str)[0], [-1, -1, -1]]
            
        if p_arg is not None:
            # if a primary argument exists, we make the first appearance of 
            # the that argument string be the primary argument,
            # and the second appearance (if exists) be the other arguments.
            evt_offset[p_arg], evt_offset[np_arg] = offsets
        elif (arg, _arg) in non_primary_key_arg_order:
            # if no primary argument exists, we consider above four commonly 
            # encountered overlapped arguments (obtained by logging the overlapped
            # arguments), and set them by prior assumptions. For example, StartDate
            # usually appears before EndDate 
            # TODO make sure doc['ann_mspan2dranges'] is sorted 
            evt_offset[arg], evt_offset[_arg] = offsets
        else:
            # remove the event outside
            overlapped_args[(arg, _arg)] = False

    for arg, _arg in overlapped_args:
        if overlapped_args[(arg, _arg)] == False and \
                overlapped_args[(_arg, arg)] == False:
            logging.info("conflict "  + arg + "-" + _arg)
            return False
    return True
            
def deduplicate(sent_anns):
    '''
    entity ids in sentence-level entity annotations may duplicate 
    (e.g., an entity takes part in multiple events)
    deduplicate() modifies (assign new) entity ids 
    '''
    if len(sent_anns) == 0:
        return sent_anns
    
    data = { "doc_id": sent_anns[0]["doc_id"],
             "sent_id": sent_anns[0]["sent_id"],
             "text": sent_anns[0]["text"],
             "token": sent_anns[0]["token"],
             "entity": [],
             "relation": [] }
    entities, relations = [], []

    # we ignore cases when an entity
    # plays different roles in different events
    def contain_ent(ent, enities):
        for _ent in entities:
            if ent["offset"] == _ent["offset"]:
                return _ent
        return None

    def contain_rel(rel, relations):
        for _rel in relations:
            if rel == _rel:
                return True
        return False

    for i, sent in enumerate(sent_anns):
        # the mapping from old ent_id to new ent_id
        id_map = {}
        for ent in sent["entity"]:
            _ent = contain_ent(ent, entities)
            old_ent_id = ent["ent_id"]
            new_ent_id = -1
            if _ent is not None:
                new_ent_id = _ent["ent_id"] 
            else:
                new_ent_id = len(entities)
                ent["ent_id"] = new_ent_id
                entities.append(ent)
            id_map[old_ent_id] = new_ent_id

        for rel in sent["relation"]:
            # update relation
            rel["args"][0] = id_map[rel["args"][0]]
            rel["args"][1] = id_map[rel["args"][1]]
            if not contain_rel(rel, relations):
                relations.append(rel)
                    
    data["entity"] = entities
    data["relation"] = relations
    return data

def main():
    chfinann_inss = load_chifinann_corpus(cmds.input_file)

    for ins in chfinann_inss:
        doc_sents = {}
        for e in ins.get_events():
            # evt_offset: a help dict for solving overlapped arguments
            e.append({k:None for k in e[2]})
            evt_id, evt_type, evt, evt_offset = e
            success = solve_args_overlapping(evt, evt_type, evt_offset, ins)
            if not success:
                logging.info("cannot resolve overlapped argument, \
                        removed docid={}, evtid={}".format(ins.get_doc_id(), evt_id))

            for sent_id in range(len(ins.get_sentences())):
                if success:
                    ent_ann = build_sent_ent_ann(sent_id, evt_type, evt, evt_offset, ins)
                    rel_ann = build_sent_rel_ann(evt_type, ent_ann, 
                            evt_schema[evt_type]["event_relations"])
                else:
                    ent_ann, rel_ann = [], []

                data = { "doc_id": ins.get_doc_id(),
                         "sent_id": sent_id,
                         "text": ins.get_sentences()[sent_id],
                         "token": [c for c in ins.get_sentences()[sent_id]],
                         "entity": ent_ann,
                         "relation": rel_ann }

                if sent_id not in doc_sents:
                    doc_sents[sent_id] = []
                doc_sents[sent_id].append(data)

        # deduplicate
        for sent_id in doc_sents:
            n_data = deduplicate(doc_sents[sent_id])
            n_data["coref_spans"] = ins.get_all_coref_spans()
            print(json.dumps(n_data, ensure_ascii=False))

evt_schema = None
cmds = None
if __name__ == '__main__':

    cmd_parser = argparse.ArgumentParser(
            description="a script converts document-level event annotations \
                    to sentence-level entity relation annotations.")
    cmd_parser.add_argument("input_file", 
            help="file with sentence-level annotations")
    cmd_parser.add_argument("schema_file", 
            help="event schema file")
    cmds = cmd_parser.parse_args()

    evt_schema = load_schema(cmds.schema_file)

    logging.basicConfig(filename=os.path.basename(cmds.input_file)+'_evt2rel.log', 
            encoding='utf-8', level=logging.DEBUG, filemode="w")
    main()
