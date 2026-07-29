import math
import re
from collections import Counter


def split_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        return []
    paragraphs = [item.strip() for item in re.split(r"\n{2,}", cleaned) if item.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= chunk_size:
            current = f"{current}\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue
        start = 0
        while start < len(paragraph):
            chunks.append(paragraph[start : start + chunk_size])
            start += max(1, chunk_size - overlap)
        current = ""
    if current:
        chunks.append(current)
    return chunks


def tokenize(text: str) -> list[str]:
    normalized = text.lower()
    latin = re.findall(r"[a-z0-9_]{2,}", normalized)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", normalized)
    chinese: list[str] = []
    for run in chinese_runs:
        if len(run) == 1:
            chinese.append(run)
        else:
            chinese.extend(run[index : index + 2] for index in range(len(run) - 1))
    return latin + chinese


def score_text(query: str, text: str) -> float:
    query_tokens = Counter(tokenize(query))
    text_tokens = Counter(tokenize(text))
    if not query_tokens or not text_tokens:
        return 0.0
    overlap = sum(min(count, text_tokens[token]) for token, count in query_tokens.items())
    coverage = overlap / max(1, sum(query_tokens.values()))
    density = overlap / math.sqrt(max(1, sum(text_tokens.values())))
    phrase_bonus = 0.5 if query.lower() in text.lower() else 0.0
    return round(coverage * 0.75 + density * 0.25 + phrase_bonus, 4)


def rank_chunks(query: str, chunks: list[dict], limit: int = 6) -> list[dict]:
    ranked = []
    for chunk in chunks:
        score = score_text(query, chunk["content"])
        if score > 0:
            ranked.append({**chunk, "score": score})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]

