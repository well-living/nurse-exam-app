# nurse-exam-app

看護師国家試験の過去問題集による学習Webアプリ（個人開発）。
- フロント: TypeScript / Next.js (App Router)
- バック: Python / uv / FastAPI / pydantic v2（必要に応じて）
- LLMチャット: SSE（ストリーミング）
- デプロイ: Google Cloud Run
- アクセス制限: HTTP(S) Load Balancer + IAP（特定メール/グループのみ）

---

## 1. このREADMEのゴール

このREADMEどおりに進めると、次ができます。

- Spec Kit を導入し、仕様駆動（spec/plan/tasks）で進める
- Claude Code を使って docs と雛形実装を効率化する
- Next.js（web）と FastAPI（api）を作ってローカル実行
- Docker の Postgres をローカルで起動（学習履歴・チャットログの永続化）
- Cloud Run に web/api をデプロイ
- IAP で特定メールのみアクセス許可

---

## 2. 必要なもの（Windows / PowerShell）

### 必須
- Git
- Node.js（LTS推奨）
- Python 3.11+ 推奨
- uv
- Docker Desktop
- Google Cloud SDK（gcloud）
- Claude Code（`claude` コマンドが使えること）

### あると便利
- VSCode
- GitHub CLI（gh）

---

## 3. リポジトリ取得後の開始地点

GitHubで新規作成済みのリポジトリを clone できている前提です。

```powershell
cd nurse-exam-app
git status
```

以降、「意味のある成果が増えた時だけ commit」します。
（空コミットや内容の薄いコミットはしません）

---

## 4. Spec Kit 初期化（重要：script type は sh を選ぶ）

Spec Kit を導入して、仕様 → 計画 → タスク → 実装の流れを固定します。

```powershell
uvx --from git+https://github.com/github/spec-kit.git specify init --here --ai claude
```

### 対話での選択
実行中に出る **choose script type** は **`sh`** を選んでください（ps ではなく）。

（任意）環境チェック
```powershell
uvx --from git+https://github.com/github/spec-kit.git specify check
```

---

## 5. Claude Code の固定事項（迷走防止）

Claude Code が勝手な技術選定をしないように `CLAUDE.md` を作ります。

```powershell
ni CLAUDE.md -Force
```

`CLAUDE.md` の内容（貼り付け）
```txt
Deploy: Google Cloud Run
Access control: HTTP(S) Load Balancer + IAP, allow only specific emails or Google Group
Frontend: Next.js (TypeScript, App Router)
Backend: FastAPI (uv, pydantic v2, pydanticAI)
Chat: SSE streaming endpoint
Database: PostgreSQL (Cloud SQL in production)
Do not add new frameworks or services without updating docs/spec.md
```

ここまでをコミット
```powershell
git add .
git commit -m "chore: initialize spec-kit and add CLAUDE constraints"
git push
```

---

## 6. Claude Code ログインで詰まったとき（注意書き）

Claude Code のログイン時に、ブラウザで
「無効なOAuth要求です / client_idパラメータが見つかりません」
が出ることがあります。

対処:
- **自動で開いたブラウザは使わず**
- **ターミナルに表示されたログインURLを手でコピーしてブラウザに貼り付けて開く**

これで解決することが多いです。

---

## 7. docs（spec / plan / tasks）を Claude Code で作成

Claude Code を起動します（リポジトリ直下）。

```powershell
claude
```

以下を **順番にそのまま貼り付け**て実行してください。

### 7.1 docs/spec.md
```txt
docs/spec.md を作ってください。

MVP:
1. 看護師国家試験の過去問題を学習できるWebアプリ
2. 問題一覧・出題・解答・正誤・解説表示
3. 学習履歴（正答率、間違い問題、ブックマーク）
4. LLMに質問できるチャット欄（学習目的の免責文を表示）
5. GCPのLoad Balancer + IAPで特定メール/グループのみアクセス許可

非ゴール:
- RAG
- ベクタDB
- 自動解説生成
- レコメンド

Acceptance Criteria:
- サンプル問題JSONから問題を読み込める
- 出題→回答→採点→履歴保存が動作する
- チャットUIが表示され、ストリーミングで返答が出る（最初はダミーでも可）
- IAP想定のユーザー識別（メール）をapiが扱える
```

### 7.2 docs/plan.md
```txt
docs/plan.md を作ってください。

構成:
- apps/web: Next.js (TypeScript, App Router)
- apps/api: FastAPI (uv + pydantic v2)
- DB: Postgres（ローカルはDocker、本番はCloud SQL）
- LLMチャット: POST /chat/stream (SSE)
- GCPデプロイ: Cloud Run + Load Balancer + IAP

含める内容:
- サービス構成（web/api/db/secret/iap）
- API一覧（attempt保存, stats取得, chat SSE）
- DB最小スキーマ（users/questions/attempts/bookmarks/chat_threads/chat_messages）
- ローカル開発手順（web/api/db）
- 本番のIAPヘッダでemailを取得する方針と注意点
```

### 7.3 docs/tasks.md
```txt
docs/tasks.md を作ってください。

条件:
- 0.5〜1.5日単位でタスクを分解
- 各タスクにAcceptance Criteria（完了条件）を必ず付ける
- GitHub Issueに貼れる形式で作る
- MVPを最短で動かす順番（web→api→db→deploy→iap）で並べる
```

docsができたらコミット
```powershell
git add docs
git commit -m "docs: add spec plan tasks"
git push
```

---

## 8. Next.js（apps/web）作成

### 8.1 create-next-app 実行
```powershell
mkdir apps -Force | Out-Null
cd apps
npx create-next-app@latest web --ts --eslint
cd ..
```

### 8.2 create-next-app の質問にどう答えるか（推奨）

出る質問と推奨回答：

- Would you like to use React Compiler? → **No**
- Would you like to use Tailwind CSS? → **Yes**
- Would you like to use `src/` directory? → **No**
- Would you like to use App Router? → **Yes**
- Would you like to use Turbopack for dev? → **Yes**
- Would you like to customize the import alias? → **No**（デフォルトのまま）

---

## 9. web：サンプル問題JSONで「解く」機能を最短で作る

### 9.1 サンプル問題データを置く
```powershell
mkdir apps\web\public\data -Force | Out-Null
ni apps\web\public\data\questions.sample.json -Force
```

`apps/web/public/data/questions.sample.json` の内容（貼り付け）
```json
[
  {
    "id": "sample-001",
    "question": "サンプル問題：看護の基本はどれ？",
    "options": ["A", "B", "C", "D"],
    "answerIndex": 0,
    "explanation": "サンプル解説"
  }
]
```

### 9.2 Claude Code で演習画面を生成
```powershell
cd apps\web
claude
```

Claudeへの指示
```txt
Next.jsの app/page.tsx に問題出題UIを実装してください。

要件:
- public/data/questions.sample.json をfetchして読み込む
- 1問ずつ表示して回答できる
- 回答→正誤→解説→次の問題
- 学習履歴（正答/誤答数、誤答ID一覧）をlocalStorageに保存
- ブックマーク（localStorageでOK）
- UIは最低限でOK（Tailwind使用）
- コンポーネント分割して拡張しやすくする
```

起動確認
```powershell
npm run dev
```

コミット
```powershell
cd ../..
git add apps/web
git commit -m "feat(web): add Next.js quiz MVP with sample data"
git push
```

---

## 10. FastAPI（apps/api）作成：SSEチャット + allowlist

### 10.1 api 作成
```powershell
mkdir apps\api -Force | Out-Null
cd apps\api
uv init
uv add fastapi uvicorn pydantic
```

### 10.2 Claude Code で api 実装
```powershell
claude
```

Claudeへの指示
```txt
FastAPIで以下を実装してください。

- GET /health
- ユーザー識別:
  - ローカル: X-Debug-Email を許可
  - 本番: IAPヘッダからemailを取得（plan.mdに記載するヘッダ名を使う）
- ALLOWLIST_EMAILS（カンマ区切り）にemailが含まれなければ 403
- POST /chat/stream をSSEで実装（まずはダミー応答を分割してストリーミング）
- ローカルCORSは http://localhost:3000 のみ許可
- pytestの最小テストを追加
```

起動確認
```powershell
$env:ALLOWLIST_EMAILS="you@example.com"
uv run uvicorn main:app --reload --port 8000
```

SSE動作確認（別PowerShellで）
```powershell
curl.exe -N -H "X-Debug-Email: you@example.com" -H "Content-Type: application/json" -d "{`"message`":`"hello`"}" http://localhost:8000/chat/stream
```

コミット
```powershell
cd ../..
git add apps/api
git commit -m "feat(api): add FastAPI SSE chat and allowlist auth skeleton"
git push
```

---

## 11. ローカルDB（Postgres）を docker compose で起動

### 11.1 docker-compose.yml を作成（ルート）
```powershell
cd nurse-exam-app
ni docker-compose.yml -Force
```

内容（貼り付け）
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

起動
```powershell
docker compose up -d
```

---

## 12. 🐳 Docker が起動しない場合の対処（Windows）

以下のエラーが出る場合があります。

```
unable to get image 'postgres:16'
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

これは **Docker Desktop が起動していない、または Linux コンテナモードで動作していない** ことが原因です。

### 対処手順
1. **Docker Desktop を起動**（スタートメニューから）
2. **Linux コンテナモードに切替**
   - Docker Desktop メニューに `Switch to Linux containers` が出ていたらクリック
3. **WSLを再起動（必要な場合）**
   ```powershell
   wsl --shutdown
   ```
   → Docker Desktop 再起動
4. **Dockerの動作確認**
   ```powershell
   docker info
   ```
5. **再度起動**
   ```powershell
   docker compose up -d
   ```

---

## 13. api にDB永続化（attempts / chatログ）を追加

Claude Code（apps/api で）
```powershell
cd apps\api
claude
```

Claudeへの指示
```txt
ローカルPostgres（docker compose）へ接続し、以下を実装してください。

- users(email)
- attempts(user_id, question_id, is_correct, created_at)
- chat_threads(user_id, created_at)
- chat_messages(thread_id, role, content, created_at)
- /attempts POST 保存
- /stats GET 集計（正答率、誤答ID一覧など）
- /chat/stream で受信/送信をDBに保存（threadが無ければ新規作成）
- マイグレーション手段（Alembic等）とローカル起動手順を docs/plan.md に追記
```

コミット
```powershell
cd ../..
git add docker-compose.yml apps/api docs/plan.md
git commit -m "feat(api): persist attempts and chat logs in postgres"
git push
```

---

## 14. web↔api 接続：チャットUIでSSEを表示

Claude Code（apps/web で）
```powershell
cd apps\web
claude
```

Claudeへの指示
```txt
webにチャットUIを追加してください。

要件:
- apiの POST /chat/stream にリクエストし、SSEを受信して逐次表示する
- ローカルでは apiBaseUrl = http://localhost:8000
- 開発用に X-Debug-Email を付与できる（本番では不要になる）
- 免責（学習目的/医療助言ではない）をUIに表示
- エラー時の表示を最低限追加
```

コミット
```powershell
cd ../..
git add apps/web
git commit -m "feat(web): add chat UI with SSE streaming"
git push
```

---

## 15. GitHub運用（Spec Kit流）

- `docs/tasks.md` のタスクを GitHub Issue に起こす
- GitHub Projects（Backlog/Doing/Done）で管理
- **1 Issue = 1 branch = 1 PR**
- PR本文は Claude Code に作らせる（目的/変更点/テスト/リスク）

ブランチ例
```powershell
git checkout -b feat/some-task
```

---

## 16. Cloud Run デプロイ（手動でまず通す）

### 16.1 Dockerfile を作る（Claude Codeで生成）
リポジトリ直下で:
```powershell
cd nurse-exam-app
claude
```

Claudeへの指示
```txt
Cloud Run向けのDockerfileを作成してください。

- apps/web: Next.jsをstandaloneでビルドし、Cloud Runで起動できるDockerfile
- apps/api: uvicorn起動のDockerfile
- .dockerignore も適切に
- ローカルで docker build が通ること
```

コミット
```powershell
git add apps/web/Dockerfile apps/api/Dockerfile
git commit -m "chore: add Dockerfiles for Cloud Run"
git push
```

### 16.2 GCPへデプロイ（PowerShell）
```powershell
$PROJECT_ID = "<YOUR_GCP_PROJECT_ID>"
$REGION = "asia-northeast1"
$AR_REPO = "nurse-exam"
$SHA = (git rev-parse --short HEAD)

gcloud config set project $PROJECT_ID

gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com sqladmin.googleapis.com

gcloud artifacts repositories create $AR_REPO --repository-format=docker --location=$REGION

gcloud builds submit apps/web --tag "$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/nurse-web:$SHA"
gcloud run deploy nurse-web --image "$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/nurse-web:$SHA" --region $REGION --allow-unauthenticated

gcloud builds submit apps/api --tag "$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/nurse-api:$SHA"
gcloud run deploy nurse-api --image "$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/nurse-api:$SHA" --region $REGION --allow-unauthenticated
```

---

## 17. IAP（特定メール/グループのみ）でアクセス制限

Cloud Run の直URLを使わず、入口を LB + IAP に統一します。

GCP Console で行うこと（チェックリスト）:
1. HTTP(S) Load Balancer を作成
2. Serverless NEG で nurse-web / nurse-api を紐づけ
3. パスルーティング（例：`/api/*` → api、それ以外 → web）
4. IAP を有効化
5. 許可するメール / Googleグループを登録
6. api 側は本番で IAP ヘッダの email を使って user を識別（X-Debug-Email は本番では無効）

---

## 18. `.claude/` と `.specify/` を push してよいか？

問題ありません。これらはプロジェクトの協働（あなた＋Claude）を再現可能にする設定/テンプレです。
秘密情報（APIキー等）は入れない運用にしてください（.env や Secret Manager を使用）。

---

## 19. 次にやること（おすすめ）

- questions の本データ（CSV/JSON）を作り、DBへ取り込みスクリプトを追加
- Cloud SQL + Secret Manager を接続して本番DBへ
- GitHub Actions（WIF）で Cloud Run を自動デプロイ
- IAPヘッダの実値に合わせて api の email取得を確定

---
