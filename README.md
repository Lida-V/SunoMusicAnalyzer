# SunoMusicAnalyzer

Suno公式MCPの楽曲分析を使い、制作意図と音の特徴、曲の展開、ミックスの所見、改善案を **A3縦・1ページの図解PDF** にまとめる再利用可能なSkillです。既存曲の分析とレポート作成を対象にし、テストのために楽曲を生成・編集しません。

It is a reusable agent skill that turns evidence from Suno's official MCP into an illustrated one-page music analysis PDF. Findings are labeled by source and uncertainty; the renderer does not invent missing data.

## できること

- 曲名、取得できた制作スタイル、歌詞欄の構成・演奏タグを整理。歌詞本文はPDFに掲載しません。
- 複数ジャンルの音楽的特徴を示し、目標がある場合はスタイルとの一致を比較。
- 取得できた曲の区間と時刻、展開、声・編成、ミックスの印象、改善候補を図解。
- Sunoの分析結果とユーザーの指定、ローカルで測定した値、提案を出典付きで区別。
- 楽曲の情報に合わせたテーマを選択。配色・図形はデザイン上の演出です。

Sunoの出力は推定を含みます。モデル間の不一致、取得できなかった項目、根拠のないジャンルの割合や時刻は、そのまま明示します。分析結果から歌詞や楽曲の実際の構成を自動的に確定するものではありません。

## 必要なもの

- Sunoアカウントと、公式Suno MCPを利用できるMCP対応クライアント。
- Python 3.9以上と [ReportLab](https://pypi.org/project/reportlab/)。
- 日本語などCJK文字を表示する場合は、ReportLabで使えるCJK TrueTypeフォント。`.ttf` または `.ttc` を使用し、CFF/PostScript形式は使用できません。OSに適切なフォントがなければ、別途用意して `--font` で指定します。
- PDFを画像として確認するためのレンダラー（例: Popplerの `pdftoppm`）。
- テストを実行する場合は `pypdf`。通常のPDF生成に必要なPythonパッケージは `reportlab` です。

利用可能なMCPツール・認証・制限は変更される場合があります。[Suno公式の接続案内](https://help.suno.com/en/articles/14551425)と使用時のツール説明を確認してください。ローカル音源をSuno側へアップロードする場合は、送信先と対象の利用権限を確認します。

## インストール

1. このリポジトリをクローンまたはダウンロードします。
2. `skills/suno-music-analyzer` フォルダを、利用するエージェントのスキル格納先に配置します。Codexの場合は通常 `~/.codex/skills/`、Claude Codeの場合は通常 `~/.claude/skills/` です。既に同名のフォルダがある場合は、上書き前に内容を確認してください。
3. 使用するPython環境に依存を入れます。

   ```sh
   python -m pip install reportlab
   ```

   リポジトリのテストも実行する場合は `python -m pip install pypdf` を追加してください。

4. Suno公式MCPをクライアントへ接続し、Sunoアカウントで認可します。Codex CLIでは、例えば次のコマンドを使用します。

   ```sh
   codex mcp add suno --url https://api.suno.com/mcp
   codex mcp login suno
   ```

   クライアントの設定画面やログイン手順は、お使いのバージョンの案内に従ってください。認証情報をSkillやGitへ保存しないでください。

## 使い方

対象曲を指定し、例えば「このSunoの曲を分析して１ページのPDFにして」と依頼します。目標ジャンルや用途が分かっていれば一緒に伝えると、目標との照合や改善案に反映できます。

Skillは、公式MCPの `audio-retrieve`、`audio-listen`、`audio-listen-wait`、必要に応じた `audio-analysis` の実際の応答を確認して分析します。対象曲IDを統一し、一覧の順番だけで別の曲を選び直しません。`audio-listen` は１曲・１依頼につき標準３問、必要な場合は最大５問です。ユーザー指定の回数を優先し、同じ質問への待機は新しい質問と区別します。サービス側の日次上限は使用時に確認してください。

エージェントが分析結果を[入力仕様](skills/suno-music-analyzer/references/report-schema.md)に沿ったJSONへ整理した後、Skillフォルダから次のようにPDFを生成できます。

```sh
python scripts/suno-one-page-report.py output/report.json --output output/report.pdf
```

レイアウトを先に確認する場合は、リポジトリのルートから次を実行できます。`examples/synthetic-report.json` は内容・数値ともに架空のサンプルで、実際の楽曲の分析結果ではありません。

```sh
python skills/suno-music-analyzer/scripts/suno-one-page-report.py examples/synthetic-report.json --output output/sample-report.pdf
```

明示的にフォントを指定する場合:

```sh
python scripts/suno-one-page-report.py output/report.json --output output/report.pdf --font /path/to/font.ttf
```

TTCコレクションは必要に応じて `--font-index 0` のように番号を指定できます。`--font` で明示した場合、見出しも本文と同じ書体になります。macOS・Linuxのフォント自動検出は候補パスを使った合成テストのみで、実機環境では未検証です。

PDFを描画して文字・図・ページ数を確認してください。入力が紙面に収まらない場合、原文を別ファイルに保持した上で、要約であることを明記して再出力します。曲の詳細データ・音源・歌詞・認証情報を公開リポジトリへ入れないでください。

## 構成

- [Skill](skills/suno-music-analyzer/SKILL.md): トリガーと作業手順。
- [分析ワークフロー](skills/suno-music-analyzer/references/analysis-workflow.md): 情報の集め方、質問回数、出典と不確実性。
- [PDF入力仕様](skills/suno-music-analyzer/references/report-schema.md): JSONの項目、形式、実行方法。
- `skills/suno-music-analyzer/scripts/`: PDF生成と曲情報整理の補助スクリプト。

## ライセンス

このリポジトリは [MIT License](LICENSE) です。Sunoのサービス・生成物・フォント・その他の依存関係には、それぞれの利用条件が適用されます。
