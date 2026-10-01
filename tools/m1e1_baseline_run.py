"""Run the single authorized M1-E1 C04 baseline and capture raw evidence.

Uses PaperQA2's core API — ``Docs.aadd`` plus ``Docs.aquery``, the same layer the
CLI agent calls — because the agent's file-level ``paper_search`` cannot match
Chinese text (see TASK_QUEUE / RUN_LOG for the recorded finding).

Reads the pinned settings and the historical noisy query from the private gold
case, writes the full raw result (answer, ranked contexts, page labels, usage)
into the private data directory, and prints only aggregate facts so that no
private source text reaches the repository or the terminal.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import m1e1_parse_probe as probe  # noqa: E402
from paperqa.docs import Docs  # noqa: E402
from paperqa.settings import Settings  # noqa: E402

SETTINGS = pathlib.Path(".pqa/settings/m1e1_c04.json")
RESULTS_DIR = pathlib.Path("data/private/C04/results")


async def run() -> int:
    settings = Settings.model_validate_json(SETTINGS.read_text(encoding="utf-8"))
    query, gold = probe.load_gold()
    gold_core = probe._core(probe._squash(gold))

    started = time.perf_counter()
    docs = Docs()
    await docs.aadd(probe.PDF, settings=settings)
    aadd_seconds = time.perf_counter() - started

    started = time.perf_counter()
    session = await docs.aquery(query, settings=settings)
    query_seconds = time.perf_counter() - started

    records = []
    for index, context in enumerate(session.contexts):
        text = getattr(context, "text", None)
        records.append(
            {
                "rank": index + 1,
                "page_label": getattr(text, "name", None),
                "score": getattr(context, "score", None),
                "text": getattr(text, "text", None),
            }
        )
    gold_hits = [
        record["rank"]
        for record in records
        if record["text"] and gold_core in probe._core(record["text"])
    ]
    page_hits = [
        record["rank"]
        for record in records
        if record["page_label"] and probe._covers(record["page_label"], int(probe.GOLD_PDF_PAGE))
    ]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"m1e1_c04_{stamp}.json"
    out_path.write_text(
        json.dumps(
            {
                "run_at": stamp,
                "aadd_seconds": aadd_seconds,
                "query_seconds": query_seconds,
                "settings": settings.model_dump(mode="json"),
                "query_chars": len(query),
                "answer": session.answer,
                "raw_answer": session.raw_answer,
                "has_successful_answer": session.has_successful_answer,
                "formatted_answer": session.formatted_answer,
                "cost": str(getattr(session, "cost", None)),
                "token_counts": str(getattr(session, "token_counts", None)),
                "contexts": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"aadd_seconds: {aadd_seconds:.0f}")
    print(f"query_seconds: {query_seconds:.0f}")
    print(f"answer_chars: {len(session.answer or '')}")
    print(f"has_successful_answer: {session.has_successful_answer}")
    print(f"contexts_returned: {len(records)}")
    print(f"gold_rank_by_wording: {gold_hits}")
    print(f"ranks_covering_page_{probe.GOLD_PDF_PAGE}: {page_hits}")
    print(f"page_labels: {[r['page_label'] for r in records]}")
    print(f"scores: {[r['score'] for r in records]}")
    print(f"cost: {getattr(session, 'cost', None)}")
    print(f"token_counts: {getattr(session, 'token_counts', None)}")
    print(f"raw_result_written_to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
