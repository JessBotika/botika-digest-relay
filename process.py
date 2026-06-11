"""Filter, rank, and trim the raw Apify tweet dataset for the Yarin ML digest.

Reads raw.json (the full Apify dataset), keeps tweets from the last 7 days,
drops already-famous accounts, ranks by engagement, caps the list, and writes
a compact yarin_tweets.json that the cloud digest routine reads via WebFetch.
"""
import json
import datetime
from datetime import timezone, timedelta

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

cutoff = datetime.datetime.now(timezone.utc) - timedelta(days=7)
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
out = out[:60]

with open("yarin_tweets.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=0)

print(f"Wrote {len(out)} tweets to yarin_tweets.json (from {len(items)} raw items)")
