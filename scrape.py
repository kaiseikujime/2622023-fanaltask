import json
import re
import sqlite3
import time

import requests

BASE = "https://github.com/orgs/google/repositories"
HEADERS = {"User-Agent": "Mozilla/5.0"}
PATTERN = re.compile(
    r'<script type="application/json" data-target="react-app.embeddedData">(.*?)</script>',
    re.S,
)


def fetch_page(page):
    for attempt in range(6):
        res = requests.get(BASE, params={"page": page}, headers=HEADERS, timeout=30)
        if res.status_code == 429:
            wait = int(res.headers.get("Retry-After", 60))
            print(f"429: {wait}秒待ってリトライ ({attempt + 1}/6)")
            time.sleep(wait)
            continue
        res.raise_for_status()
        for raw in PATTERN.findall(res.text):
            data = json.loads(raw)
            route = data.get("payload", {}).get("orgReposPageRoute")
            if route:
                return route["pageCount"], route["repositories"]
        raise RuntimeError(f"page {page}: データが見つかりません")
    raise RuntimeError(f"page {page}: 429が続いたため中断")


def main():
    con = sqlite3.connect("google_repos.db")
    con.execute(
        "CREATE TABLE IF NOT EXISTS repositories ("
        "name TEXT PRIMARY KEY, language TEXT, stars INTEGER)"
    )
    page, page_count = 1, 1
    while page <= page_count:
        page_count, repos = fetch_page(page)
        for r in repos:
            lang = (r.get("primaryLanguage") or {}).get("name")
            con.execute(
                "INSERT OR REPLACE INTO repositories VALUES (?, ?, ?)",
                (r["name"], lang, r["starsCount"]),
            )
        con.commit()
        print(f"page {page}/{page_count}: {len(repos)}件")
        page += 1
        time.sleep(1)

    for row in con.execute(
        "SELECT name, language, stars FROM repositories ORDER BY stars DESC"
    ):
        print(row)
    con.close()


if __name__ == "__main__":
    main()