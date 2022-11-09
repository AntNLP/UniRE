import difflib

def get_overlap(s1, s2):
    """
    This function is used to calculate the overlap of two strings.
    """
    SeqMatcher = difflib.SequenceMatcher(None, s1, s2)
    _, _, overlap_len = SeqMatcher.find_longest_match(0, len(s1), 0, len(s2))
    return overlap_len

def cal_correct_pred(correct_set, pred_set, overlap_match_rate, cal_type):
    
    """
    This function is used to calculate the number of corrects entities.
    
    Arguments:
        correct_set {collection.defaultdict} -- a set of correct entities 
        (entity text, entity type) or relations (entity1 text, entity1 type,
        entity2 text, entity2 type).
        
        pred_set {collection.defaultdict} -- a set of predicated entities  
         (entity text, entity type) or relations (entity1 text, entity1 type,
        entity2 text, entity2 type).
        
        overlap_match_rate {float} -- the matched rate of the text.
        if get_overlap(predication_text, correct_text) > overlap_match_rate,
        then we reagrd this predication entity is right
        
        cal_type {str} -- calculate the number of correct predication(entities or 
        relations)
    
    Returns:
        correct_num {int} -- the number of correct entities or relations the model predicate
    """
    matched_ids = []
    correct_num = 0
    for pred in pred_set:
        for idx, correct in enumerate(correct_set):
            if cal_type == 'ent':
                pred_text = pred[0].replace(' ', '')
                pred_type = pred[1].replace(' ', '')
                correct_text = correct[0].replace(' ', '')
                correct_type = correct[1].replace(' ', '')
                if pred_type != correct_type:
                    continue
                if idx in matched_ids:
                    continue
                if get_overlap(pred_text, 
                            correct_text) < overlap_match_rate *len(correct_text):
                    continue
            elif cal_type == 'rel':
                pred_ent1_text = pred[0].replace(' ', '')
                pred_ent1_type = pred[1].replace(' ', '')
                pred_ent2_text = pred[2].replace(' ', '')
                pred_ent2_type = pred[3].replace(' ', '')
                correct_ent1_text = correct[0].replace(' ', '')
                correct_ent1_type = correct[1].replace(' ', '')
                correct_ent2_text = correct[2].replace(' ', '')
                correct_ent2_type = correct[3].replace(' ', '')
                if pred_ent1_type != correct_ent1_type or pred_ent2_type != correct_ent2_type:
                    continue
                if idx in matched_ids:
                    continue
                if get_overlap(pred_ent1_text, 
                            correct_ent1_text) < overlap_match_rate*len(correct_ent1_text):
                    continue
                if get_overlap(pred_ent2_text, 
                            correct_ent2_text) < overlap_match_rate*len(correct_ent2_text):
                    continue
            correct_num += 1
            matched_ids.append(idx)
            break
    return correct_num

