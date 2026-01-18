# タスク一覧

## 凡例

- **見積もり**: 0.5d = 半日, 1d = 1日
- **優先度**: P0(必須) > P1(重要) > P2(あれば良い)
- **依存**: 先に完了が必要なタスク

---

## インフラ (Infrastructure)

### INFRA-001: ローカル開発環境のDocker Compose構築

**見積もり**: 0.5d
**優先度**: P0
**依存**: なし

#### 概要
PostgreSQLをローカルで動かすためのDocker Compose設定を作成する。

#### Acceptance Criteria
- [ ] `docker-compose.yml` が作成されている
- [ ] `docker compose up -d` でPostgreSQLが起動する
- [ ] PostgreSQL 15以上が使用されている
- [ ] データが永続化される（named volume）
- [ ] `nurse_exam` データベースが自動作成される
- [ ] 接続情報がREADMEまたは.env.exampleに記載されている

#### 技術詳細
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: nurse_exam
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

---

### INFRA-002: Cloud SQL インスタンス構築（Terraform）

**見積もり**: 1d
**優先度**: P1
**依存**: なし

#### 概要
本番環境用のCloud SQL PostgreSQLインスタンスをTerraformで構築する。

#### Acceptance Criteria
- [ ] `infra/terraform/` ディレクトリが作成されている
- [ ] Cloud SQL PostgreSQL 15インスタンスが作成される
- [ ] プライベートIP接続が設定されている
- [ ] 自動バックアップが有効化されている
- [ ] `terraform plan` が成功する
- [ ] 接続用のサービスアカウントが作成される

#### 技術詳細
- インスタンスタイプ: db-f1-micro（開発用）
- リージョン: asia-northeast1
- ストレージ: 10GB SSD

---

### INFRA-003: Cloud Run サービス構築（API）

**見積もり**: 1d
**優先度**: P0
**依存**: INFRA-002, API-001

#### 概要
FastAPI バックエンドをCloud Runにデプロイする設定を作成する。

#### Acceptance Criteria
- [ ] `apps/api/Dockerfile` が作成されている
- [ ] ローカルでDockerビルドが成功する
- [ ] Cloud Runサービス定義（Terraform or YAML）が作成されている
- [ ] Cloud SQL への接続が設定されている
- [ ] 環境変数（ANTHROPIC_API_KEY等）がSecret Managerから取得される
- [ ] ヘルスチェックエンドポイント `/health` が応答する
- [ ] Cloud Buildトリガーまたはデプロイスクリプトが用意されている

---

### INFRA-004: Cloud Run サービス構築（Web）

**見積もり**: 1d
**優先度**: P0
**依存**: INFRA-003, WEB-001

#### 概要
Next.js フロントエンドをCloud Runにデプロイする設定を作成する。

#### Acceptance Criteria
- [ ] `apps/web/Dockerfile` が作成されている
- [ ] Next.js が standalone モードでビルドされる
- [ ] ローカルでDockerビルドが成功する
- [ ] Cloud Runサービス定義が作成されている
- [ ] API URLが環境変数で設定可能
- [ ] Cloud Buildトリガーまたはデプロイスクリプトが用意されている

---

### INFRA-005: Load Balancer + IAP 設定

**見積もり**: 1.5d
**優先度**: P0
**依存**: INFRA-003, INFRA-004

#### 概要
HTTPS Load BalancerとIAPを設定し、認証済みユーザーのみアクセス可能にする。

#### Acceptance Criteria
- [ ] HTTPS Load Balancerが作成されている
- [ ] SSL証明書（Google managed）が設定されている
- [ ] IAPが有効化されている
- [ ] 許可するメールアドレス/Google Groupが設定可能
- [ ] 未認証アクセスが403エラーになる
- [ ] IAPヘッダー（`X-Goog-Authenticated-User-Email`）がバックエンドに渡される
- [ ] カスタムドメインまたはデフォルトドメインでアクセス可能

---

## API (Backend)

### API-001: FastAPI プロジェクト初期構築

**見積もり**: 0.5d
**優先度**: P0
**依存**: INFRA-001

#### 概要
FastAPIプロジェクトの雛形を作成し、基本的な設定を行う。

#### Acceptance Criteria
- [ ] `apps/api/` ディレクトリが作成されている
- [ ] `pyproject.toml` でuv管理されている
- [ ] `uv sync` で依存関係がインストールされる
- [ ] `uv run fastapi dev src/main.py` でサーバーが起動する
- [ ] `/health` エンドポイントが200を返す
- [ ] `/docs` でSwagger UIが表示される
- [ ] CORS設定が環境変数で制御可能
- [ ] `.env.example` が作成されている

---

### API-002: DB接続・マイグレーション基盤

**見積もり**: 1d
**優先度**: P0
**依存**: API-001, INFRA-001

#### 概要
PostgreSQL接続とマイグレーション機能を実装する。

#### Acceptance Criteria
- [ ] asyncpgまたはpsycopg3で非同期DB接続ができる
- [ ] 接続プール設定がされている
- [ ] マイグレーションスクリプト（または Alembic）が動作する
- [ ] `users`, `questions`, `attempts`, `bookmarks`, `chat_messages` テーブルが作成される
- [ ] インデックスがplan.mdの定義通り作成される
- [ ] マイグレーションのup/downが可能

---

### API-003: IAPユーザー認可ミドルウェア

**見積もり**: 1d
**優先度**: P0
**依存**: API-002

#### 概要
IAPヘッダーからユーザー情報を取得し、認可を行うミドルウェアを実装する。

#### Acceptance Criteria
- [ ] `X-Goog-Authenticated-User-Email` ヘッダーからメールアドレスを取得できる
- [ ] ユーザーが存在しない場合、自動で `users` テーブルに作成される
- [ ] リクエストコンテキストに `current_user` が設定される
- [ ] ローカル開発時はヘッダー偽装または環境変数でユーザー指定可能
- [ ] 認可エラー時は401/403を返す
- [ ] ユニットテストが存在する

---

### API-004: 問題取得API

**見積もり**: 0.5d
**優先度**: P0
**依存**: API-002

#### 概要
問題一覧・詳細取得のAPIを実装する。

#### Acceptance Criteria
- [ ] `GET /api/questions` で問題一覧が取得できる
- [ ] `year`, `category` でフィルタ可能
- [ ] ページネーション（limit/offset）が動作する
- [ ] `GET /api/questions/{id}` で問題詳細が取得できる
- [ ] 存在しないIDは404を返す
- [ ] レスポンスがPydanticモデルで型定義されている

---

### API-005: 問題データインポートスクリプト

**見積もり**: 0.5d
**優先度**: P0
**依存**: API-002

#### 概要
JSONファイルから問題データをDBにインポートするスクリプトを作成する。

#### Acceptance Criteria
- [ ] `uv run python -m src.scripts.import_questions <file>` で実行できる
- [ ] `data/questions.json` のサンプルデータが用意されている
- [ ] 重複インポートが防止される（upsert）
- [ ] インポート件数がログ出力される
- [ ] 不正なJSONはエラーメッセージを表示して終了する

---

### API-006: 解答保存・採点API

**見積もり**: 1d
**優先度**: P0
**依存**: API-003, API-004

#### 概要
ユーザーの解答を保存し、正誤判定を行うAPIを実装する。

#### Acceptance Criteria
- [ ] `POST /api/attempts` で解答を送信できる
- [ ] リクエスト: `{question_id, selected_answer}`
- [ ] レスポンス: `{is_correct, correct_answer, explanation}`
- [ ] `attempts` テーブルに履歴が保存される
- [ ] 同じ問題に複数回解答可能（履歴は全て保存）
- [ ] `GET /api/attempts` でユーザーの解答履歴が取得できる
- [ ] 存在しない問題IDは400を返す

---

### API-007: 学習統計API

**見積もり**: 0.5d
**優先度**: P1
**依存**: API-006

#### 概要
ユーザーの学習統計を取得するAPIを実装する。

#### Acceptance Criteria
- [ ] `GET /api/stats` で統計情報が取得できる
- [ ] レスポンス: `{total_attempts, correct_count, accuracy_rate, by_category: [{category, total, correct, rate}]}`
- [ ] `GET /api/stats/weak` で正答率の低い問題一覧が取得できる
- [ ] カテゴリ別の正答率が計算される
- [ ] 解答がない場合は空のレスポンスを返す

---

### API-008: ブックマークAPI

**見積もり**: 0.5d
**優先度**: P1
**依存**: API-003, API-004

#### 概要
問題のブックマーク機能を実装する。

#### Acceptance Criteria
- [ ] `GET /api/bookmarks` でブックマーク一覧が取得できる
- [ ] `POST /api/bookmarks` でブックマークを追加できる
- [ ] `DELETE /api/bookmarks/{question_id}` でブックマークを削除できる
- [ ] 重複追加は409を返す
- [ ] 問題一覧APIで `is_bookmarked` フラグが取得できる

---

### API-009: チャットSSE API

**見積もり**: 1.5d
**優先度**: P0
**依存**: API-003

#### 概要
LLMとのチャットをSSEでストリーミング配信するAPIを実装する。

#### Acceptance Criteria
- [ ] `POST /api/chat/stream` でSSEストリームが開始される
- [ ] リクエスト: `{message, history?: [{role, content}]}`
- [ ] `Content-Type: text/event-stream` で応答する
- [ ] pydanticAI を使用してAnthropicAPIを呼び出す
- [ ] トークン単位でストリーミングされる
- [ ] チャット履歴が `chat_messages` テーブルに保存される
- [ ] システムプロンプトに免責文・役割が設定されている
- [ ] APIキーエラー時は適切なエラーメッセージを返す
- [ ] `GET /api/chat/history` で過去の会話が取得できる

---

## Web (Frontend)

### WEB-001: Next.js プロジェクト初期構築

**見積もり**: 0.5d
**優先度**: P0
**依存**: なし

#### 概要
Next.jsプロジェクトの雛形を作成し、基本的な設定を行う。

#### Acceptance Criteria
- [ ] `apps/web/` ディレクトリが作成されている
- [ ] Next.js 14+ (App Router) が使用されている
- [ ] TypeScript が設定されている
- [ ] `npm run dev` でサーバーが起動する
- [ ] ESLint/Prettier が設定されている
- [ ] `.env.example` が作成されている
- [ ] API_URL が環境変数で設定可能

---

### WEB-002: 共通レイアウト・UIコンポーネント

**見積もり**: 1d
**優先度**: P0
**依存**: WEB-001

#### 概要
アプリ全体の共通レイアウトと基本UIコンポーネントを作成する。

#### Acceptance Criteria
- [ ] ヘッダー（タイトル、ナビゲーション）が表示される
- [ ] レスポンシブデザイン（モバイル対応）
- [ ] ボタン、カード、ローディングスピナー等の基本コンポーネントが作成されている
- [ ] CSS Modules または Tailwind CSS が設定されている
- [ ] ダークモード対応（任意）

---

### WEB-003: 問題一覧ページ

**見積もり**: 1d
**優先度**: P0
**依存**: WEB-002, API-004

#### 概要
問題一覧を表示し、フィルタ・検索ができるページを実装する。

#### Acceptance Criteria
- [ ] `/` で問題一覧が表示される
- [ ] 年度でフィルタできる
- [ ] カテゴリでフィルタできる
- [ ] 「未解答」「間違えた問題」「ブックマーク」でフィルタできる
- [ ] ページネーションまたは無限スクロールが動作する
- [ ] 問題カードに年度、番号、カテゴリ、正答状況が表示される
- [ ] 問題カードクリックで詳細ページに遷移する
- [ ] ローディング状態が表示される
- [ ] APIエラー時にエラーメッセージが表示される

---

### WEB-004: 問題詳細・解答ページ

**見積もり**: 1.5d
**優先度**: P0
**依存**: WEB-002, API-006

#### 概要
問題を解答し、結果・解説を表示するページを実装する。

#### Acceptance Criteria
- [ ] `/questions/{id}` で問題詳細が表示される
- [ ] 問題文が表示される
- [ ] 選択肢がラジオボタンで表示される
- [ ] 「解答する」ボタンで解答を送信できる
- [ ] 正誤結果が表示される（○/×、正解の選択肢ハイライト）
- [ ] 解説が表示される
- [ ] ブックマークボタンが動作する
- [ ] 「次の問題へ」ボタンで次の問題に遷移できる
- [ ] 解答前に選択肢を選ばないと送信できない（バリデーション）

---

### WEB-005: 学習履歴ページ

**見積もり**: 1d
**優先度**: P1
**依存**: WEB-002, API-007

#### 概要
学習履歴と統計情報を表示するページを実装する。

#### Acceptance Criteria
- [ ] `/history` で履歴ページが表示される
- [ ] 総解答数、正答数、正答率が表示される
- [ ] カテゴリ別の正答率がグラフまたはテーブルで表示される
- [ ] 解答履歴一覧が時系列で表示される
- [ ] 履歴から問題詳細ページに遷移できる
- [ ] 苦手問題（正答率の低い問題）が表示される

---

### WEB-006: チャットパネル

**見積もり**: 1.5d
**優先度**: P0
**依存**: WEB-002, API-009

#### 概要
LLMに質問できるチャットUIを実装する。

#### Acceptance Criteria
- [ ] 全ページからアクセス可能なサイドパネルまたはモーダル
- [ ] チャット開閉ボタンが表示される
- [ ] 免責文が表示される（「このチャットは学習支援目的であり...」）
- [ ] メッセージ入力欄がある
- [ ] 送信ボタンでメッセージを送信できる
- [ ] SSEストリーミングで応答がリアルタイム表示される
- [ ] ユーザー/アシスタントのメッセージが区別できる
- [ ] 過去の会話履歴が表示される
- [ ] ローディング中はタイピングインジケータが表示される
- [ ] エラー時にエラーメッセージが表示される

---

## 統合・テスト

### TEST-001: E2Eテスト基盤構築

**見積もり**: 1d
**優先度**: P2
**依存**: WEB-004, API-006

#### 概要
PlaywrightによるE2Eテスト環境を構築する。

#### Acceptance Criteria
- [ ] Playwright がインストールされている
- [ ] `npm run test:e2e` でテストが実行できる
- [ ] 問題一覧→問題詳細→解答→結果表示の一連の流れがテストされる
- [ ] CI（GitHub Actions）でテストが実行される
- [ ] テストレポートが出力される

---

### TEST-002: API統合テスト

**見積もり**: 0.5d
**優先度**: P1
**依存**: API-006

#### 概要
FastAPIの統合テストを作成する。

#### Acceptance Criteria
- [ ] pytest + httpx でテストが書かれている
- [ ] テスト用DBが使用される（本番DBとは分離）
- [ ] 主要APIエンドポイントのテストが存在する
- [ ] `uv run pytest` でテストが実行できる
- [ ] CIでテストが実行される

---

## タスク一覧サマリー

| ID | タスク | 見積もり | 優先度 | 依存 |
|----|--------|----------|--------|------|
| INFRA-001 | Docker Compose構築 | 0.5d | P0 | - |
| INFRA-002 | Cloud SQL構築 | 1d | P1 | - |
| INFRA-003 | Cloud Run (API) | 1d | P0 | INFRA-002, API-001 |
| INFRA-004 | Cloud Run (Web) | 1d | P0 | INFRA-003, WEB-001 |
| INFRA-005 | LB + IAP設定 | 1.5d | P0 | INFRA-003, INFRA-004 |
| API-001 | FastAPI初期構築 | 0.5d | P0 | INFRA-001 |
| API-002 | DB接続・マイグレーション | 1d | P0 | API-001 |
| API-003 | IAP認可ミドルウェア | 1d | P0 | API-002 |
| API-004 | 問題取得API | 0.5d | P0 | API-002 |
| API-005 | 問題インポートスクリプト | 0.5d | P0 | API-002 |
| API-006 | 解答保存・採点API | 1d | P0 | API-003, API-004 |
| API-007 | 学習統計API | 0.5d | P1 | API-006 |
| API-008 | ブックマークAPI | 0.5d | P1 | API-003, API-004 |
| API-009 | チャットSSE API | 1.5d | P0 | API-003 |
| WEB-001 | Next.js初期構築 | 0.5d | P0 | - |
| WEB-002 | 共通レイアウト・UI | 1d | P0 | WEB-001 |
| WEB-003 | 問題一覧ページ | 1d | P0 | WEB-002, API-004 |
| WEB-004 | 問題詳細・解答ページ | 1.5d | P0 | WEB-002, API-006 |
| WEB-005 | 学習履歴ページ | 1d | P1 | WEB-002, API-007 |
| WEB-006 | チャットパネル | 1.5d | P0 | WEB-002, API-009 |
| TEST-001 | E2Eテスト基盤 | 1d | P2 | WEB-004, API-006 |
| TEST-002 | API統合テスト | 0.5d | P1 | API-006 |

**合計見積もり**: 約18日（P0のみ: 約13日）
