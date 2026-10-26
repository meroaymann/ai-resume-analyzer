import math
import re
from collections import Counter

# Common English stop words (replaces scikit-learn's ENGLISH_STOP_WORDS)
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "also", "am", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "either",
    "else", "etc", "even", "ever", "every", "few", "for", "from", "further", "get", "got", "had",
    "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "however", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "least",
    "less", "like", "may", "me", "might", "more", "most", "much", "must", "my", "myself", "neither",
    "no", "nor", "not", "now", "of", "off", "often", "on", "once", "one", "only", "or", "other",
    "others", "our", "ours", "ourselves", "out", "over", "own", "per", "please", "rather", "same",
    "she", "should", "since", "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "thus",
    "to", "too", "under", "until", "up", "upon", "us", "very", "via", "was", "we", "well", "were",
    "what", "whatever", "when", "where", "whether", "which", "while", "who", "whom", "whose", "why",
    "will", "with", "within", "without", "would", "yet", "you", "your", "yours", "yourself",
    "yourselves", "able", "across", "along", "already", "among", "around", "become", "becomes",
    "come", "comes", "done", "due", "eg", "ie", "include", "includes", "including", "make",
    "makes", "many", "new", "next", "part", "put", "see", "seem", "seems", "take", "two", "three",
    "use", "used", "using", "want", "way", "ways", "work", "works",
}

TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z+#]+(?![A-Za-z0-9])")


def tokenize(text, stop_words=STOP_WORDS, min_len=2):
    tokens = (t.lower() for t in TOKEN_RE.findall(text))
    return [t for t in tokens if len(t) >= min_len and t not in stop_words]


def tfidf_cosine(text_a, text_b):
    """Same idea as scikit-learn TfidfVectorizer + cosine_similarity (smooth idf, l2 norm)."""
    count_a, count_b = Counter(tokenize(text_a)), Counter(tokenize(text_b))
    if not count_a or not count_b:
        return 0.0

    def idf(term):
        doc_freq = (term in count_a) + (term in count_b)
        return math.log((1 + 2) / (1 + doc_freq)) + 1

    vec_a = {t: c * idf(t) for t, c in count_a.items()}
    vec_b = {t: c * idf(t) for t, c in count_b.items()}
    dot = sum(v * vec_b.get(t, 0) for t, v in vec_a.items())
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0