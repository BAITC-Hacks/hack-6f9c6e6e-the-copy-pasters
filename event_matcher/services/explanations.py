import re

import pandas as pd

from ..config import QUERY_TERMS
from ..data import normalized
from .relevance import words


def relevant_description(description, event, category) -> str:
    text = re.sub(r"\s+", " ", str(description or "")).strip()
    if not text:
        return ""
    sentences = [part.strip(" •-–") for part in re.split(r"(?<=[.!?])\s+|\s*[•\n]+", text) if part.strip(" •-–")]
    if not sentences:
        sentences = [text]
    query_terms = set()
    for value in (event, category):
        key = normalized(value)
        query_terms.update(QUERY_TERMS.get(key, words(value)))
    chosen = max(enumerate(sentences), key=lambda pair: (len(words(pair[1]) & query_terms), -pair[0]))[1]
    if len(chosen) > 190:
        chosen = chosen[:187].rsplit(" ", 1)[0] + "…"
    return chosen


def explain_match(row, budget, event_date, event, category, hours=None, language=None) -> str:
    price = int(row.price_from_kzt)
    spare = int(budget) - price
    if spare == 0:
        price_fact = f"Цена от {price:,} ₸ — цена совпадает с бюджетом.".replace(",", " ")
    else:
        price_fact = f"Цена от {price:,} ₸ — на {spare:,} ₸ ниже вашего бюджета.".replace(",", " ")
    first = f"Дата {event_date.strftime('%d.%m.%Y')} не отмечена как занята в каталоге; формат «{event}» указан в профиле. {price_fact}"
    facts = []
    if language:
        facts.append(f"Работает на языке «{language}»")
    if hours and pd.notna(row.max_hours):
        facts.append(f"максимум {int(row.max_hours)} ч при запросе {int(hours)} ч")
    elif hours:
        facts.append("длительность присутствия в профиле не указана")
    detail = relevant_description(row.description, event, category)
    if detail:
        facts.append(f"в описании: «{detail}»")
    return (first + " " + "; ".join(facts) + ".").strip() if facts else first
