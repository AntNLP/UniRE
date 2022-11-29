import json

class ChFinAnnInstance():
    data = None
    doc_id = -1

    def __init__(self, doc_id, data):
        self.doc_id = doc_id
        self.data = data

    def get_events(self):
        return self.data["recguid_eventname_eventdict_list"]

    def get_sentences(self):
        return self.data["sentences"]

    def get_ent_locations(self, ent_str):
        '''
        return list of (sent_id, start, end) tripls 
        each triple indicating an appearance of an entity
        '''
        if ent_str not in self.data["ann_mspan2dranges"]:
            return []
        else:
            return self.data["ann_mspan2dranges"][ent_str]

    def get_all_coref_spans(self):
        return self.data["coref_spans"]

    def get_coref(self, ent_str):
        if ent_str not in self.data["coref_spans"]:
            return []
        else:
            return self.data["coref_spans"][ent_str]

    def get_doc_id(self):
        return self.doc_id

    def get_data(self):
        return self.data

def load_chifinann_corpus(fn):
    data = []
    with open(fn, 'r') as f:
        for _doc in json.load(f):
            data.append(ChFinAnnInstance(_doc[0], _doc[1]))
    return data

# if no primary argument exists, we consider four commonly 
# encountered overlapped arguments (obtained by logging the overlapped
# arguments), and set them by prior assumptions. For example, StartDate
# usually appears before EndDate 
non_primary_key_arg_order = [
            ("StartDate", "EndDate"),
            ("EndDate", "ReleasedDate"),
            ("HighestTradingPrice", "LowestTradingPrice"),
            ("TotalHoldingShares", "TotalPledgedShares")
        ]

