#!/bin/python

import json
import os
import argparse

cmd_parser = argparse.ArgumentParser(description="sub-sample data sets")
cmd_parser.add_argument("input_file", help="input file")
cmd_parser.add_argument("-n", "--number", help="number of samples (default 100)", 
        metavar="N", type=int, default=100)
cmd_parser.add_argument("-t", "--type", metavar="TYPE",
        help="list of event types to be sampled",
        nargs="*",
        default=[])
cmds = cmd_parser.parse_args()

with open(cmds.input_file, 'r') as f:
    evt_type_list = cmds.type
    counts = {evt_type:0 for evt_type in evt_type_list}
    data = []
    for doc_id, doc in json.load(f):
        flag = False
        for _, evt_type, _ in doc["recguid_eventname_eventdict_list"]:
            if evt_type in evt_type_list and counts[evt_type] < int(cmds.number):
                counts[evt_type] += 1
                flag = True
        if flag:
            data.append([doc_id, doc])

    print(json.dumps(data, ensure_ascii=False, indent=4))
 
    
