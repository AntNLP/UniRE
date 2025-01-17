#!/bin/bash

mkdir -p 01-change-fields  # dir of the transferred version
mkdir -p 02-matrix  # dir of the processed version

python ../transfer.py transfer 00-raw/train.json 01-change-fields/train.json [PER-SOC]
python ../transfer.py transfer 00-raw/dev.json 01-change-fields/dev.json [PER-SOC]
python ../transfer.py transfer 00-raw/test.json 01-change-fields/test.json [PER-SOC]

python ../process.py process 01-change-fields/train.json ent_rel_file.json 02-matrix/train.json bert-base-uncased 200-raw
python ../process.py process 01-change-fields/dev.json ent_rel_file.json 02-matrix/dev.json bert-base-uncased 200-raw
python ../process.py process 01-change-fields/test.json ent_rel_file.json 02-matrix/test.json bert-base-uncased 200-raw

#rm -rf 01-change-fields