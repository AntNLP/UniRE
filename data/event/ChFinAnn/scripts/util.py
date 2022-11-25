import difflib
import json

def get_longest_match(s1, s2):
    s = difflib.SequenceMatcher(None, s1, s2)
    pos_a, pos_b, size = s.find_longest_match(0, len(s1), 0, len(s2))
    return pos_a, pos_b, size

def span_distance(a, b):
    '''
    distance between two non-intersecting spans
    '''
    return a[0] - b[1] if a[0] - b[1] > 0 else b[0] - a[1]

def is_span_overlapped(s1, s2):
    if s1[0] == s2[0]:
        return True
    elif s1[0] < s2[0]:
        return s1[1] > s2[0]
    else:
        return s2[1] > s1[0]

def load_schema(fn):
    with open(fn, 'r') as f:
        schema = json.load(f)
    return schema


