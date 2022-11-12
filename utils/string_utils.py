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

def check_output(file_path):
    """
    This function is used to check the output file.
    e.g.
    
    before:
        my dog is cute.
        
        my cat is cute
         too.
    after:
        my dog is cute.
        
        my cat is cute too.
    """
    with open(file_path, 'r') as fin:
        lines = fin.readlines()
    fout = open(file_path, 'w')
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip('\r\n')
        print(idx)
        if line == "":
            fout.write('\n')
        else:
            words = line
            while idx+1 < len(lines) and len(lines[idx+1]) != 0 and lines[idx+1][0] == ' ':
                words = words + '&' + lines[idx+1].strip('\r\n')
                # replace '\n' as '&', but it may cause some bugs.
                # we will change our output form later.
                idx+=1
            print(words)
            fout.write(words + '\n')
        idx += 1
        
    