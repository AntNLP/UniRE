import json

def print_predictions_for_joint_decoding(outputs, pred_file_path, gold_file_path, vocab, separator=" "):
    """print_predictions prints prediction results
    
    Args:
        outputs (list): prediction outputs
        file_path (str): output file path
        vocab (Vocabulary): vocabulary
        separator (str): the separator of the text, English is ' ' and Chinese is ''
    """

    with open(pred_file_path, 'w') as fpred, open(gold_file_path, 'w') as fgold:
        sent_id = 0
        for sent_output in outputs:
            # tokens
            seq_len = sent_output['seq_len']
            assert 'tokens' in sent_output
            tokens = [vocab.get_token_from_index(token, 'tokens') for token in sent_output['tokens'][:seq_len]]
            
            # entity prediction
            assert 'all_ent_preds' in sent_output
            ents, entity = {}, []
            for i, (span, ent_type) in enumerate(sent_output['all_ent_preds'].items()):
                ents[span] = i
                entity.append({
                    "ent_id": i,
                    "type": ent_type,
                    "offset": list(span),
                    "text": separator.join(tokens[span[0]:span[1]])
                    })

            # relation prediction
            assert 'all_rel_preds' in sent_output
            relation = []
            for (span1, span2), rel in sent_output['all_rel_preds'].items():
                relation.append({
                    "type": rel,
                    "args": [ents[span1], ents[span2]]
                    })

            triple = {
                "id": sent_id,
                "text": separator.join(tokens),
                "entity": entity,
                "relation": relation
            }

            # Output to pred_file            
            print(json.dumps(triple), file=fpred)


            # gold entity
            assert 'span2ent' in sent_output
            ents, entity = {}, []
            for i, (span, ent_type) in enumerate(sent_output['span2ent'].items()):
                ent_type = vocab.get_token_from_index(ent_type, 'ent_rel_id')
                assert ent_type != 'None', "true relation can not be `None`."
                ents[span] = i
                
                entity.append({
                    "ent_id": i,
                    "type": ent_type,
                    "offset": list(span),
                    "text": separator.join(tokens[span[0]:span[1]])
                    })

            # gold relation
            assert 'span2rel' in sent_output
            relation = []
            for (span1, span2), rel in sent_output['span2rel'].items():
                rel = vocab.get_token_from_index(rel, 'ent_rel_id')
                assert rel != 'None', "true relation can not be `None`."
                if rel[-1] == '<':
                    span1, span2 = span2, span1

                relation.append({
                    "type": rel,
                    "args": [ents[span1], ents[span2]]
                    })

            triple = {
                "id": sent_id,
                "text": separator.join(tokens),
                "entity": entity,
                "relation": relation
            }

            # Output to gold_file            
            print(json.dumps(triple), file=fgold)

            sent_id += 1


            