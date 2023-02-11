#!/bin/python

import json
import os
import sys
import itertools
import logging
import argparse
from collections import defaultdict
import difflib

logger = logging.getLogger(__name__)

def get_longest_match(s1, s2):
    '''
    find the longest continuous overlapping substring between s1 and s2.
    '''
    s = difflib.SequenceMatcher(None, s1, s2)
    pos_a, pos_b, size = s.find_longest_match(0, len(s1), 0, len(s2))
    return pos_a, pos_b, size

def read_output(fn):
    inss = []
    with open(fn, 'r') as f:
        for line in f:
            inss.append(json.loads(line))
    return inss

def find_entity_id(ent_id, ents):
    for ent in ents:
        if ent["ent_id"] == ent_id:
            return ent
    return None

def locate_entites_of_relation(rel, ents):
    ent0 = find_entity_id(rel["args"][0], ents)
    ent1 = find_entity_id(rel["args"][1], ents)
    return ent0, ent1

def compare_entity_exact(p_ent, g_ent):
    return p_ent["offset"] == g_ent["offset"] and\
            p_ent["type"] == g_ent["type"]

def compare_entity_offset(p_ent, g_ent):
    return p_ent["offset"] == g_ent["offset"]

def compare_entity_string(p_ent, g_ent):
    return p_ent["text"] == g_ent["text"]

def compare_entity_overlap(p_ent, g_ent):
    _, _, match_len = get_longest_match(p_ent["text"], g_ent["text"])
    #match_len = get_overlap(p_ent["text"], g_ent["text"])
    return match_len >= cmds.overlap_propotion * len(g_ent["text"])

def compare_relation(p_rel, g_rel, p_ents, g_ents, is_entity_equal):
    p_ent0, p_ent1 = locate_entites_of_relation(p_rel, p_ents)
    g_ent0, g_ent1 = locate_entites_of_relation(g_rel, g_ents)
    if any(map(lambda x: x is None, [p_ent0, p_ent1, g_ent0, g_ent1])):
        return False
    return p_rel["type"] == g_rel["type"] and\
            is_entity_equal(p_ent0, g_ent0) and\
            is_entity_equal(p_ent1, g_ent1)

def compare_relation_overlap(p_rel, g_rel, p_ents, g_ents):
    return compare_relation(p_rel, g_rel, 
                            p_ents, g_ents, compare_entity_overlap)

def compare_relation_exact(p_rel, g_rel, p_ents, g_ents):
    return compare_relation(p_rel, g_rel, 
                            p_ents, g_ents, compare_entity_exact)

def compare_relation_string(p_rel, g_rel, p_ents, g_ents):
    return compare_relation(p_rel, g_rel, 
                            p_ents, g_ents, compare_entity_string)

def best_match(obj, objs, is_equal):
    for _obj in objs:
        r = is_equal(obj, _obj)
        if r is True:
            return 1
    return 0

def evaluation(pred_inss, gold_inss, obj, is_equal_ops):
    '''
    obj: "entity" or "relation"
    is_equal: whether two objs are equal
    '''
    stat = defaultdict(lambda: {"tp":0, "pred":0, "gold":0})
    for p_ins, g_ins, is_equal in zip(pred_inss, gold_inss, is_equal_ops):
        if p_ins["id"] != g_ins["id"]:
            logging.error("ids are not aligned")
            return 

        for p_obj in p_ins[obj]:
            tp = best_match(p_obj, g_ins[obj], is_equal)
            stat[p_obj["type"]]["tp"] += tp
            stat[p_obj["type"]]["pred"] += 1
        for g_obj in g_ins[obj]:
            stat[g_obj["type"]]["gold"] += 1

    tp = sum([stat[arg]["tp"] for arg in stat])
    num_gold = sum([stat[arg]["gold"] for arg in stat])
    num_pred = sum([stat[arg]["pred"] for arg in stat])
    p, r, f1 = output(tp, num_pred, num_gold, "overall scores ")
    for arg in stat:
        output(stat[arg]["tp"], stat[arg]["pred"], stat[arg]["gold"], 
                "argument type {} ".format(arg))

    return p, r, f1

def output(tp, num_pred, num_gold, prefix):
    p = float(tp)/num_pred if num_pred != 0 else 0
    r = float(tp)/num_gold if num_gold != 0 else 0
    f1 = 2*p*r/(p+r) if p+r != 0 else 0

    logger.info(prefix + "tp={}, num_pred={}, num_gold={}, "\
                    "P={:.2f}, R={:.2f}, F={:.2f}".format(
                    tp, num_pred, num_gold, p, r, f1))

    return p, r, f1

entity_metrics = {
        "exact": compare_entity_exact,
        "offset": compare_entity_offset,
        "string": compare_entity_string,
        "overlap": compare_entity_overlap
        }

relation_metrics = {
        "exact": compare_relation_exact,
        "string": compare_relation_string,
        "overlap": compare_relation_overlap
        }

def eval_file(pred_file, gold_file, entity_metric=["exact"], relation_metric=["exact"]):
    pred_inss = read_output(pred_file)
    gold_inss = read_output(gold_file)
    if len(pred_inss) != len(gold_inss):
        logging.error("different sample size")
        exit(1)

    for m in entity_metric:
        is_equal_ops = itertools.repeat(entity_metrics[m], len(pred_inss))
        logger.info(10*"=" + " entity:" + m + 10*"=")
        ne_p, ne_r, ne_f1 = evaluation(pred_inss, gold_inss, "entity", is_equal_ops)
    
    for m in relation_metric:
        is_equal_ops = (lambda x, y: 
                relation_metrics[m](x, y, p_ins["entity"], g_ins["entity"])
                for p_ins, g_ins in zip(pred_inss, gold_inss))
        logger.info(10*"=" + " relation:" + m + 10*"=")
        re_p, re_r, re_f1 = evaluation(pred_inss, gold_inss, "relation", is_equal_ops)

    return ne_f1, re_f1


def build_cmd_parser():
    cmd_parser = argparse.ArgumentParser(description="a (stand alone) script for "\
            "evaluating entity relation extraction", 
            formatter_class=argparse.RawTextHelpFormatter)
    cmd_parser.add_argument("pred_file", help="predict file")
    cmd_parser.add_argument("gold_file", help="gold file")
    cmd_parser.add_argument("-p", "--overlap_propotion", metavar="FLOAT",
            help="a predicted span is correct if it overlaps with p of a gold span (default 1.0)",
            type=float,
            default=1.0)
    cmd_parser.add_argument("-e", "--entity_metrics", metavar="TYPE",
            choices=["exact", "offset", "string", "overlap"], 
            help="criteria for evaluating correctness of entities.\n"\
                "  exact: accept entities with correct type and offset\n"\
                "  offset: ignore entity type, only match entity offset\n"\
                "  string: accept entities with correct string\n"\
                "  overlap: accept entities with overlapped string (combine with -p option)\n"\
                "  (default ALL)",
            nargs="*",
            default=["exact", "offset", "string", "overlap"])
    cmd_parser.add_argument("-r", "--relation_metrics", metavar="TYPE",
            choices=["exact", "string", "overlap"], 
            help="criteria for evaluating correctness of relations.\n"\
                "  exact: accept relations with exact entities match (type and offset)\n"\
                "  string: accept relations with correct entity strings\n"\
                "  (default ALL)",
            nargs="*",
            default=["exact", "string", "overlap"])
    return cmd_parser

cmds = None
if __name__ == '__main__':
    cmd_parser = build_cmd_parser()
    cmds = cmd_parser.parse_args()
    logging.basicConfig(filename=os.path.basename(cmds.pred_file)+u'.log',
             level=logging.DEBUG)
    eval_file(cmds.pred_file, cmds.gold_file, cmds.entity_metrics, cmds.relation_metrics)
