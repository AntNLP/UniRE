plm_name="/mnt/data1/public/pretrain/mengzi-bert-base-fin"

mkdir -p DUEE_FIN_LITE/01-change-fields
mkdir -p DUEE_FIN_LITE/02-matrix

# python ./transfer.py transfer DUEE_FIN_LITE/00-raw/train.json DUEE_FIN_LITE/01-change-fields/train.json
# python ./transfer.py transfer DUEE_FIN_LITE/00-raw/dev.json DUEE_FIN_LITE/01-change-fields/dev.json
python ./transfer.py transfer DUEE_FIN_LITE/00-raw/test.json DUEE_FIN_LITE/01-change-fields/test.json

# python ./process.py process DUEE_FIN_LITE/01-change-fields/train.json DUEE_FIN_LITE/02-matrix/train.json ${plm_name} DUEE_FIN_LITE/ent_rel_file.json
# python ./process.py process DUEE_FIN_LITE/01-change-fields/dev.json DUEE_FIN_LITE/02-matrix/dev.json ${plm_name} DUEE_FIN_LITE/ent_rel_file.json
python ./process.py process DUEE_FIN_LITE/01-change-fields/test.json DUEE_FIN_LITE/02-matrix/test.json ${plm_name} DUEE_FIN_LITE/ent_rel_file.json 