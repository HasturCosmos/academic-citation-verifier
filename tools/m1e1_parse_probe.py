"""M1-E1 C04 parsing/chunking probe — zero model calls.

Parses the C04 PDF with the same reader PaperQA2 is configured to use, chunks it
with PaperQA2's own ``chunk_pdf``, and reports page provenance plus whether the
gold sentence and the noisy historical query land in a chunk.

The gold-case values and the page text are read from private local files at
runtime, so no private source text is embedded in this script or in the
repository, and no private text is printed: differences are reported as counts
and Unicode character categories only.
"""

from __future__ import annotations

import difflib
import json
import pathlib
import re
import statistics
import time
import unicodedata

from paperqa.readers import chunk_pdf
from paperqa.settings import ParsingSettings, get_default_pdf_parser
from paperqa.types import Doc, ParsedMetadata, ParsedText

PDF = pathlib.Path("data/private/C04/pqa_corpus/C04.pdf")
GOLD_CASE = pathlib.Path("data/private/C04/M1-E1_C04_gold_case.md")
CACHE = pathlib.Path(".pqa/cache/m1e1_parse.json")
GOLD_PDF_PAGE = "109"
CHUNK_CHARS = 5000
CHUNK_OVERLAP = 250


def _extract(heading: str, lines: list[str]) -> str:
    """Return the first non-empty line after the markdown heading ``heading``."""
    for index, line in enumerate(lines):
        if line.lstrip().startswith("#") and heading in line:
            for candidate in lines[index + 1 :]:
                text = candidate.strip().strip("“”\"'")
                if text:
                    return text
    raise SystemExit(f"heading not found in gold case: {heading}")


def load_gold(path: pathlib.Path = GOLD_CASE) -> tuple[str, str]:
    """Return the (noisy historical query, gold sentence) pair from the gold case."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return _extract("待核文本（原始输入）", lines), _extract("Gold 原文", lines)


def _squash(text: str) -> str:
    """Drop all whitespace so PDF line wrapping cannot break a containment test."""
    return re.sub(r"\s+", "", text)


def _core(text: str) -> str:
    """Keep only alphanumeric/CJK characters.

    The gold-case markdown and the PDF text can differ in quote and punctuation
    characters, so containment is tested on this reduced form.
    """
    return "".join(char for char in text if char.isalnum())


def _covers(chunk_name: str, page: int) -> bool:
    """True when a PaperQA2 label such as 'x.pdf pages 106-112' spans ``page``."""
    span = [int(n) for n in re.findall(r"\d+", chunk_name.split("pages", 1)[-1])]
    return len(span) >= 2 and span[0] <= page <= span[1]


def _categories(text: str, limit: int = 20) -> str:
    """Unicode general categories, so a private diff can be described safely."""
    return ",".join(unicodedata.category(char) for char in text[:limit])


def load_pages() -> tuple[dict[str, str], float, str]:
    """Return (raw page text keyed by PDF page number, parse seconds, source)."""
    stat = PDF.stat()
    if CACHE.exists():
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
        if cached.get("size") == stat.st_size and cached.get("mtime") == stat.st_mtime:
            return cached["pages"], cached["seconds"], "cache"

    parser = get_default_pdf_parser()
    started = time.perf_counter()
    parsed = parser(
        PDF, page_size_limit=ParsingSettings().page_size_limit, parse_media=False
    )
    seconds = time.perf_counter() - started
    content = parsed.content
    assert isinstance(content, dict)
    pages = {
        str(page): entry[0] if isinstance(entry, tuple) else entry
        for page, entry in content.items()
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(
            {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "seconds": seconds,
                "pages": pages,
            }
        ),
        encoding="utf-8",
    )
    return pages, seconds, "parsed"


def main() -> int:
    query, gold = (_squash(value) for value in load_gold())
    query_core, gold_core = _core(query), _core(gold)

    pages, parse_seconds, source = load_pages()
    squashed = {page: _squash(text) for page, text in pages.items()}
    lengths = [len(text) for text in squashed.values()]

    parsed_text = ParsedText(
        content=pages,
        metadata=ParsedMetadata(
            parsing_libraries=["paper-qa-pypdf (cached)"],
            total_parsed_text_length=sum(lengths),
        ),
    )
    started = time.perf_counter()
    chunks = chunk_pdf(
        parsed_text,
        Doc(docname=PDF.name, dockey="c04", citation="C04"),
        CHUNK_CHARS,
        CHUNK_OVERLAP,
    )
    chunk_seconds = time.perf_counter() - started

    matcher = difflib.SequenceMatcher(a=query_core, b=gold_core, autojunk=False)
    block = matcher.find_longest_match(0, len(query_core), 0, len(gold_core))
    shared_run = query_core[block.a : block.a + block.size]
    gold_tail = gold_core[-9:]

    chunk_core = [_core(chunk.text) for chunk in chunks]
    gold_chunks = [i for i, text in enumerate(chunk_core) if gold_core in text]
    shared_chunks = [i for i, text in enumerate(chunk_core) if shared_run in text]
    page_core = {page: _core(text) for page, text in squashed.items()}
    page_109_core = page_core.get(GOLD_PDF_PAGE, "")
    page_109_chunks = [
        i for i, chunk in enumerate(chunks) if _covers(chunk.name, int(GOLD_PDF_PAGE))
    ]

    print(f"pages parsed: {len(pages)} ({source}, {parse_seconds:.1f}s)")
    print(f"total chars (whitespace removed): {sum(lengths)}")
    print(
        "page length stats: "
        f"min={min(lengths)} median={int(statistics.median(lengths))} max={max(lengths)}"
    )
    print(f"pages with <50 chars: {[p for p, t in squashed.items() if len(t) < 50][:20]}")
    print(
        f"chunks (chunk_chars={CHUNK_CHARS}, overlap={CHUNK_OVERLAP}): {len(chunks)} "
        f"in {chunk_seconds:.1f}s"
    )
    print(
        f"gold sentence chars: {len(gold)}; noisy query chars: {len(query)}; "
        f"longest shared run: {block.size} chars of {len(gold_core)}"
    )
    print(
        f"gold wording present on PDF page {GOLD_PDF_PAGE}: "
        f"{gold_core in page_109_core}"
    )
    print(f"gold sentence tail present on page {GOLD_PDF_PAGE}: {gold_tail in page_109_core}")
    start = page_109_core.find(shared_run)
    after = start + len(shared_run)
    tail_at = page_109_core.find(gold_tail, after)
    if start >= 0 and tail_at >= 0:
        gap = page_109_core[after:tail_at]
        print(
            f"page {GOLD_PDF_PAGE} gap between shared run and tail: "
            f"{len(gap)} core chars; categories: {_categories(gap)}"
        )
    print(f"chunk labels containing page {GOLD_PDF_PAGE}: {[chunks[i].name for i in page_109_chunks]}")
    print(f"chunk indices containing the full gold sentence: {gold_chunks}")
    print(f"chunk indices containing the longest shared run: {shared_chunks}")
    print(f"their page-range labels: {[chunks[i].name for i in shared_chunks]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
