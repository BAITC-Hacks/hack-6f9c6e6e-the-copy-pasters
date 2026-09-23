import re

from ..config import QUERY_TERMS
from ..data import normalized


def words(value) -> set[str]:
    return {word for word in re.findall(r"[a-zа-яё0-9]+", normalized(value)) if len(word) >= 3}


def text_relevance(description, event, category) -> float:
    """Deterministic lexical relevance from profile text and query terms."""
    description_words = words(description)
    terms = set()
    for value in (event, category):
        key = normalized(value)
        terms.update(QUERY_TERMS.get(key, words(value)))
    if not description_words or not terms:
        return 0.0
    matched = sum(
        any(word.startswith(term) or term.startswith(word) for word in description_words)
        for term in terms
    )
    return matched / len(terms)
