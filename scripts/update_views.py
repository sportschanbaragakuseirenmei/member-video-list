"""data/videos.tsv の全動画の再生回数を YouTube Data API で取り直し、data/views.tsv を書き換える。
環境変数 YT_API_KEY に YouTube Data API v3 の APIキーが必要。"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

key = os.environ.get("YT_API_KEY")
if not key:
    sys.exit("YT_API_KEY が設定されていません")
ids = [l.split("\t")[0] for l in open("data/videos.tsv", encoding="utf-8")
       if l.strip() and not l.startswith("#")]
old = {}
for l in open("data/views.tsv", encoding="utf-8"):
    if l.strip() and not l.startswith("#"):
        i, c = l.rstrip("\n").split("\t")[:2]
        old[i] = c
views = {}
for k in range(0, len(ids), 50):
    batch = ids[k:k + 50]
    q = urllib.parse.urlencode({"part": "statistics", "id": ",".join(batch), "key": key,
                                "fields": "items(id,statistics/viewCount)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + q, timeout=30) as r:
                data = json.load(r)
            break
        except Exception as e:  # 一時的なエラーは少し待って再試行
            if attempt == 3:
                sys.exit(f"取得に失敗しました: {e}")
            time.sleep(2 ** attempt)
    for it in data.get("items", []):
        views[it["id"]] = it["statistics"].get("viewCount", "0")
# 取れなかった動画（非公開になったものなど）は前回の値を残す
for i in ids:
    if i not in views and i in old:
        views[i] = old[i]
jst = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
with open("data/views.tsv", "w", encoding="utf-8") as f:
    f.write(f"# updated: {jst}\n# 形式: 動画ID\t再生回数\n")
    for i in ids:
        if i in views:
            f.write(f"{i}\t{views[i]}\n")
print(f"{len(views)} / {len(ids)} 本の再生回数を更新しました")
