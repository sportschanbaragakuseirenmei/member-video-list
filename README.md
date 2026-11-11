# member-video-list

スポーツチャンバラ YouTube チャンネルのメンバー限定動画を検索するページです（GitHub Pages）。

- ページ本体：`index.html`
- 動画一覧：`data/videos.tsv`（1行1本、`動画ID<TAB>公開日<TAB>タイトル`。`#` で始まる行はコメント）

動画を追加したら `data/videos.tsv` に行を足すだけでページに反映されます。
再生にはチャンネルのメンバー登録が必要です。
