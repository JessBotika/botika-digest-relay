"""Filter, rank, and trim the raw Apify tweet dataset for the Yarin ML digest.

Reads raw.json (the full Apify dataset), keeps tweets from the last 7 days,
drops already-famous accounts, ranks by engagement, caps the list, and writes
a compact yarin_tweets.json that the cloud digest routine reads via WebFetch.
"""
import json
import os
import datetime
from datetime import timezone, timedelta

# Days of history to keep. Defaults to 7 for the daily routine; override with
# CUTOFF_DAYS for catch-up / test runs (e.g. CUTOFF_DAYS=4).
CUTOFF_DAYS = int(os.environ.get("CUTOFF_DAYS", "7"))

# Robust date parsing: prefer dateutil (handles Twitter + ISO formats), fall back to ISO.
try:
    from dateutil import parser as _dp

    def parse_date(s):
        return _dp.parse(s)
except Exception:  # pragma: no cover
    def parse_date(s):
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))

FAMOUS = {
    "karpathy", "ylecun", "goodfellow_ian", "fchollet", "demishassabis",
    "jeffdean", "huggingface", "andrewyng", "openai", "googleai",
    "googledeepmind", "aiatmeta",
}

with open("raw.json", encoding="utf-8") as f:
    items = json.load(f)

if not isinstance(items, list):
    raise SystemExit(f"Expected a JSON array from Apify, got {type(items).__name__}: {str(items)[:200]}")

cutoff = datetime.datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)
out = []
for t in items:
    author = t.get("author") or {}
    handle = author.get("userName") or "unknown"
    if handle.lower() in FAMOUS:
        continue
    raw_date = t.get("createdAt", "") or ""
    try:
        d = parse_date(raw_date)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        if d < cutoff:
            continue
    except Exception:
        pass  # keep if the date can't be parsed
    out.append({
        "userName": handle,
        "text": t.get("text", "") or "",
        "likeCount": t.get("likeCount", 0) or 0,
        "retweetCount": t.get("retweetCount", 0) or 0,
        "url": t.get("url", "") or "",
        "createdAt": raw_date,
    })

out.sort(key=lambda x: x["likeCount"] + 2 * x["retweetCount"], reverse=True)
out = out[:40]

# Paginate into small files so WebFetch returns them verbatim (no summarization
# of a large blob). PAGE=20 keeps each file well under the size that triggers
# WebFetch's extraction/summarization step.
PAGE = 20
pages = [out[i:i + PAGE] for i in range(0, len(out), PAGE)] or [[]]
for idx, chunk in enumerate(pages, start=1):
    fname = f"yarin_tweets_{idx}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(chunk, f, ensure_ascii=False, indent=0)
    print(f"Wrote {len(chunk)} tweets to {fname}")

print(f"Total {len(out)} tweets across {len(pages)} page(s) (from {len(items)} raw items)")
