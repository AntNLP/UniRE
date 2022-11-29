#!/bin/bash

mkdir -p fold1/01-change-fields
mkdir -p fold1/02-matrix  # dir of the processed version

python ../transfer.py transfer fold1/00-raw/train.json fold1/01-change-fields/train.json [PER-SOC]
python ../transfer.py transfer fold1/00-raw/dev.json fold1/01-change-fields/dev.json [PER-SOC]
python ../transfer.py transfer fold1/00-raw/test.json fold1/01-change-fields/test.json [PER-SOC]

python ../process.py process fold1/01-change-fields/train.json fold1/ent_rel_file.json fold1/02-matrix/train.json bert-base-uncased 200
python ../process.py process fold1/01-change-fields/dev.json fold1/ent_rel_file.json fold1/02-matrix/dev.json bert-base-uncased 200
python ../process.py process fold1/01-change-fields/test.json fold1/ent_rel_file.json fold1/02-matrix/test.json bert-base-uncased 200
