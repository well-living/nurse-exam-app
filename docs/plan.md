# 実装計画書

## サービス構成図

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Platform                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────────┐                                              │
│   │  Cloud Load      │                                              │
│   │  Balancer        │◄─── HTTPS                                    │
│   │  + IAP           │     (認証済みユーザーのみ)                      │
│   └────────┬─────────┘                                              │
│            │                                                         │
│            ▼                                                         │
│   ┌──────────────────────────────────────────┐                      │
│   │            Cloud Run                      │                      │
│   │  ┌─────────────┐    ┌─────────────┐      │                      │
│   │  │  apps/web   │    │  apps/api   │      │                      │
│   │  │  (Next.js)  │───►│  (FastAPI)  │      │                      │
│   │  │  :3000      │    │  :8000      │      │                      │
│   │  └─────────────┘    └──────┬──────┘      │                      │
│   └─────────────────────────────┼────────────┘                      │
│                                 │                                    │
│                                 ▼                                    │
│                        ┌───────────────┐      ┌───────────────┐     │
│                        │   Cloud SQL   │      │   LLM API     │     │
│                        │  (PostgreSQL) │      │  (Anthropic)  │     │
│                        └───────────────┘      └───────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### ローカル開発構成

```
┌─────────────────────────────────────────────────────────┐
│                     localhost                            │
│                                                          │
│   ┌─────────────┐         ┌─────────────┐              │
│   │  apps/web   │ ──────► │  apps/api   │              │
│   │  :3000      │         │  :8000      │              │
│   └─────────────┘         └──────┬──────┘              │
│                                  │                      │
│                                  ▼                      │
│                          ┌─────────────┐               │
│                          │   Docker    │               │
│                          │  PostgreSQL │               │
│                          │  :5432      │               │
│                          └─────────────┘               │
└─────────────────────────────────────────────────────────┘
```

## ディレクトリ構成

```
nurse-exam-app/
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/           # App Router
│   │   │   ├── components/    # UIコンポーネント
│   │   │   ├── lib/           # ユーティリティ
│   │   │   └── types/         # 型定義
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── api/                    # FastAPI backend
│       ├── src/
│       │   ├── main.py        # エントリーポイント
│       │   ├── routers/       # APIルーター
│       │   ├── models/        # Pydanticモデル
│       │   ├── db/            # DB接続・クエリ
│       │   └── services/      # ビジネスロジック
│       ├── pyproject.toml
│       └── uv.lock
│
├── data/
│   └── questions.json          # 問題データ
│
├── docker-compose.yml          # ローカルDB
├── docs/
│   ├── spec.md
│   └── plan.md
└── CLAUDE.md
```

## API一覧

### 問題取得

| Method | Endpoint | 説明 | Request | Response |
|--------|----------|------|---------|----------|
| GET | `/api/questions` | 問題一覧 | `?year=&category=&status=` | `Question[]` |
| GET | `/api/questions/{id}` | 問題詳細 | - | `Question` |

### 解答・履歴 (attempts)

| Method | Endpoint | 説明 | Request | Response |
|--------|----------|------|---------|----------|
| POST | `/api/attempts` | 解答を保存 | `{question_id, selected_answer}` | `{is_correct, correct_answer, explanation}` |
| GET | `/api/attempts` | 履歴一覧 | `?limit=&offset=` | `Attempt[]` |

### 統計 (stats)

| Method | Endpoint | 説明 | Request | Response |
|--------|----------|------|---------|----------|
| GET | `/api/stats` | 学習統計 | - | `{total, correct, accuracy, by_category}` |
| GET | `/api/stats/weak` | 苦手問題 | `?limit=` | `Question[]` |

### ブックマーク

| Method | Endpoint | 説明 | Request | Response |
|--------|----------|------|---------|----------|
| GET | `/api/bookmarks` | 一覧取得 | - | `Bookmark[]` |
| POST | `/api/bookmarks` | 追加 | `{question_id}` | `Bookmark` |
| DELETE | `/api/bookmarks/{question_id}` | 削除 | - | `204` |

### チャット

| Method | Endpoint | 説明 | Request | Response |
|--------|----------|------|---------|----------|
| POST | `/api/chat/stream` | SSEチャット | `{message, history?}` | `text/event-stream` |
| GET | `/api/chat/history` | 履歴取得 | `?limit=` | `ChatMessage[]` |

## DBスキーマ

### users

| Column | Type | Constraint | 説明 |
|--------|------|------------|------|
| id | UUID | PK | ユーザーID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | メールアドレス（IAP連携） |
| name | VARCHAR(255) | | 表示名 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新日時 |

### questions

| Column | Type | Constraint | 説明 |
|--------|------|------------|------|
| id | UUID | PK | 問題ID |
| year | INTEGER | NOT NULL | 出題年度 |
| number | INTEGER | NOT NULL | 問題番号 |
| category | VARCHAR(100) | NOT NULL | カテゴリ |
| question_text | TEXT | NOT NULL | 問題文 |
| choices | JSONB | NOT NULL | 選択肢配列 |
| correct_answer | INTEGER | NOT NULL | 正解番号（0-indexed） |
| explanation | TEXT | | 解説 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 作成日時 |

```sql
CREATE UNIQUE INDEX idx_questions_year_number ON questions(year, number);
CREATE INDEX idx_questions_category ON questions(category);
```

### attempts

| Column | Type | Constraint | 説明 |
|--------|------|------------|------|
| id | UUID | PK | 解答ID |
| user_id | UUID | FK → users.id, NOT NULL | ユーザーID |
| question_id | UUID | FK → questions.id, NOT NULL | 問題ID |
| selected_answer | INTEGER | NOT NULL | 選択した回答 |
| is_correct | BOOLEAN | NOT NULL | 正誤 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 解答日時 |

```sql
CREATE INDEX idx_attempts_user_id ON attempts(user_id);
CREATE INDEX idx_attempts_user_question ON attempts(user_id, question_id);
```

### bookmarks

| Column | Type | Constraint | 説明 |
|--------|------|------------|------|
| id | UUID | PK | ブックマークID |
| user_id | UUID | FK → users.id, NOT NULL | ユーザーID |
| question_id | UUID | FK → questions.id, NOT NULL | 問題ID |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 作成日時 |

```sql
CREATE UNIQUE INDEX idx_bookmarks_user_question ON bookmarks(user_id, question_id);
```

### chat_messages

| Column | Type | Constraint | 説明 |
|--------|------|------------|------|
| id | UUID | PK | メッセージID |
| user_id | UUID | FK → users.id, NOT NULL | ユーザーID |
| role | VARCHAR(20) | NOT NULL | 'user' or 'assistant' |
| content | TEXT | NOT NULL | メッセージ内容 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 送信日時 |

```sql
CREATE INDEX idx_chat_messages_user_id ON chat_messages(user_id, created_at DESC);
```

## ER図

```
┌──────────────┐       ┌──────────────┐
│    users     │       │  questions   │
├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │
│ email        │       │ year         │
│ name         │       │ number       │
│ created_at   │       │ category     │
│ updated_at   │       │ question_text│
└──────┬───────┘       │ choices      │
       │               │ correct_answer│
       │               │ explanation  │
       │               └──────┬───────┘
       │                      │
       ▼                      ▼
┌──────────────┐       ┌──────────────┐
│   attempts   │       │  bookmarks   │
├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │
│ user_id (FK) │───┐   │ user_id (FK) │
│ question_id  │───┼──►│ question_id  │
│ selected_ans │   │   │ created_at   │
│ is_correct   │   │   └──────────────┘
│ created_at   │   │
└──────────────┘   │   ┌──────────────┐
                   │   │chat_messages │
                   │   ├──────────────┤
                   │   │ id (PK)      │
                   └──►│ user_id (FK) │
                       │ role         │
                       │ content      │
                       │ created_at   │
                       └──────────────┘
```

## ローカル開発手順

### 1. 前提条件

- Node.js 20+
- Python 3.12+
- uv (Python package manager)
- Docker / Docker Compose

### 2. リポジトリのセットアップ

```bash
git clone <repository-url>
cd nurse-exam-app
```

### 3. データベース起動 (Docker)

```bash
# PostgreSQL起動
docker compose up -d

# 接続確認
docker compose exec db psql -U postgres -d nurse_exam
```

### 4. Backend (FastAPI) セットアップ

```bash
cd apps/api

# 依存関係インストール
uv sync

# 環境変数設定
cp .env.example .env
# .envを編集: DATABASE_URL, ANTHROPIC_API_KEY等

# DBマイグレーション
uv run python -m src.db.migrate

# 開発サーバー起動
uv run fastapi dev src/main.py --port 8000
```

### 5. Frontend (Next.js) セットアップ

```bash
cd apps/web

# 依存関係インストール
npm install

# 環境変数設定
cp .env.example .env.local
# .env.localを編集: NEXT_PUBLIC_API_URL等

# 開発サーバー起動
npm run dev
```

### 6. 動作確認

| サービス | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

### 7. 問題データの投入

```bash
# JSONから問題をインポート
cd apps/api
uv run python -m src.scripts.import_questions ../data/questions.json
```

## 環境変数

### apps/api/.env

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nurse_exam
ANTHROPIC_API_KEY=sk-ant-xxx
ALLOWED_ORIGINS=http://localhost:3000
```

### apps/web/.env.local

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 開発コマンド一覧

```bash
# 全サービス起動
docker compose up -d && cd apps/api && uv run fastapi dev src/main.py &
cd apps/web && npm run dev

# テスト実行
cd apps/api && uv run pytest
cd apps/web && npm test

# Lint/Format
cd apps/api && uv run ruff check . && uv run ruff format .
cd apps/web && npm run lint
```
