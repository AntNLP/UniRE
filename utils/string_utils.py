import difflib

def get_overlap(s1, s2):
    """
    This function is used to find the longest overlapping substring between s1 and s2.
    e.g. 

        my stackoverflow mysteries
        .................mystery..
        
        the result is "myster"

    """
    SeqMatcher = difflib.SequenceMatcher(None, s1, s2)
    _, _, overlap_len = SeqMatcher.find_longest_match(0, len(s1), 0, len(s2))
    return overlap_len

