"""Scrapes https://dico.elix-lsf.fr for a word's LSF sign videos and definitions.

The site server-renders everything we need (word, part of speech, per-meaning
definitions, and <video src> URLs) directly in the HTML, so a plain HTTP GET
plus BeautifulSoup parse is enough — no headless browser required.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://dico.elix-lsf.fr"
HEADERS = {"User-Agent": "Elixcopter/1.0 (personal LSF flashcard study tool)"}


@dataclass
class Meaning:
    word: str
    part_of_speech: str
    definition: str
    source_url: str
    video_urls: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class ElixLookupError(Exception):
    pass


def word_url(word: str) -> str:
    return f"{BASE_URL}/dictionnaire/{quote(word)}"


def search_word(word: str) -> dict:
    """Look up a word on the Elix dictionary.

    Returns a dict: {"word": str, "url": str, "meanings": [Meaning...], "suggestions": [str...]}
    `meanings` is empty when there's no exact match; `suggestions` then holds
    alternate words the site proposes instead.
    """
    url = word_url(word)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    meanings: list[Meaning] = []
    for word_section in soup.select("section.word"):
        title_el = word_section.select_one("h2.word__title")
        if not title_el:
            continue
        title_text = title_el.get_text(" ", strip=True)
        # e.g. "crier (v.)" -> word="crier", pos="v."
        base_word, _, pos = title_text.rpartition("(")
        base_word = base_word.strip() or title_text
        pos = pos.replace(")", "").strip()

        for article in word_section.select("article.meaning-renderer"):
            heading = article.select_one("header h3")
            definition = heading.get_text(" ", strip=True) if heading else ""
            source_a = article.select_one("a.source")
            source_url = source_a["href"] if source_a and source_a.has_attr("href") else url

            video_urls = [
                urljoin(BASE_URL, v["src"])
                for v in article.select(".meaning-videos video[src]")
                if v.has_attr("src")
            ]
            if not video_urls:
                continue

            meanings.append(
                Meaning(
                    word=base_word,
                    part_of_speech=pos,
                    definition=definition,
                    source_url=source_url,
                    video_urls=video_urls,
                )
            )

    suggestions: list[str] = []
    if not meanings:
        for a in soup.select("section#suggestions a"):
            text = a.get_text(" ", strip=True)
            href = a.get("href", "")
            if text and href.startswith("/dictionnaire/"):
                suggestions.append(text)
        # de-dupe while preserving order
        seen = set()
        deduped = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        suggestions = deduped[:20]

    return {
        "word": word,
        "url": url,
        "meanings": [m.to_dict() for m in meanings],
        "suggestions": suggestions,
    }


def download_video(video_url: str, dest_path: str) -> None:
    resp = requests.get(video_url, headers=HEADERS, timeout=30, stream=True)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            if chunk:
                f.write(chunk)
