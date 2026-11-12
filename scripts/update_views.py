"""data/videos.tsv の全動画の再生回数を YouTube Data API で取り直し、data/views.tsv を書き換える。
環境変数 YT_API_KEY に YouTube Data API v3 の APIキーが必要。"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
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
    data = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + q, timeout=30) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(body)["error"]
                reason = ", ".join(x.get("reason", "") for x in err.get("errors", []))
                msg = f"HTTP {e.code} {reason}: {err.get('message', '')}"
            except Exception:
                msg = f"HTTP {e.code}: {body[:300]}"
            print(f"[{k // 50 + 1}回目の呼び出し] {msg}", flush=True)
            if e.code in (400, 401, 403) and "rateLimit" not in msg and "backendError" not in msg:
                break  # キーの設定やAPIの有効化の問題。再試行しても直らない
            time.sleep(2 ** attempt)
        except Exception as e:  # 通信の一時的なエラー
            print(f"[{k // 50 + 1}回目の呼び出し] {e}", flush=True)
            time.sleep(2 ** attempt)
    if data is None:
        if not views:
            sys.exit("最初の呼び出しで失敗したので、再生回数は更新しません")
        print("途中で失敗したので、ここまで取れた分だけ更新します", flush=True)
        break
    for it in data.get("items", []):
        views[it["id"]] = it["statistics"].get("viewCount", "0")
fetched = len(views)
# 取れなかった動画（非公開になったもの、途中で止まった分など）は前回の値を残す
for i in ids:
    if i not in views and i in old:
        views[i] = old[i]
jst = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
with open("data/views.tsv", "w", encoding="utf-8") as f:
    f.write(f"# updated: {jst}\n# 形式: 動画ID\t再生回数\n")
    for i in ids:
        if i in views:
            f.write(f"{i}\t{views[i]}\n")
print(f"今回取れたのは {fetched} / {len(ids)} 本です（取れなかった分は前回の値のまま）")
if fetched < len(ids) * 0.9:
    sys.exit("取れた本数が少なすぎるので、失敗として扱います")
