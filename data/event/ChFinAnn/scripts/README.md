# From Event Extration to Entity-Relation Extraction 

Tools for converting document-level
event annotations to sentence-level entity relation annotations.
Core scripts are
- `evt2rel.py` converts events to entity-relations
- `rel2evt.py` converts entity-relations back to events.
- `eval.py` is a document-level event evaluation scripts following the 
[Doc2EDAG paper](https://github.com/dolphin-zs/Doc2EDAG)

# evt2rel

```shell
usage: evt2rel.py [-h] input_file schema_file

a script converts document-level event annotations to sentence-level entity relation annotations.

positional arguments:
  input_file   file with sentence-level annotations
  schema_file  event schema file

options:
  -h, --help   show this help message and exit
```

`evt2rel.py` is currently tailored to ChFinAnn annotation format.
For a document, ChFinAnn labels each event's 
arguments with text strings (without offsets).
The crux here is to find the correct locations (offsets) of
each arguments string.
We adopt the following heuristic strategies, 
- first, for each event, all appearances of its argument 
strings are seen as entities.
- next, in each sentence, any entity pair (belongs to the event) forms
a sentence-level relation, and the type of the relation 
is defined "type(entity1)-type(entity2)" (e.g., "EquityHolder-StartDate").
To prune the number of possible relation types 
and make relation models easier to learn,
we further pre-define a relation type set
 ("event_relations" fields in `schema.json`)
which are subsets of all possible entity type combinations.

Another problem is about overlapped arguments. 
Generally, two cases may happen,
- a text string is associated with multiple arguments of an event 
(e.g., in an event, "StartDate" equals "EndDate").
- a text string is associated with arguments belong to different events
(e.g., the "StartDate" of an event is the "EndDate" of another event).

Since UniRE can not deal with entities labelled with multiple types,
we need to resolve the overlapping problem before passing them to UniRE.
We adopt the following heuristic, 
- for the first case above, 
  * if one argument is a primary argument (defined in `schema.json`),
and another is not, we assign the first appearance of
the string in sentence the primary argument. It reflects that "primary"
arguments are usually first described in an utterance.
  * if both arguments are primary, the script exits:
overlapping between primary arguments rarely happens (by inspecting 
the corpus, it rarely happens)
  * if both arguments are not primary, we pre-define the order of 
argument assignments (`non_primary_key_arg_order` in `chfinann_reader`)
based on some prior assumptions (e.g., "StartDate" is usually described 
before "EndDate"). Finally, if argument types fall out of the pre-defined set,
we simiply ignore them.
- for the second case, we currently ignore them.

# rel2evt


```shell
usage: rel2evt.py [-h] [-n NUM] [-l LEN] [-t [TYPE ...]] [-w SIZE] input_file schema_file

a script aggregates sentence-level entity relation annotations to document-level event annotations.

positional arguments:
  input_file            file with sentence-level annotations
  schema_file           event schema file

options:
  -h, --help            show this help message and exit
  -n NUM, --filter_num NUM
                        discard events with number less than filter_num (default 2)
  -l LEN, --filter_len LEN
                        discard entities with length less than filter_len (default 2)
  -t [TYPE ...], --filter_type [TYPE ...]
                        discard entities belong to those types (default None)
  -w SIZE, --window_size SIZE
                        hyper parameter of the heuristic merging algorithm: only merge records within window_size (default 3)
```

`rel2evt.py` implements a deterministic procedure 
(another choice is to learn a model) to recover document-level 
event records from sentence-level entity relation annotations 
(outputs of UniRE). Specifically,
- for each predicted entity, we either create a new event record 
(`class Record` in `record.py`), or put it in an existing record
according to predicted relations:
if the entity holds a relation with another entity, 
and that entity has been filled in an event record, 
then our entity could be put in the same record provides they are compatible.
  * if the argument slot of the record is empty, we directly fill the entity.
  * if the slot is occupied, we fork a new record and fill the entity to the new one.
- after find-and-fill records for each entity (`find_fill_record()`) in sentence-level
(not accurate, see the code for details),
we further merge records across sentences (`merge_record()`).

`rel2evt.py` also performs some filtering and supplementing operations,
- it filters out predicted entities with short length (`filter_len` option)
- it filters out events with less arguments (`filter_num` option)
- it can also ignore some `unreliable` entity predictions (`filter_type`). 
For example, we find that in ChFinAnn, annotations of dates 
("StartDate", "EndDate", "ReleasedDate") are sometimes
questionable, thus the model may suffer from garbage-in-garbage-out.
In this case, for better evaluating extraction performances,
we may prefer to ignoring date entities. 
- it incorporates regular expression extractors (`re_extractors.py`) which supplement
model predictions with prior patterns.


# eval

```shell
usage: eval.py [-h] [-p FLOAT] [-t [TYPE ...]] [-r] pred_file gold_file

document-level event extraction evaluation.

positional arguments:
  pred_file             predict file
  gold_file             gold file

options:
  -h, --help            show this help message and exit
  -p FLOAT, --overlap_propotion FLOAT
                        a predicted span is correct if it overlaps with p of a gold span (default 1.0)
  -t [TYPE ...], --filter_type [TYPE ...]
                        ignore entities belong to those types during evaluation (default None)
  -r, --replacement     matching gold spans with replacement if it is set
```


# Other Files

- `evt2evt.py` converts the original ChFinAnn format to the evaluation file format 
(generating gold files for `eval.py`).
- `chfinann_reader.py` helps to host ChFinAnn-format-dependent parts in `evt2rel.py`.
- `record.py` defines event records for `rel2evt.py`.
- `re_extractor.py` contains regular expressions for post-extracting in `rel2evt.py`.
- `util.py` contains some helper functions.
- `prettyjson.py` outputs readable json format.


