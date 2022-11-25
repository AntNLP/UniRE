#!/bin/bash


python3 ../scripts/evt2rel.py ../01-coref/dev.json ../schema/schema.json > dev.json
python3 ../scripts/evt2rel.py ../01-coref/test.json ../schema/schema.json > test.json

python3 ../scripts/evt2rel.py ../01-coref/train.json ../schema/schema.json > train.json

# or building sub-sampled training sets
# python3 ../scripts/evt2rel.py ../02-sample/train_100.json ../schema/schema.json > train_100.json
# python3 ../scripts/evt2rel.py ../02-sample/train_50.json ../schema/schema.json > train_50.json
