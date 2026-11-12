"""data/videos.tsv の全動画の再生回数を YouTube Data API で取り直し、data/views.tsv を書き換える。
メンバー限定動画の再生回数はチャンネル所有者の許可が必要なので、
環境変数 YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN（読み取り専用の OAuth）を使う。
これらがなければ YT_API_KEY を使う（メンバー限定動画は 0 になる）。"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

key = os.environ.get("YT_API_KEY")
cid, csec, rtok = (os.environ.get(n) for n in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
headers = {}
if cid and csec and rtok:
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": csec, "refresh_token": rtok,
                                   "grant_type": "refresh_token"}).encode()
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=30) as r:
            headers = {"Authorization": "Bearer " + json.load(r)["access_token"]}
    except urllib.error.HTTPError as e:
        sys.exit(f"ログインの許可（リフレッシュトークン）が使えません: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
    key = None
elif not key:
    sys.exit("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN も YT_API_KEY も設定されていません")
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
    params = {"part": "statistics", "id": ",".join(batch), "fields": "items(id,statistics/viewCount)"}
    if key:
        params["key"] = key
    q = urllib.parse.urlencode(params)
    data = None
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://www.googleapis.com/youtube/v3/videos?" + q, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
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
nonzero = sum(1 for i in ids if views.get(i, "0") not in ("0", 0))
if nonzero < len(ids) * 0.5:
    sys.exit("再生回数がほとんど0になっているので（メンバー限定動画は所有者のログインが必要）、更新しません")
if fetched < len(ids) * 0.9:
    sys.exit("取れた本数が少なすぎるので、失敗として扱います")
