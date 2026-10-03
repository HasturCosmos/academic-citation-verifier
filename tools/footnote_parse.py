#!/usr/bin/env python
"""Deterministic footnote / endnote parsing for the footnote-first product.

V0.2 (PRODUCT_V0_2_FOOTNOTE_FIRST, D022 / D023) starts from a secondary
quotation/paraphrase **plus its footnote or endnote**. The note is the primary
bibliographic navigation clue, so it gets its own deterministic parser instead
of being folded into the generic free-form ``hints`` field.

This module is intentionally small and stdlib-only. It does not call a model,
the network, or any external service. It extracts the fields that are written
in the note and records where each field came from; anything it cannot read
stays ``None`` / ``unresolved``. It never invents a Chinese title or a
containing publication from a foreign-language work — a missing container is a
missing container, and the user is asked to confirm or supply it.

Public surface:

    parse_note(note)                      -> deterministic field dict
    build_identity(note, secondary, ...)  -> cited work vs containing publication
    identity_queries(identity)            -> targeted lookup queries
    identity_is_useful(identity)          -> "is there anything to search on?"
    describe_identity(identity)           -> plain-language field labels (zh)
    identity_citation_metadata(identity)  -> confirmed fields usable in a citation
    compose_citation_metadata(src, ident) -> source-record + confirmed composition
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------- #
# field vocabulary
# --------------------------------------------------------------------------- #

WORK_TYPES = ("book", "essay", "chapter", "article", "lecture", "unknown")

WORK_TYPE_LABEL_ZH = {
    "book": "整本书",
    "essay": "文章 / 论文",
    "chapter": "书中章节",
    "article": "期刊论文",
    "lecture": "演讲 / 讲稿",
    "unknown": "暂不确定",
}

FIELD_LABEL_ZH = {
    "author": "作者",
    "title": "篇名 / 书名",
    "title_variants": "其他题名",
    "year": "年份",
    "cited_page": "所引页码",
    "translator": "译者",
    "editor": "编者",
    "publisher": "出版社",
    "volume_issue": "卷期",
    "doi": "DOI",
    "isbn": "ISBN",
    "container_title": "收录于",
}

# Recurring reference markers. A note that only says "ibid."/"同上" points back
# to an earlier note the user has not given us; it is a real clue but not a
# standalone identity, so it is flagged rather than guessed.
REFERENCE_MARKERS = ("ibid", "ibid.", "op. cit", "op. cit.", "loc. cit",
                     "同上", "同前", "前引", "前揭", "参见前注")

# --------------------------------------------------------------------------- #
# primitives
# --------------------------------------------------------------------------- #

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9<>]+")
ISBN_RE = re.compile(r"(?:ISBN(?:-1[03])?[:：\s]*)?((?:97[89][\s-]?)?\d[\d\s-]{8,}[\dXx])")

# Chinese-style notes: 作者：《书名》，译者，出版社，年份，第X页。
CN_BOOK_RE = re.compile(r"《([^》]+)》")
CN_QUOTE_RE = re.compile(r"[“\"]([^”\"]{2,})[”\"]")
CN_CONTAINER_RE = re.compile(
    r"(?:载|收[于入]|见|收录于)\s*[《\"“]?([^》\"”，,。；;]{2,})[》\"”]?"
)
CN_PAGE_RE = re.compile(r"第\s*([0-9]+(?:\s*[-–—~]\s*[0-9]+)?)\s*[页頁]")
CN_TRANSLATOR_RE = re.compile(r"([^，,。；;：:\s]{1,24}?)\s*译")
CN_PUBLISHER_RE = re.compile(r"([^，,。；;]+?出版社)")
CN_EDITOR_RE = re.compile(r"([^，,。；;]{1,24}?)\s*(?:主编|编)")
CN_AUTHOR_RE = re.compile(r"^([^：:《》“”\"，,。；;]{1,24})[：:]?\s*[《“\"]")
CN_YEAR_RE = re.compile(r"(1[5-9][0-9]{2}|20[0-9]{2})\s*年")

# Western-style notes: Author, Title (Place: Publisher, Year), page.
EN_YEAR_PAREN_RE = re.compile(r"[(（]\s*[^()（）]*?(1[5-9][0-9]{2}|20[0-9]{2})[^()（）]*?[)）]")
EN_PAGE_RE = re.compile(r"\bpp?\.\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)")
EN_QUOTED_TITLE_RE = re.compile(r"[\"“]([^\"”]{2,})[\"”]")
EN_IN_CONTAINER_RE = re.compile(
    r"\bin\s+(?P<container>[^,(;]+?)\s*(?:,|\(|$)", re.IGNORECASE
)
EN_TRANSLATOR_RE = re.compile(r"\b(?:trans(?:lated by|\.)?|tr\.)\s+([A-Z][^,()]+)", re.IGNORECASE)
EN_EDITOR_RE = re.compile(r"\b(?:ed(?:s)?\.|edited by)\s+([A-Z][^,()]+)", re.IGNORECASE)
EN_VOLUME_RE = re.compile(r"\b(?:vol\.|volume)\s*([0-9IVX]+)(?:\s*,?\s*no\.?\s*([0-9]+))?", re.IGNORECASE)
EN_YEAR_RE = re.compile(r"\b(1[5-9][0-9]{2}|20[0-9]{2})\b")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip(" ,，。;；:：()（）[]【】")
    return text or None


def _first_year(text: str) -> str | None:
    years = EN_YEAR_RE.findall(text or "")
    return years[-1] if years else None


def _normalize_isbn(raw: str) -> str | None:
    digits = re.sub(r"[^0-9Xx]", "", raw or "").upper()
    return digits if len(digits) in (10, 13) else None


def _looks_like_reference_note(note: str) -> bool:
    lowered = (note or "").lower()
    return any(marker in lowered for marker in REFERENCE_MARKERS)


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text or "")


def _strip_quoted(text: str) -> str:
    """Remove quoted spans so "in <container>" is not matched inside a title."""
    return EN_QUOTED_TITLE_RE.sub(" ", text or "")


def _cn_segments(text: str) -> list[str]:
    return [seg.strip() for seg in re.split(r"[，,。；;]", text or "") if seg.strip()]


# --------------------------------------------------------------------------- #
# note parsing
# --------------------------------------------------------------------------- #


def parse_note(note: str) -> dict:
    """Extract the bibliographic fields that are actually written in one note.

    Returns a dict with ``fields``, ``provenance`` (a short reason per field)
    and ``unresolved`` (fields that were looked for but not found). Missing
    fields are simply absent; nothing is inferred from the secondary text here.
    """
    raw = (note or "").strip()
    fields: dict[str, object] = {"title_variants": []}
    provenance: dict[str, str] = {}

    def put(key: str, value, reason: str) -> None:
        if value in (None, "", []):
            return
        if fields.get(key) in (None, "", []):
            fields[key] = value
            provenance[key] = reason

    if not raw:
        return {"raw": raw, "fields": fields, "provenance": provenance,
                "unresolved": ["note"], "reference_note": False, "language": "unknown"}

    doi = DOI_RE.search(raw)
    if doi:
        put("doi", doi.group(0).rstrip(".。，,；;"), "脚注中直接出现的 DOI")
    isbn_match = ISBN_RE.search(raw)
    if isbn_match:
        isbn = _normalize_isbn(isbn_match.group(1))
        if isbn:
            put("isbn", isbn, "脚注中直接出现的 ISBN")

    cjk = _has_cjk(raw)

    if cjk:
        author = CN_AUTHOR_RE.match(raw)
        if author:
            put("author", _clean(author.group(1)), "脚注《》/引号前的作者")

        titles = [_clean(t) for t in CN_BOOK_RE.findall(raw)]
        titles = [t for t in titles if t]
        quoted = [_clean(t) for t in CN_QUOTE_RE.findall(raw)]
        quoted = [t for t in quoted if t]
        container_match = CN_CONTAINER_RE.search(raw)

        if container_match:
            # 载/收于/见/收录于《X》 — X is the containing publication; the
            # cited essay/chapter is the quoted title (or the other 《》 title).
            put("container_title", _clean(container_match.group(1)),
                "脚注中的“载/收于/见”结构标明收录文集")
            remaining = [t for t in titles if t != fields.get("container_title")]
            if quoted:
                put("title", quoted[0], "脚注引号内的篇名")
            elif remaining:
                put("title", remaining[0], "脚注中与收录文集并列的篇名")
            work_type = "essay"
        elif titles:
            put("title", titles[0], "脚注《》内的书名")
            work_type = "book"
            for extra in titles[1:]:
                fields["title_variants"].append({"value": extra, "lang": "zh", "source": "note"})
        elif quoted:
            put("title", quoted[0], "脚注引号内的篇名")
            work_type = "essay"
        else:
            work_type = "unknown"

        page = CN_PAGE_RE.search(raw)
        if page:
            put("cited_page", _clean(page.group(1)), "脚注“第X页”")

        year = CN_YEAR_RE.search(raw)
        put("year", year.group(1) if year else _first_year(raw), "脚注中的年份")

        for segment in _cn_segments(raw):
            if segment.endswith("译") and segment not in (fields.get("title"), "译"):
                put("translator", _clean(segment[:-1]), "脚注“XX译”")
                break

        publisher = CN_PUBLISHER_RE.search(raw)
        if publisher:
            put("publisher", _clean(re.split(r"[：:]", publisher.group(1))[-1]),
                "脚注中的出版社")

        # “某某编/主编” is an editor of the cited book, not a container.
        editor = CN_EDITOR_RE.search(raw)
        if editor and _clean(editor.group(1)) not in (fields.get("author"),):
            put("editor", _clean(editor.group(1)), "脚注“XX编/主编”")
    else:
        quoted = [_clean(t) for t in EN_QUOTED_TITLE_RE.findall(raw)]
        quoted = [t for t in quoted if t]
        in_container = EN_IN_CONTAINER_RE.search(_strip_quoted(raw))

        if quoted:
            put("title", quoted[0], "脚注引号内的篇名")
            if in_container:
                put("container_title", _clean(in_container.group("container")),
                    "脚注 \"in <书名>\" 结构标明收录出版物")
            work_type = "essay"
            opener = EN_QUOTED_TITLE_RE.search(raw)
            head = _clean(raw[: opener.start()]) if opener else None
            if head:
                put("author", head, "脚注引号前的作者")
        else:
            # Author, Title (Place: Publisher, Year), page.
            year_paren = EN_YEAR_PAREN_RE.search(raw)
            head = raw[: year_paren.start()] if year_paren else raw
            segments = [seg.strip() for seg in head.split(",") if seg.strip()]
            if len(segments) >= 2:
                put("author", _clean(segments[0]), "脚注首个逗号前的作者")
                put("title", _clean(segments[1]), "作者后的书名/篇名")
            elif segments:
                put("title", _clean(segments[0]), "脚注中的题名")
            work_type = "book"

        year_paren = EN_YEAR_PAREN_RE.search(raw)
        if year_paren:
            put("year", year_paren.group(1), "括号内的出版年")
            publisher = re.search(r":\s*([^,():（）]+?)\s*[,)]", year_paren.group(0))
            if publisher:
                put("publisher", _clean(publisher.group(1)), "括号内出版社")
        else:
            put("year", _first_year(raw), "脚注中的年份")

        page = EN_PAGE_RE.search(raw)
        if not page and year_paren:
            page = re.search(r"[)）]\s*,\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)\.?\s*$", raw)
        if page:
            put("cited_page", _clean(page.group(1)), "脚注中的页码")

        translator = EN_TRANSLATOR_RE.search(raw)
        if translator:
            put("translator", _clean(translator.group(1)), "脚注 trans./translated by")
        editor = EN_EDITOR_RE.search(raw)
        if editor:
            put("editor", _clean(editor.group(1)), "脚注 ed./edited by")
        volume = EN_VOLUME_RE.search(raw)
        if volume:
            value = volume.group(1)
            if volume.group(2):
                value = f"{value}({volume.group(2)})"
            put("volume_issue", value, "脚注 vol./no.")

    looked_for = ("author", "title", "year", "cited_page", "translator",
                  "editor", "publisher", "container_title")
    unresolved = [key for key in looked_for if fields.get(key) in (None, "", [])]
    return {
        "raw": raw,
        "fields": fields,
        "provenance": provenance,
        "unresolved": unresolved,
        "reference_note": _looks_like_reference_note(raw),
        "language": "zh" if cjk else "western",
        "work_type": work_type,
    }


# --------------------------------------------------------------------------- #
# identity model (cited work vs Chinese containing publication)
# --------------------------------------------------------------------------- #


def build_identity(
    note: str,
    secondary_text: str = "",
    hints: str = "",
    *,
    overrides: dict | None = None,
) -> dict:
    """Resolve one note into a cited work plus containing-publication candidates.

    The cited intellectual work and the Chinese publication that contains it are
    modelled separately on purpose (D022/D023): an essay may be published in
    Chinese only inside a larger collected volume, and the product must not
    collapse the two into one title. ``overrides`` carries the user's edited
    fields from the confirmation screen; an override always wins and is marked
    as coming from the user.

    Nothing here is invented. A foreign-language work with no Chinese clue in
    the note yields a cited work and **no** Chinese containing publication.
    """
    parsed = parse_note(note or hints or "")
    fields = dict(parsed["fields"])
    provenance = dict(parsed["provenance"])

    overrides = {key: value for key, value in (overrides or {}).items() if value}
    for key, value in overrides.items():
        fields[key] = value
        provenance[key] = "用户确认 / 修改"

    title_variants: list[dict] = list(fields.get("title_variants") or [])
    title = fields.get("title")
    if title:
        lang = "zh" if _has_cjk(str(title)) else "orig"
        if not any(variant.get("value") == title for variant in title_variants):
            title_variants.insert(0, {"value": title, "lang": lang, "source": "note"})

    cited_work = {
        "work_type": parsed.get("work_type") or "unknown",
        "author": fields.get("author"),
        "title": title,
        "title_variants": title_variants,
        "year": fields.get("year"),
        "cited_page": fields.get("cited_page"),
        "editor": fields.get("editor"),
        "identifiers": {
            "doi": fields.get("doi"),
            "isbn": fields.get("isbn"),
        },
        "volume_issue": fields.get("volume_issue"),
    }

    container_title = fields.get("container_title")
    containing: list[dict] = []
    if container_title:
        containing.append(
            {
                "title": container_title,
                "editor": fields.get("editor"),
                "translator": fields.get("translator"),
                "publisher": fields.get("publisher"),
                "year": fields.get("year"),
                "source": "note",
            }
        )

    unresolved = [
        key
        for key in ("author", "title", "year", "cited_page", "translator", "editor",
                    "publisher", "container_title")
        if not fields.get(key)
    ]
    if not containing:
        unresolved = sorted(set(unresolved) | {"containing_publication"})

    return {
        "raw_note": (note or "").strip(),
        "secondary_text_chars": len((secondary_text or "").strip()),
        "cited_work": cited_work,
        "containing_publications": containing,
        "title_variants": title_variants,
        "translator": fields.get("translator"),
        "publisher": fields.get("publisher"),
        "provenance": provenance,
        "unresolved": unresolved,
        "reference_note": parsed.get("reference_note", False),
        "note_language": parsed.get("language", "unknown"),
    }


def identity_is_useful(identity: dict) -> bool:
    """True when there is at least one concrete bibliographic handle to search.

    A bare page number or a lone "同上" is not enough: the product asks for a
    better clue instead of launching a broad search (V0.2 Stage 4 / Stage 8.8).
    """
    work = identity.get("cited_work") or {}
    if work.get("title") or work.get("author"):
        return True
    if (work.get("identifiers") or {}).get("doi"):
        return True
    if (work.get("identifiers") or {}).get("isbn"):
        return True
    return bool(identity.get("containing_publications"))


# --------------------------------------------------------------------------- #
# confirmed identity -> citation metadata (composed with the PDF's own record)
# --------------------------------------------------------------------------- #

# Provenance labels used when a confirmed identity is composed with the metadata
# that travels with the primary PDF. They are shown verbatim on the result page,
# so a reader can tell which fields came from the footnote / confirmation screen
# and which came from a source record.
CITATION_PROVENANCE_SOURCE = "一手 PDF 随附的元数据"
CITATION_PROVENANCE_USER = "用户确认（脚注/确认页）"


def _confirmed(value: object) -> bool:
    return value not in (None, "", [])


def identity_citation_metadata(identity: dict | None) -> dict:
    """Map one confirmed identity onto citation-metadata keys.

    The Chinese containing publication is preferred over the cited work when
    both exist, because the PDF being verified *is* that publication. Only
    fields that are explicitly present in the note, or that the user
    confirmed/edited, are returned, each with its provenance.

    When the note describes an original-language work and nothing in it confirms
    a Chinese edition (no Chinese title, container, translator or publisher),
    the title is withheld and ``chinese_edition_confirmed`` is False: the
    product must not dress a foreign edition up as a Chinese citation.
    """
    identity = identity or {}
    work = identity.get("cited_work") or {}
    containers = identity.get("containing_publications") or []
    container = containers[0] if containers else {}
    prov = identity.get("provenance") or {}

    container_title = _clean(container.get("title"))
    work_title = _clean(work.get("title"))
    author = _clean(work.get("author"))
    translator = _clean(container.get("translator")) or _clean(identity.get("translator"))
    publisher = _clean(container.get("publisher")) or _clean(identity.get("publisher"))
    year = _clean(container.get("year")) or _clean(work.get("year"))

    chinese_edition_confirmed = any(
        _has_cjk(str(value))
        for value in (container_title, work_title, translator, publisher)
        if value
    )

    fields: dict[str, object] = {}
    provenance: dict[str, str] = {}

    if author:
        fields["author"] = author
        provenance["author"] = prov.get("author") or CITATION_PROVENANCE_USER

    title = container_title or work_title
    if title and chinese_edition_confirmed:
        fields["title"] = title
        provenance["title"] = (
            prov.get("container_title")
            if container_title and prov.get("container_title")
            else prov.get("title") or CITATION_PROVENANCE_USER
        )

    if chinese_edition_confirmed:
        if translator:
            fields["translator"] = translator
            provenance["translator"] = prov.get("translator") or CITATION_PROVENANCE_USER
        if publisher:
            fields["publisher"] = publisher
            provenance["publisher"] = prov.get("publisher") or CITATION_PROVENANCE_USER
        if year:
            fields["year"] = year
            provenance["year"] = prov.get("year") or CITATION_PROVENANCE_USER

    return {
        "fields": fields,
        "provenance": provenance,
        "chinese_edition_confirmed": chinese_edition_confirmed,
    }


def compose_citation_metadata(
    source_metadata: dict | None, identity: dict | None
) -> dict:
    """Compose the PDF's own metadata with the user-confirmed footnote identity.

    The confirmed identity is the user's explicit claim and therefore wins, but
    a difference from the source record is recorded in ``metadata_conflicts``
    instead of being silently overwritten. Per-field provenance is recorded in
    ``metadata_provenance`` so the result page can label every value honestly.
    """
    source = dict(source_metadata or {})
    source.pop("metadata_provenance", None)
    source.pop("metadata_conflicts", None)
    source_origin = str(source.get("metadata_origin") or CITATION_PROVENANCE_SOURCE)

    merged: dict[str, object] = dict(source)
    provenance: dict[str, str] = {}
    for key, value in source.items():
        if key == "metadata_origin" or not _confirmed(value):
            continue
        provenance[key] = source_origin

    identity_meta = identity_citation_metadata(identity)
    confirmed = identity_meta["fields"]
    conflicts: dict[str, dict] = {}
    for key, value in confirmed.items():
        if not _confirmed(value):
            continue
        current = merged.get(key)
        if _confirmed(current) and str(current).strip() != str(value).strip():
            conflicts[key] = {
                "source_record": current,
                "confirmed": value,
                "used": value,
                "note": "用户确认值覆盖了 PDF 随附记录；原值保留在此处，未丢弃。",
            }
        merged[key] = value
        provenance[key] = identity_meta["provenance"].get(key) or CITATION_PROVENANCE_USER

    origins: list[str] = []
    if confirmed:
        origins.append(CITATION_PROVENANCE_USER)
    if any(
        _confirmed(value) for key, value in source.items() if key != "metadata_origin"
    ):
        origins.append(source_origin)
    if origins:
        merged["metadata_origin"] = " + ".join(dict.fromkeys(origins))
    merged["metadata_provenance"] = provenance
    merged["metadata_conflicts"] = conflicts
    # ``None`` means "no footnote identity was supplied at all" and is different
    # from ``False`` ("an identity was confirmed, but it does not establish a
    # Chinese edition"). The result page only warns in the latter case.
    merged["chinese_edition_confirmed"] = (
        bool(identity_meta["chinese_edition_confirmed"]) if identity else None
    )
    return merged


def identity_queries(identity: dict, *, limit: int = 3) -> list[str]:
    """Targeted lookup strings, generated only from confirmed identity fields.

    When the user has confirmed a Chinese container / translator / publisher,
    that publication-oriented query comes first: the goal of the lookup is to
    find that specific Chinese publication, not to re-search the original work
    in general. DOI/ISBN then author+title follow.
    """
    work = identity.get("cited_work") or {}
    identifiers = work.get("identifiers") or {}
    author = (work.get("author") or "").strip()
    queries: list[str] = []

    for container in identity.get("containing_publications") or []:
        container_title = (container.get("title") or "").strip()
        if not container_title:
            continue
        parts = [container_title]
        for extra in (
            container.get("translator") or identity.get("translator"),
            container.get("publisher") or identity.get("publisher"),
            container.get("year"),
        ):
            extra = str(extra).strip() if extra else ""
            if extra and extra not in parts:
                parts.append(extra)
        queries.append(" ".join(parts))

    if identifiers.get("doi"):
        queries.append(str(identifiers["doi"]))
    if identifiers.get("isbn"):
        queries.append(str(identifiers["isbn"]))

    titles = []
    for variant in identity.get("title_variants") or []:
        value = (variant.get("value") or "").strip()
        if value and value not in titles:
            titles.append(value)
    if work.get("title") and work["title"] not in titles:
        titles.insert(0, work["title"])

    for title in titles:
        if author:
            queries.append(f"{author} {title}".strip())
        else:
            queries.append(title)

    seen: list[str] = []
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        if query and query not in seen:
            seen.append(query)
        if len(seen) >= limit:
            break
    return seen


def describe_identity(identity: dict) -> dict:
    """Plain-language labels for the confirmation screen."""
    work = identity.get("cited_work") or {}
    fields: list[tuple[str, str]] = []
    author = work.get("author")
    title = work.get("title")
    if author and title:
        fields.append(("被引作品", f"{author}：{title}"))
    elif title:
        fields.append(("被引作品", title))
    elif author:
        fields.append(("被引作者", author))
    if work.get("year"):
        fields.append(("年份", str(work["year"])))
    if work.get("cited_page"):
        fields.append(("所引页码", str(work["cited_page"])))
    if identity.get("translator"):
        fields.append(("译者", str(identity["translator"])))
    if identity.get("publisher"):
        fields.append(("出版社", str(identity["publisher"])))
    for container in identity.get("containing_publications") or []:
        if container.get("title"):
            fields.append(("可能收录于", str(container["title"])))
    return {
        "work_type": work.get("work_type") or "unknown",
        "work_type_label": WORK_TYPE_LABEL_ZH.get(work.get("work_type") or "unknown", "暂不确定"),
        "fields": fields,
    }
