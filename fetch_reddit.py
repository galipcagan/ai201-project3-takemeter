"""
Fetch posts/comments from r/soccer using Reddit's public .json endpoints.

Method: append `.json` to any Reddit listing or thread URL and request it
with a real User-Agent header (Reddit rejects the default urllib agent).

NOTE: Reddit blocks programmatic requests from non-residential IPs (HTTP 403
"Blocked"), so the fetch commands below only work from a residential network.
If they fail, save the raw .json from your browser (open the URL with `.json`
appended, Ctrl+S) and use the `parse` command to flatten it instead.

Usage:
    python fetch_reddit.py explore        # small varied sample to read by hand
    python fetch_reddit.py listing hot 50 # fetch a listing (hot/new/top), N posts
    python fetch_reddit.py thread <url>   # fetch all comments from one thread
    python fetch_reddit.py parse <file>   # flatten a browser-saved .json to CSV

Output goes to data/ as raw JSON plus a flat CSV for reading.
"""

import csv
import json
import os
import sys
import time
import urllib.request

HEADERS = {"User-Agent": "takemeter-coursework/0.1 (educational data collection)"}
DATA_DIR = "data"


def get_json(url):
    if not url.endswith(".json"):
        url = url.rstrip("/") + ".json"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_listing(sort="hot", limit=50):
    """Fetch top-level posts from a subreddit listing."""
    url = f"https://www.reddit.com/r/soccer/{sort}.json?limit={limit}"
    data = get_json(url)
    posts = []
    for child in data["data"]["children"]:
        d = child["data"]
        posts.append(
            {
                "id": d["id"],
                "kind": "post",
                "title": d.get("title", ""),
                "body": d.get("selftext", ""),
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "permalink": "https://www.reddit.com" + d.get("permalink", ""),
            }
        )
    return posts


def fetch_thread_comments(url, limit=200):
    """Fetch comments from a single thread."""
    data = get_json(url)
    comments = []

    def walk(children):
        for child in children:
            if child.get("kind") != "t1":
                continue
            d = child["data"]
            body = d.get("body", "")
            if body and body not in ("[deleted]", "[removed]"):
                comments.append(
                    {
                        "id": d["id"],
                        "kind": "comment",
                        "title": "",
                        "body": body,
                        "score": d.get("score", 0),
                        "num_comments": 0,
                        "permalink": "https://www.reddit.com" + d.get("permalink", ""),
                    }
                )
            replies = d.get("replies")
            if isinstance(replies, dict):
                walk(replies["data"]["children"])

    # data[0] is the post listing, data[1] is the comment tree
    walk(data[1]["data"]["children"])
    return comments[:limit]


def save(rows, name):
    os.makedirs(DATA_DIR, exist_ok=True)
    json_path = os.path.join(DATA_DIR, name + ".json")
    csv_path = os.path.join(DATA_DIR, name + ".csv")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "kind", "title", "body", "score", "num_comments", "permalink"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows -> {json_path} and {csv_path}")


def parse_file(path):
    """Flatten a browser-saved Reddit .json file (listing or thread) to CSV."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    # Already-flattened rows from browser_snippet.js (list of plain dicts).
    if isinstance(data, list) and data and "body" in data[0]:
        rows = data
    # A thread .json is a 2-element list: [post listing, comment tree].
    elif isinstance(data, list) and len(data) == 2:
        post = data[0]["data"]["children"][0]["data"]
        rows.append(
            {
                "id": post["id"],
                "kind": "post",
                "title": post.get("title", ""),
                "body": post.get("selftext", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "permalink": "https://www.reddit.com" + post.get("permalink", ""),
            }
        )

        def walk(children):
            for child in children:
                if child.get("kind") != "t1":
                    continue
                d = child["data"]
                body = d.get("body", "")
                if body and body not in ("[deleted]", "[removed]"):
                    rows.append(
                        {
                            "id": d["id"],
                            "kind": "comment",
                            "title": "",
                            "body": body,
                            "score": d.get("score", 0),
                            "num_comments": 0,
                            "permalink": "https://www.reddit.com" + d.get("permalink", ""),
                        }
                    )
                replies = d.get("replies")
                if isinstance(replies, dict):
                    walk(replies["data"]["children"])

        walk(data[1]["data"]["children"])
    # A listing .json is a single dict with data.children.
    elif isinstance(data, dict) and "data" in data:
        for child in data["data"]["children"]:
            d = child["data"]
            rows.append(
                {
                    "id": d["id"],
                    "kind": "post" if child.get("kind") == "t3" else "comment",
                    "title": d.get("title", ""),
                    "body": d.get("selftext") or d.get("body", ""),
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "permalink": "https://www.reddit.com" + d.get("permalink", ""),
                }
            )
    else:
        raise ValueError("Unrecognized Reddit JSON shape")
    name = os.path.splitext(os.path.basename(path))[0]
    save(rows, name)


def explore():
    """Grab a small, varied sample to read by hand before designing labels."""
    all_rows = []
    posts = fetch_listing("hot", 25)
    all_rows.extend(posts)
    print(f"Fetched {len(posts)} hot posts. Pulling comments from a few threads...")
    # pull comments from the 3 most-commented threads for reaction/take variety
    busy = sorted(posts, key=lambda p: p["num_comments"], reverse=True)[:3]
    for p in busy:
        time.sleep(2)  # be polite to Reddit
        try:
            comments = fetch_thread_comments(p["permalink"], limit=15)
            all_rows.extend(comments)
            print(f"  + {len(comments)} comments from: {p['title'][:60]}")
        except Exception as e:
            print(f"  ! failed on {p['permalink']}: {e}")
    save(all_rows, "explore_sample")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "explore"
    if cmd == "explore":
        explore()
    elif cmd == "listing":
        sort = sys.argv[2] if len(sys.argv) > 2 else "hot"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        save(fetch_listing(sort, limit), f"listing_{sort}")
    elif cmd == "thread":
        url = sys.argv[2]
        save(fetch_thread_comments(url), "thread_" + url.rstrip("/").split("/")[-1])
    elif cmd == "parse":
        parse_file(sys.argv[2])
    else:
        print(__doc__)
