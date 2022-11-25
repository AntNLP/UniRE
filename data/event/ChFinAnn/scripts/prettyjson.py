#!/bin/python

import json
import os
import sys


with open(sys.argv[1], 'r') as f:
    for line in f:
        print(json.dumps(json.loads(line), ensure_ascii=False, sort_keys=True, indent=4))


