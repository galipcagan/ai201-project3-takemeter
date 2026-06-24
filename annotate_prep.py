"""
Build a clean candidate pool for annotation from the parsed thread JSON files.

Steps:
  - load all data/<thread>.json
  - drop the post rows (auto-generated match templates), keep comments
  - filter out very short / low-content comments
  - drop bot/automod boilerplate
  - dedupe on normalized text
  - write data/candidates.csv  (id, thread_type, score, word_len, text)
"""

import csv
import json
import os
import re

THREADS = {
    "match_thread": "match_thread",
    "analysis_thread": "analysis_thread",
    "transfer_thread": "transfer_thread",
    "Daily_discussion": "daily_discussion",
}

MIN_WORDS = 5            # drop comments shorter than this
MIN_CHARS = 25
BOT_MARKERS = ("i am a bot", "this comment was removed", "^^this ^^action")


def normalize(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def is_low_content(text):
    words = text.split()
    if len(words) < MIN_WORDS or len(text.strip()) < MIN_CHARS:
        return True
    low = text.lower()
    if any(m in low for m in BOT_MARKERS):
        return True
    # emoji / punctuation only
    if not re.search(r"[a-zA-Z]", text):
        return True
    return False


def main():
    seen = set()
    rows = []
    for fname, thread_type in THREADS.items():
        path = os.path.join("data", fname + ".json")
        data = json.load(open(path, encoding="utf-8"))
        for r in data:
            if r["kind"] != "comment":
                continue
            text = r["body"].strip()
            if is_low_content(text):
                continue
            key = normalize(text)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "id": r["id"],
                    "thread_type": thread_type,
                    "score": r["score"],
                    "word_len": len(text.split()),
                    "text": " ".join(text.split()),
                }
            )

    out = os.path.join("data", "candidates.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "thread_type", "score", "word_len", "text"])
        w.writeheader()
        w.writerows(rows)

    # report
    by_thread = {}
    for r in rows:
        by_thread[r["thread_type"]] = by_thread.get(r["thread_type"], 0) + 1
    print(f"Wrote {len(rows)} candidates -> {out}")
    for t, n in sorted(by_thread.items()):
        print(f"  {t:<18} {n}")


if __name__ == "__main__":
    main()
