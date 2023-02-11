#!/bin/python

import json
import sys
import itertools
import logging

def main():
    with open(sys.argv[1], 'r') as f:
        for _doc in json.load(f):
            doc_id, doc = _doc[0], _doc[1]
            data = {}
            data["doc_id"] = doc_id
            data["coref_spans"] = {k:[v for v in doc["coref_spans"][k]] 
                for k in doc["coref_spans"]}

            data["event"] = []
            for evt_id, evt_type, evt in doc["recguid_eventname_eventdict_list"]:
                ann = {}
                ann["type"] = [evt_type]
                ann["args"] = evt
                data["event"].append(ann)
            print(json.dumps(data, ensure_ascii=False)) 

if __name__ == '__main__':
    main()
