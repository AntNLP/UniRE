#!/bin/python

import json
import os
import sys
import itertools
import logging
import argparse
from collections import defaultdict
from util import get_longest_match

def read_output(fn):
    docs = []
    with open(fn, 'r') as f:
        for line in f:
            docs.append(json.loads(line))
    return docs

def compare_arg(p_arg, g_arg, coref_spans):
    logging.debug("compar_arg: p_arg: {} g_arg: {}\n coref_spans {}".format(
        p_arg, g_arg, coref_spans) )

    # simpler implementation without consider cmds.overlap_propotion
    #return p_arg == g_arg or (g_arg in coref_spans and p_arg in coref_spans[g_arg])

    if (p_arg is None) and (g_arg is None):
        return True
    elif (p_arg is None) != (g_arg is None):
        return False
    _, _, match_len = get_longest_match(p_arg, g_arg)
    if match_len >= cmds.overlap_propotion * len(g_arg):
        return True
    elif g_arg in coref_spans:
        for arg in coref_spans[g_arg]:
            _, _, match_len = get_longest_match(p_arg, arg)
            if match_len >= cmds.overlap_propotion* len(arg):
                return True

    return False

def get_tp_counts(p_evt, g_evt, is_equal):
    tp = 0
    for arg in p_evt["args"]:
        if arg in g_evt["args"] and \
                is_equal(p_evt["args"][arg], g_evt["args"][arg]):
                #p_evt["args"][arg] == g_evt["args"][arg]:
            tp += 1
    return tp

def update_arg_stat(p_evt, g_evt, arg_stat, is_equal):
    logging.debug("update_arg_stat \n p_evt {} \n g_evt {}".format(p_evt, g_evt))
    if g_evt is None:
        for arg in p_evt["args"]:
            arg_stat[arg]["pred"] += 1
            logging.debug("============" + arg)
    else:
        for arg in p_evt["args"]:
            arg_stat[arg]["pred"] += 1
            if arg in g_evt["args"] and \
                    is_equal(p_evt["args"][arg], g_evt["args"][arg]):
                arg_stat[arg]["tp"] += 1

        for arg in g_evt["args"]:
            if g_evt["args"][arg] is not None:
                arg_stat[arg]["gold"] += 1

        # output some debug info
        for arg in g_evt["args"]:
            if arg not in p_evt["args"] and g_evt["args"][arg] is not None:
                logging.debug("+++++++++++++Recall arg {}, {}".format(
                    arg, g_evt["args"][arg]))
        for arg in p_evt["args"]:
            if arg not in g_evt["args"] or p_evt["args"][arg] is None:
                logging.debug("-------------Precision arg {}, {}".format(
                    arg, p_evt["args"][arg]))

def best_aligned(evt, evts, is_equal):
    max_tp = -1
    best_evt = None
    for _evt in evts:
        tp = get_tp_counts(evt, _evt, is_equal)
        if tp > max_tp:
            best_evt, max_tp = _evt, tp
    return best_evt
               
def evaluation(pred_docs, gold_docs):
    arg_stat = defaultdict(lambda: {"tp":0, "pred":0, "gold":0})
    for p_doc, g_doc in zip(pred_docs, gold_docs):
        if p_doc["doc_id"] != g_doc["doc_id"]:
            logging.error("doc ids are not aligned")
            return 
        for p_evt in p_doc["event"]:
            #is_equal = lambda x, y:compare_arg(x, y, p_doc["coref_spans"])
            is_equal = lambda x, y:compare_arg(x, y, g_doc["coref_spans"])
            best_g_evt = best_aligned(p_evt, g_doc["event"], is_equal)
            update_arg_stat(p_evt, best_g_evt, arg_stat, is_equal)
            # without replacement
            if not cmds.replacement:
                if best_g_evt is not None:
                    g_doc["event"].remove(best_g_evt)

        # without replacement
        if not cmds.replacement:
            if len(g_doc["event"]) > 0:
                for g_evt in g_doc["event"]:
                    logging.debug("left g_evt \n g_evt {}".format(g_evt))
                    for arg in g_evt["args"]:
                        if g_evt["args"][arg] is not None:
                            arg_stat[arg]["gold"] += 1
                            logging.debug("+++++++++++++Recall arg {}, {}".format(
                                arg, g_evt["args"][arg]))
               
    #print(arg_stat)
    tp = sum([arg_stat[arg]["tp"] for arg in arg_stat if arg not in cmds.filter_type])
    num_gold = sum([arg_stat[arg]["gold"] for arg in arg_stat if arg not in cmds.filter_type])
    num_pred = sum([arg_stat[arg]["pred"] for arg in arg_stat if arg not in cmds.filter_type])
    output(tp, num_pred, num_gold, "overall scores ")
    for arg in arg_stat:
        output(arg_stat[arg]["tp"], arg_stat[arg]["pred"], arg_stat[arg]["gold"], 
                "argument type {} ".format(arg))

def output(tp, num_pred, num_gold, prefix):
    p = float(tp)/num_pred if num_pred != 0 else 0
    r = float(tp)/num_gold if num_gold != 0 else 0
    f1 = 2*p*r/(p+r) if p+r != 0 else 0

    print(prefix + "tp={}, num_pred={}, num_gold={}, "\
            "P={:.2f}, R={:.2f}, F={:.2f}".format(tp, num_pred, num_gold, p, r, f1))

def main():
    pred_docs = read_output(cmds.pred_file)
    gold_docs = read_output(cmds.gold_file)
    if len(pred_docs) != len(gold_docs):
        logging.error("different sample size")
        exit(1)
    evaluation(pred_docs, gold_docs)

cmds = None
if __name__ == '__main__':
    cmd_parser = argparse.ArgumentParser(description="document-level \
            event extraction evaluation.")
    cmd_parser.add_argument("pred_file", help="predict file")
    cmd_parser.add_argument("gold_file", help="gold file")
    cmd_parser.add_argument("-p", "--overlap_propotion", metavar="FLOAT",
            help="a predicted span is correct if it overlaps with p of a gold span (default 1.0)",
            type=float,
            default=1.0)
    cmd_parser.add_argument("-t", "--filter_type", metavar="TYPE",
            help="ignore entities belong to those types during evaluation (default None)",
            nargs="*",
            default=[])
    # argument types not included in evaluation
    #["EndDate", "StartDate", "ReleasedDate"]

    cmd_parser.add_argument("-r", "--replacement", 
            help= "matching gold spans with replacement",
            action="store_true")

    cmds = cmd_parser.parse_args()

    logging.basicConfig(filename=os.path.basename(cmds.pred_file)+'.evt.log',
            encoding='utf-8', level=logging.DEBUG)
    main()
