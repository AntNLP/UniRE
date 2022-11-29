#!/bin/python

import json
import re
import os
import sys
import itertools
import logging
import operator

coref_args = {"Pledger", "Pledgee", "EquityHolder", "CompanyName"}

# TODO normalize parentheses/quotes/colons
LP = "[（(]"
RP = "[）)]"
LQ = '[“"]?'
RQ = '[”"]?'
Colon = '[：:]?'
#abbr_pattern = "（以下简?称：?“?(.*?)”?([，、或]“?(.*?)”?)?）"
#abbr_pattern = "（以下简?称：?“?([^《》]*?)”?([，、或]“?([^《》]*?)”?)?）"
#abbr_pattern = "（以下简?称：?“?(?P<abbr1>[^《》]*?)”?([，、或]“?(?P<abbr2>[^《》]*?)”?)?）"
abbr_pattern = '^[（(]以下简?称[：:]?[“"]?(?P<abbr1>[^《》]*?)[”"]?([，、或][“"]?(?P<abbr2>[^《》]*?)[”"]?)?[）)]'

def print_re_matches(m):
    logging.info(m)
    if m is not None:
        logging.info("group(abbr1) {}, span(abbr1) {}".format(
            m.group("abbr1"), m.span("abbr1")))
        logging.info("group(abbr2) {}, span(abbr2) {}".format(
            m.group("abbr2"), m.span("abbr2")))
    pass

def find_coref_mentions(mention, doc):

    logging.info(f"{mention=}")
    # step 1. find abbreviation strings of mention
    abbrs = {}
    for sent_id, start, end in doc["ann_mspan2dranges"][mention]:
        sent = doc["sentences"][sent_id]
        logging.info("sent[end:]=" + sent[end:])
        m = re.search(abbr_pattern, sent[end:]) 
        print_re_matches(m)
        if m is None:
            continue

        # empty matched string SZ002138_2018-12-19_1205676945
        if len(m.group("abbr1")) != 0:
            abbrs[m.group("abbr1")] = []
        if m.group("abbr2") is not None and len(m.group("abbr1")) != 0:
            abbrs[m.group("abbr2")] = []

    # step 2. find all appearances for each mention
    for a in abbrs:
        for sent_id, sent in enumerate(doc["sentences"]):
            for m in re.finditer(a, sent):
                abbrs[a].append([sent_id, m.start(), m.end()])

    # TODO ensure no overlapping with existing spans
    return abbrs
        
        
def main():
    docs = []
    with open(sys.argv[1], 'r') as f:
        for doc_id, doc in json.load(f):
            doc["coref_spans"] = {}
            mentions = set()
            for _, _, evt in doc["recguid_eventname_eventdict_list"]:
                for arg in coref_args:
                    if arg in evt:
                        mentions.add(evt[arg])
            for m in mentions:
                coref = find_coref_mentions(m, doc)
                if len(coref) != 0:
                    doc["coref_spans"][m] = coref
                # "ann_mspan2dranges"
                #for abbr in mentions[m]:
                #    doc["ann_mspan2dranges"].append({abbr["text"]:[ ?? ]})

            docs.append([doc_id, doc])
    print(json.dumps(docs, ensure_ascii=False, indent=4))

if __name__ == '__main__':
    logging.basicConfig(filename=os.path.basename(sys.argv[1])+'_coref_resolv.log', 
            encoding='utf-8', level=logging.DEBUG, filemode="w")
    main()

    # test case 1
    #sent = u"（以下简称“亚特投资”）将其持有的公司部分股份进行质押的通知，现将具体情况公告如下"

    # test case 2 
    #sent = "（以下简称“当代科技”，持有公司股份总数157491362股，占本公司总股本的24.49%）通知，"


    #m = re.search(abbr_pattern, sent) 
    #print_re_matches(m)

