# seras-english-grammar プロジェクト

英語参考書PDF（6冊）を高品質なMarkdownに変換するOCRプロジェクト。

---

## プロジェクト概要

### 目的
- 英語参考書のPDFを文字データ（Markdown）に変換
- 複数LLMを使い分け、品質と効率を両立
- 長期間の作業に耐えられる一貫したワークフロー

### 対象書籍（6冊）

| 書籍名 | ファイル構成 | ステータス |
|--------|-------------|-----------|
| 核心 | 前半 + 後半 | 目次完了（21章） |
| 成川 | 前半 + 後半 + 別冊 | 目次完了（162章） |
| スクランブル | 前半 + 後半 | 未着手 |
| 肘井 | 本体 + 別冊 | 未着手 |
| 入門英文 | 1ファイル | 未着手 |
| はじめの英文読解ドリル | 1ファイル | 未着手 |

---

## ディレクトリ構造

```
.
├── CLAUDE.md                   # このファイル（最重要）
├── .claude/
│   ├── commands/               # skills定義
│   │   ├── ocr-toc.md
│   │   ├── ocr-chapter.md
│   │   ├── ocr-review.md
│   │   └── ocr-status.md
│   └── settings.local.json     # hooks設定
├── .rules/
│   ├── ocr-workflow.md         # ワークフロー詳細
│   └── notation-rules.md       # 表記ルール
├── progress/
│   ├── status.json             # 進捗管理 v2.0
│   └── logs/
│       ├── reviews/            # Codexレビューログ
│       ├── errors/             # エラーログ
│       └── spot_checks/        # スポットチェックログ
├── pdf/
│   ├── raw/                    # 元PDF（横向き）
│   ├── rotated/                # 回転済みPDF（縦向き）
│   ├── images/                 # 画像化したもの
│   │   └── {書籍名}/           # page_001.png, page_002.png...
│   └── output/                 # 完成Markdown
│       └── {書籍名}/
├── scripts/
│   ├── pdf_tools.py            # PDF操作ツール（info, to-images, split, page-map）
│   ├── extract_chapters.py     # 目次から章情報を抽出
│   ├── migrate_status.py       # status.json v1.0→v2.0移行
│   └── rotate_all.py           # 全PDF回転スクリプト
└── tests/
    ├── conftest.py             # テストfixture
    ├── test_pdf_tools.py       # pdf_tools.pyのテスト
    └── fixtures/               # テスト用ファイル
```

---

## 役割分担（重要）

| 役割 | 担当 | 責務 |
|------|------|------|
| **オーケストレーター** | Claude Code (メイン) | 全体管理、進捗追跡、品質判断、**実作業はしない** |
| **書き起こし** | Claude subagent | 画像→Markdown変換 |
| **レビュー** | Codex CLI | 誤字脱字、構造チェック |
| **前処理** | Python (pdf_tools.py) | PDF回転、画像化、分割 |

### 最重要ルール
**オーケストレーターは画像を直接読まない。必ずsubagentに委譲する。**
これはコンテキスト保護のため。（スポットチェック時のみ例外）

---

## 利用可能なSkills

| コマンド | 用途 |
|---------|------|
| `/ocr-toc {書籍名}` | 目次の書き起こし |
| `/ocr-chapter {書籍名} {章ID}` | 章の書き起こし（例: 核心 Part1_01） |
| `/ocr-review {ファイルパス}` | Codexレビュー |
| `/ocr-status` | 進捗確認 |

---

## 命名規則

### 画像ファイル
```
page_{PDFページ番号:03d}.png
例: page_001.png, page_002.png, page_010.png
```

### 出力Markdownファイル
```
{Part番号}_{章番号}_{章名}.md
例: Part1_01_冠詞.md, Part2_07_文型.md
```

### 書籍名の表記
- ディレクトリ名・ファイル名では日本語をそのまま使用
- 別冊は `{書籍名}_別冊` として独立管理
- 例: `核心`, `成川`, `成川_別冊`, `スクランブル`

---

## ワークフロー

### Phase 1: 前処理
```bash
# PDF情報確認
.venv/bin/python scripts/pdf_tools.py info --all

# ページマッピング確認
.venv/bin/python scripts/pdf_tools.py page-map 核心

# 画像変換
.venv/bin/python scripts/pdf_tools.py to-images pdf/rotated/核心_前半.pdf pdf/images/核心 --dpi 150
```

### Phase 2: 目次書き起こし
1. ユーザーに目次ページ範囲を確認
2. `/ocr-toc {書籍名}` で実行
3. subagentが画像を読み取り
4. Codexでレビュー
5. `pdf/output/{書籍名}/00_目次.md` に保存
6. `python scripts/extract_chapters.py` で章情報を抽出
7. `python scripts/migrate_status.py` でstatus.jsonを更新

### Phase 3: 章書き起こし
1. `status.json` から章のページ範囲を取得
2. `/ocr-chapter {書籍名} {章ID}` で実行
3. subagentが画像を読み取り
4. Codexでレビュー
5. スポットチェック（該当する場合のみ）
6. `pdf/output/{書籍名}/{Part番号}_{章番号}_{章名}.md` に保存
7. `progress/status.json` を更新

---

## スポットチェックルール

以下のいずれかに該当する章は、オーケストレーターがサンプルページで原本照合を行う：

1. **各書籍の最初の章** - 表記スタイルの確認
2. **5章ごと（5, 10, 15, ...）** - 継続的な品質確認
3. **前半/後半の境界をまたぐ章** - ページマッピングの検証
4. **Codexが警告を出した章** - 問題の深堀り

`status.json` の `spot_check_required: true` で判定。

---

## エラーリカバリ

| エラー | 対応 | リトライ上限 |
|--------|------|-------------|
| 画像が読めない | DPIを上げて再変換（150→200→300） | 3回 |
| subagentがタイムアウト | ページ数を半分に減らして再試行 | 2回 |
| Codexがエラーを検出 | 修正して再レビュー | 2回 |
| 原本と大きく異なる | ユーザーに確認 | - |

リトライ上限超過時は `progress/logs/errors/` にログを記録。

### コンテキストがCompactされた場合
1. このCLAUDE.mdを最初に読む
2. `progress/status.json` で進捗を確認
3. `.rules/` でワークフロールールを確認
4. 直近の作業を継続

---

## 進捗管理（status.json v2.0）

```bash
# 進捗ファイルを確認
cat progress/status.json | jq '.books | keys'

# 章情報を確認
cat progress/status.json | jq '.books.核心.chapters[:3]'

# または skill を使用
/ocr-status
```

### status.json の主要フィールド
- `version`: "2.0"
- `config`: 命名規則、DPI、リトライ上限
- `books.{書籍名}.page_mapping`: 前半/後半のページ対応
- `books.{書籍名}.chapters`: 各章の情報（ID、ページ範囲、ステータス、スポットチェック要否）
- `books.{書籍名}.supplement`: 別冊情報（成川、肘井）

---

## 関連ファイル

- `.rules/ocr-workflow.md` - ワークフローの詳細
- `.rules/notation-rules.md` - 表記ルール（随時更新）
- `progress/status.json` - 進捗管理
- `.claude/commands/` - 各skillの詳細

---

## 設計思想

1. **コンテキスト保護**: オーケストレーターは管理に徹し、実作業はsubagentに委譲
2. **状態の永続化**: 全ての状態はファイルに保存、中断・再開が可能
3. **複数LLMの協調**: Claude（書き起こし）+ Codex（レビュー）で品質担保
4. **漸進的改善**: 表記ルールは最小限から始め、必要に応じて追加
5. **一貫性**: skillsとhooksで同じ手順を毎回実行

---

## 開発環境

```bash
# venv有効化
source .venv/bin/activate

# テスト実行
.venv/bin/pytest tests/ -v

# PDFツールのヘルプ
.venv/bin/python scripts/pdf_tools.py --help
```
