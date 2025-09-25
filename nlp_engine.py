# nlp_engine.py
import nltk
from nltk import word_tokenize, pos_tag

# Ensure minimal data
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("taggers/averaged_perceptron_tagger")
except LookupError:
    nltk.download("averaged_perceptron_tagger")

def tokenize_and_tag(sentence: str):
    tokens = word_tokenize(sentence)
    tags = pos_tag(tokens)
    return tags  # list of (token, pos)
