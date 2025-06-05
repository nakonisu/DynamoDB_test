# 警報音管理システム

警報音の管理とデバイス設定を行う Web アプリケーション

## 概要

本システムは以下の機能を提供します：

- 警報音ファイルのアップロード・管理
- デバイスの警報音設定管理
- 検知閾値の設定（手動・自動）

## システム構成

### ディレクトリ構造

```
DynamoDB_test/
├── app.py                        # メインアプリケーション
├── app/                          # アプリケーション（現在未使用）
│   └── app.py
├── static/                       # 静的ファイル
│   └── css/
│       └── style.css
├── templates/                    # HTMLテンプレート
│   ├── alarm_sounds.html
│   └── devices.html
├── uploads/                      # アップロードファイル
│   ├── 4.wav
│   ├── 5.wav
│   └── test_alarm.wav
├── data/                         # DynamoDBデータ
│   └── dynamodb/
│       └── shared-local-instance.db
├── DB/                           # データベース関連
│   ├── docker-compose.yml        # DynamoDB Local設定
│   ├── migrate.py                # テーブル作成・マイグレーション
│   ├── test.py                   # テスト用スクリプト
│   └── data/
│       └── dynamodb/
│           └── shared-local-instance.db
├── venv/                         # 仮想環境
├── requirements.txt              # Python依存関係
├── .env                          # 環境変数設定
├── .gitignore                    # Git除外設定
└── readme.md                     # このファイル
```

### アーキテクチャの特徴

1. **シンプルな構造**

   - 単一ファイル構成（app.py）でプロトタイプ開発
   - 必要最小限の機能に集約
   - DynamoDB Local を使用したローカル開発環境

2. **責任分離**

   - ルーティング、ビジネスロジック、データアクセスを同一ファイル内で分離
   - テンプレートとスタイルの分離
   - 設定値の明示的定義

3. **Flask の基本機能活用**
   - シンプルなルーティング
   - テンプレートエンジン（Jinja2）
   - ファイルアップロード機能

## セットアップ

### 1. 仮想環境の作成・アクティベート

```bash
cd DynamoDB_test
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. DynamoDB ローカル起動

```bash
cd DB
docker-compose up -d
```

### 4. テーブル作成

```bash
cd DB
python migrate.py
```

### 5. アプリケーション起動

```bash
# プロジェクトルートディレクトリで実行
python app.py
```

アプリケーションは http://localhost:5000 で起動します。

## 主要機能

### 1. 警報音管理 (`/alarm-sounds-page`)

- **新規登録**: 音源ファイル（wav, mp3, ogg, m4a）のアップロード
- **一覧表示**: 登録済み警報音の表示
- **更新**: 警報音名と S3 キーの編集
- **削除**: 警報音とファイルの削除
- **再生**: ブラウザでの音源再生

### 2. デバイス管理 (`/devices-page`)

- **新規登録**: 警報音設定と検知状態の設定
- **一覧表示**: 登録済みデバイスの表示
- **削除**: デバイス設定の削除
- **閾値管理**: 手動閾値と自動閾値の管理

## API エンドポイント

### 警報音管理

| メソッド | エンドポイント             | 説明                   |
| -------- | -------------------------- | ---------------------- |
| GET      | `/alarm-sounds`            | 警報音一覧取得         |
| POST     | `/alarm-sounds`            | 警報音追加             |
| GET      | `/alarm-sounds/<sound_id>` | 特定警報音取得         |
| PUT      | `/alarm-sounds/<sound_id>` | 警報音更新（API）      |
| POST     | `/alarm-sounds/<sound_id>` | 警報音更新（フォーム） |
| DELETE   | `/alarm-sounds/<sound_id>` | 警報音削除             |
| GET      | `/play-sound/<sound_id>`   | 音源ファイル配信       |

### デバイス管理

| メソッド | エンドポイント                              | 説明                     |
| -------- | ------------------------------------------- | ------------------------ |
| GET      | `/devices`                                  | デバイス一覧取得         |
| POST     | `/devices`                                  | デバイス追加             |
| GET      | `/devices/<device_id>`                      | 特定デバイス取得         |
| PUT      | `/devices/<device_id>`                      | デバイス更新（API）      |
| POST     | `/devices/<device_id>`                      | デバイス更新（フォーム） |
| DELETE   | `/devices/<device_id>`                      | デバイス削除             |
| GET      | `/devices/<device_id>/effective-thresholds` | 有効閾値取得             |

## データベース設計

### AlarmSounds テーブル

| 項目       | 型     | 説明                       |
| ---------- | ------ | -------------------------- |
| sound_id   | String | 警報音 ID（主キー）        |
| sound_name | String | 警報音名                   |
| s3_key     | String | S3 キー                    |
| local_path | String | ローカルファイルパス       |
| created_at | Number | 作成日時（Unix timestamp） |
| updated_at | Number | 更新日時（Unix timestamp） |

### Devices テーブル

| 項目             | 型      | 説明                       |
| ---------------- | ------- | -------------------------- |
| device_id        | String  | デバイス ID（主キー）      |
| device_configs   | List    | 警報音設定リスト           |
| detection_status | Boolean | 検知状態                   |
| created_at       | Number  | 作成日時（Unix timestamp） |
| updated_at       | Number  | 更新日時（Unix timestamp） |

#### device_configs 構造

```json
[
  {
    "sound_id": "警報音ID",
    "threshold": {
      "auto": 25.5, // 自動生成閾値
      "manual": 30.0 // 手動設定閾値（任意）
    }
  }
]
```

## 設定ファイル

### app.py 内の設定

```python
# ファイルアップロード設定
UPLOAD_FOLDER = 'uploads'                        # ファイルアップロード先
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'm4a'} # 許可拡張子
MAX_CONTENT_LENGTH = 16 * 1024 * 1024             # 最大ファイルサイズ（16MB）
SECRET_KEY = 'your-secret-key-here'               # Flask秘密キー

# DynamoDB 接続設定
endpoint_url = "http://localhost:8000"            # DynamoDB Local URL
region_name = "ap-northeast-1"                    # AWS リージョン
```

### DB/docker-compose.yml

DynamoDB Local 環境設定

```yaml
version: "3.8"
services:
  dynamodb:
    image: amazon/dynamodb-local:latest
    container_name: dynamodb-local
    command: "-jar DynamoDBLocal.jar -sharedDb -dbPath /home/dynamodb"
    ports:
      - "8000:8000"
    volumes:
      - ./data/dynamodb:/home/dynamodb
```

## 開発指針

### 1. プロトタイプ開発

- **単一ファイル構成**: 素早いプロトタイプ開発のため
- **機能最小化**: 必要最小限の機能に絞り込み
- **将来の拡張性**: モジュール化への移行可能性を考慮

### 2. エラーハンドリング

- Flask の標準エラーハンドリング
- ユーザーフレンドリーなメッセージ表示
- ファイルアップロード時の検証

### 3. セキュリティ

- ファイルアップロード時の拡張子チェック
- ファイル名のサニタイズ（secure_filename 使用）
- DynamoDB を使用したインジェクション対策

## トラブルシューティング

### 1. DynamoDB 接続エラー

```bash
# DynamoDBローカルの状態確認
cd DB
docker-compose ps

# 再起動
docker-compose restart
```

### 2. ファイルアップロードエラー

- `uploads/` ディレクトリの存在・権限確認
- ファイルサイズ制限の確認（16MB）
- 許可拡張子の確認

### 3. インポートエラー

```bash
# 仮想環境の再作成
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# プロジェクトディレクトリで実行
cd /Users/nishioshin/Documents/0_batonext/0_task/202504_警報音検知/DynamoDB_test
python app.py
```

## 今後の改善点

1. **アーキテクチャ改善**: モジュール化・レイヤード アーキテクチャへの移行
2. **認証・認可**: ユーザー管理機能の追加
3. **ログ機能**: 操作ログの記録
4. **バリデーション強化**: より詳細な入力検証
5. **テスト**: 単体テスト・結合テストの追加
6. **API 文書化**: OpenAPI/Swagger 対応
7. **デプロイ**: Docker 化・本番環境対応
8. **環境設定**: .env ファイルの活用とセキュリティ強化
