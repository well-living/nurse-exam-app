# 看護師国家試験学習アプリ 仕様書

## 概要

看護師国家試験の過去問題を学習できるWebアプリケーション。問題演習と学習履歴管理、LLMチャット機能を提供する。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Frontend | Next.js (TypeScript) |
| Backend | FastAPI (uv, pydantic v2, pydanticAI) |
| Database | PostgreSQL (本番: Cloud SQL) |
| Chat | SSE streaming endpoint |
| Deploy | Google Cloud Run |
| Access Control | HTTP(S) Load Balancer + IAP |

## MVP機能

### 1. 問題管理

- JSONファイルから問題データを読み込み
- 問題一覧の表示
- 問題の出題・解答入力・採点・解説表示

### 2. 学習履歴

- 正答率の記録・表示
- 間違えた問題の記録・フィルタ表示
- ブックマーク機能

### 3. LLMチャット

- 学習に関する質問ができるチャット欄
- SSEによるストリーミング応答
- 免責文の表示（学習目的であり医療アドバイスではない旨）

### 4. アクセス制御

- GCP IAP による認証
- 特定のメールアドレス/Google Groupのみアクセス許可

## 非ゴール（MVP対象外）

- RAG（検索拡張生成）
- ベクトルDB
- 自動解説生成
- レコメンド機能

## データモデル

### Question（問題）

```json
{
  "id": "string",
  "year": "number",
  "number": "number",
  "category": "string",
  "question_text": "string",
  "choices": ["string"],
  "correct_answer": "number",
  "explanation": "string"
}
```

### UserHistory（学習履歴）

```
- user_id: string
- question_id: string
- is_correct: boolean
- answered_at: timestamp
```

### Bookmark（ブックマーク）

```
- user_id: string
- question_id: string
- created_at: timestamp
```

## API エンドポイント

### 問題

| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/questions` | 問題一覧取得 |
| GET | `/api/questions/{id}` | 問題詳細取得 |

### 学習履歴

| Method | Path | 説明 |
|--------|------|------|
| POST | `/api/answers` | 解答を送信・採点 |
| GET | `/api/history` | 学習履歴取得 |
| GET | `/api/stats` | 統計情報（正答率等）取得 |

### ブックマーク

| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/bookmarks` | ブックマーク一覧取得 |
| POST | `/api/bookmarks/{question_id}` | ブックマーク追加 |
| DELETE | `/api/bookmarks/{question_id}` | ブックマーク削除 |

### チャット

| Method | Path | 説明 |
|--------|------|------|
| POST | `/api/chat` | チャットメッセージ送信（SSE応答） |

## 画面構成

1. **問題一覧ページ** (`/`)
   - 問題リスト表示
   - フィルタ（年度、カテゴリ、未回答/間違い/ブックマーク）

2. **問題演習ページ** (`/questions/{id}`)
   - 問題文・選択肢表示
   - 解答選択・送信
   - 正誤表示・解説表示
   - ブックマークボタン

3. **学習履歴ページ** (`/history`)
   - 正答率表示
   - 履歴一覧

4. **チャットパネル**
   - 全ページでアクセス可能なサイドパネル
   - 免責文表示

## Acceptance Criteria

- [ ] JSONから問題を読み込める
- [ ] 出題→回答→採点→履歴保存が動作する
- [ ] チャットUIが表示される
- [ ] IAP認証が機能する

## 免責文（チャット機能）

> このチャットは学習支援を目的としており、医療上のアドバイスではありません。
> 実際の医療判断は必ず医療専門家にご相談ください。
