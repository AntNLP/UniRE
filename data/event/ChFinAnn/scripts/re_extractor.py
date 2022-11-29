import re
import os
import logging


shares_pattern = re.compile("(?P<shares>[\d]+股)")
percent_pattern = re.compile("(?P<percent>[\d]+\.[\d]*%)")


total_pattern = re.compile("总计|累积|共计|累计|总数|合计")
share_pattern = re.compile("股票|股份")
pledge_pattern = re.compile("质押")

totoalholding_pattern =re.compile("持")

#，占... 持

def get_prefix(text, start, window_size):
    prefix_start = start-window_size if start > window_size else 0
    return text[prefix_start:start]

def totalpledgedshares_re_extractor(text):
    matches = []
    window_size = 15
    for m in re.finditer(shares_pattern, text):
        prefix = get_prefix(text, m.start(), window_size)
        n1 = total_pattern.search(prefix)
        #n2 =share_pattern.search(prefix)
        n3 =pledge_pattern.search(prefix)
        if n1 is None or n3 is None:
            continue
        else:
            logging.debug("text: {}\n totoalpledgedshares m: {}".format(text, m))
            matches.append(m)
    return matches

def totalholdingshares_re_filter(text, span):
    start, end = span
    window_size = 15
    if percent_patter.match(text[start:end]) is None:
        return True
    prefix = get_prefix(text, start, window_size)
    if totoalholding_filter_pattern.search(prefix) is not None:
        return True
    return False


if __name__ == '__main__':

    # totalpledgedshares test cases

    #prefix = "累积质押股份1000股"
    #n1 = re.search(total_pattern, prefix)
    #n2 = re.search(share_pattern, prefix)
    #n3 = re.search(pledge_pattern, prefix)
    #print("=================")
    #print("n1: {}".format(n1))
    #print("n2: {}".format(n2))
    #print("n3: {}".format(n3))

    # totalholdingratio test case
    prefix = "本次补充质押的1188600股占李华青女士所持有的公司股份总数的5.25%"
    n1 = totoalholding_pattern.search(prefix)
    print("n1: {}".format(n1))

    pass
 
