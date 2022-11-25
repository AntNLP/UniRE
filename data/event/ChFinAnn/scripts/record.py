#!/bin/python

import json
import sys
import itertools
import logging

class Record():
    '''
    types: possible event types expressed by 
    items: dictionaries with event argument names as keys
           each key is associated with an "entity" field and an "occupied" field
    example:
    {
        "type": ["EquityPledge"],  
        "items": {
            "Pledger": {"entity": ent, "occupied": True/False},
            "PledgedShare": {"entity": ent, "occupied": True/False},
            "Pledgee": {"entity": ent, "occupied": True/False},
        }
    }
    records are NOT (explicitly) bounded to a specific event
    we need to check compatibility of arguments when filling records
    '''
    def __init__(self, evt_schema):
        self.types = list(evt_schema.keys())
        self.items = {}
        self.evt_schema = evt_schema

    def __str__(self):
        # ignore types and "occupied" 
        l = []
        for arg in sorted(self.items):
            if self.items[arg]["entity"] is None:
                l.append("{}:{}".format(arg, None))
            else:
                l.append("{}:{}".format(arg, self.items[arg]["entity"]["text"]))
        return "\n".join(l)

    def is_compatible(self, ent):
        '''
        return True if ent is compatible with arguments in record
        '''
        if len(self.items) == 0:
            return True
        else:
            return len(list(filter(lambda x: ent["type"] in self.evt_schema[x]["args"], 
                self.types))) != 0

    def fill(self, ent):
        if ent is None:
            return True
        if not self.is_compatible(ent):
            return False
        if ent["type"] not in self.items:
            self.items[ent["type"]] = {}
        self.items[ent["type"]]["entity"] = ent
        self.items[ent["type"]]["occupied"] = True
        ent["record"] = self

        # discard incompatible events
        self.types = list(filter(lambda x: ent["type"] in self.evt_schema[x]["args"], 
                self.types))
        return True

    def fork(self):
        new_record = Record(self.evt_schema)
        new_record.types = list(self.types)
        for arg in self.items:
            new_record.items[arg] = {}
            new_record.items[arg]["entity"] = self.items[arg]["entity"]
            new_record.items[arg]["occupied"] = False
        return new_record

    def compare(self, rec, is_entity_equal):
        if set(self.types) != set(rec.types) or \
                set(self.items.keys()) != set(rec.items.keys()):
            return False
        else:
            for arg in self.items:
                if is_entity_equal(self.items[arg]["entity"],
                        rec.items[arg]["entity"]) is False:
                    return False
        return True

    def is_complete(self):
        return any(all(parg in self.items 
            for parg in self.evt_schema[evt_type]["primary_args"])
                for evt_type in self.types)

    def merge(self, rec, is_entity_equal):
        logging.debug("record.merge(): self={}, rec={}".format(self, rec))
        if any(evt_type not in rec.types for evt_type in self.types) and \
                any(evt_type not in self.types for evt_type in rec.types):
            logging.debug("record.merge() return none: type incompatible," \
                    "self.types={}, rec.types={}".format(self.types, rec.types))
            return None

        # copy self (it may merge with other record)
        _rec = self.fork()
        
        # merge _rec with rec
        # if they conflict (i.e., with different text in a field), return None
        for arg in rec.items:
            if rec.items[arg] is None:
                continue
            ent = rec.items[arg]["entity"]
            if not _rec.is_compatible(ent):
                logging.debug("record.merge() return none: is_compatible false,"\
                        "entity={}, record={}".format(ent["text"]+ent["type"], self))
                return None
            elif arg not in _rec.items:
                _rec.items[arg] = {}
                _rec.items[arg]["entity"] = ent
                _rec.items[arg]["occupied"] = True
                # it is possible to remove some types when adding arguments
                _rec.types = list(filter(lambda x: 
                        ent["type"] in self.evt_schema[x]["args"], _rec.types))
            elif not is_entity_equal(_rec.items[arg]["entity"], 
                    rec.items[arg]["entity"]):
                logging.debug("record.merge() return none: text not equal, {}, {}"
                        .format(_rec.items[arg]["entity"]["text"], 
                            rec.items[arg]["entity"]["text"]))
                return None
            else:
                continue

        return _rec
