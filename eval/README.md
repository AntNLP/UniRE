# Evaluation


## eval.py

A (stand alone) script for evaluating entity relation extraction.

```shell
usage: eval.py [-h] [-p FLOAT] [-e [TYPE ...]] [-r [TYPE ...]] pred_file gold_file

a (stand alone) script for evaluating entity relation extraction

positional arguments:
  pred_file             predict file
  gold_file             gold file

options:
  -h, --help            show this help message and exit
  -p FLOAT, --overlap_propotion FLOAT
                        a predicted span is correct if it overlaps with p of a gold span (default 1.0)
  -e [TYPE ...], --entity_metrics [TYPE ...]
                        criteria for evaluating correctness of entities.
                          exact: accept entities with correct type and offset
                          offset: ignore entity type, only match entity offset
                          string: accept entities with correct string
                          overlap: accept entities with overlapped string (combine with -p option)
                          (default ALL)
  -r [TYPE ...], --relation_metrics [TYPE ...]
                        criteria for evaluating correctness of relations.
                          exact: accept relations with exact entities match (type and offset)
                          string: accept relations with correct entity strings
                          (default ALL)
``` 


The `pred_file` and `gold_file` are in the following jsonline format,
```json
{
  "id": 0,
  "text": "abcdefg",
  "entity": [
    {"ent_id" = 0, "type": "ent_type_1", "offset": [0, 1], "text": "a"},
    {"ent_id" = 1, "type": "ent_type_2", "offset": [1, 2], "text": "b"},
    {"ent_id" = 2, "type": "ent_type_1", "offset": [2, 4], "text": "cd"},
    {"ent_id" = 3, "type": "ent_type_2", "offset": [4, 5], "text": "e"},
    {"ent_id" = 4, "type": "ent_type_3", "offset": [5, 7], "text": "fg"}
  ],
  "relation": [{
      "type": "rel_type_1",
      "args": [0, 4]
    },
    {
      "type": "rel_type_2",
      "args": [1, 3]
    }]
}
```
Arguments of relations are specified by their "ent_id".


## eval_old.py

It is the script used in the original UniRE paper. 
We keep it for backword compatibility and will remove it later.
