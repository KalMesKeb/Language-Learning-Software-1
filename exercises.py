# exercises.py
import random

def generate_matching(vocab_list):
    # returns pairs and shuffled lists
    pairs = [(v['word'], v['translation']) for v in vocab_list]
    engs = [p[0] for p in pairs]
    amhs = [p[1] for p in pairs]
    random.shuffle(engs)
    random.shuffle(amhs)
    return engs, amhs

def generate_fill_blank(sentence, target_word):
    # replace target_word with blank token
    lower = sentence.lower()
    tgt_lower = target_word.lower()
    if tgt_lower in lower:
        blanked = sentence.replace(target_word, "_____")
    else:
        blanked = sentence
    return blanked
