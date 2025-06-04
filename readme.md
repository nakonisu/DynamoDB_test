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
├── app/
│   ├── app.py                    # メインアプリケーション
│   ├── config/                   # 設定ファイル
│   │   ├── __init__.py
│   │   ├── app_config.py         # アプリケーション設定
│   │   └── database.py           # DynamoDB接続設定
│   ├── models/                   # データモデル（今後の拡張用）
│   │   └── __init__.py
│   ├── routes/                   # ルート定義
│   │   ├── __init__.py
│   │   ├── main_routes.py        # メインページルート
│   │   ├── alarm_sound_routes.py # 警報音管理ルート
│   │   └── device_routes.py      # デバイス管理ルート
│   ├── services/                 # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── id_service.py         # ID生成サービス
│   │   ├── alarm_sound_service.py # 警報音管理サービス
│   │   └── device_service.py     # デバイス管理サービス
│   ├── utils/                    # ユーティリティ関数
│   │   ├── __init__.py
│   │   └── helpers.py            # ヘルパー関数
│   ├── static/                   # 静的ファイル
│   │   └── css/
│   │       └── style.css
│   ├── templates/                # HTMLテンプレート
│   │   ├── alarm_sounds.html
│   │   └── devices.html
│   └── uploads/                  # アップロードファイル
├── venv/                         # 仮想環境
├── data/                         # DynamoDBデータ
├── DB/                           # データベース関連
├── requirements.txt              # Python依存関係
└── README.md                     # このファイル
```

### アーキテクチャの特徴

1. **レイヤード アーキテクチャ**

   - Routes: HTTP リクエストの処理
   - Services: ビジネスロジック
   - Utils: 共通ユーティリティ

2. **責任分離**

   - 各機能ごとにサービスクラスを分離
   - データベース接続設定の分離
   - 設定値の外部化

3. **Flask Blueprint**
   - 機能ごとにルートを分割
   - 保守性とスケーラビリティの向上

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
cd app
python app.py
```

アプリケーションは http://localhost:8080 で起動します。

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

### config/app_config.py

```python
UPLOAD_FOLDER = 'app/uploads'           # ファイルアップロード先
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'm4a'}  # 許可拡張子
MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 最大ファイルサイズ（16MB）
SECRET_KEY = 'your-secret-key-here'     # Flask秘密キー
DEBUG = True                            # デバッグモード
PORT = 8080                             # ポート番号
```

### config/database.py

DynamoDB ローカル接続設定

## 開発指針

### 1. コード分割原則

- **単一責任原則**: 各クラス・関数は単一の責任を持つ
- **機能分離**: ルート、サービス、ユーティリティの明確な分離
- **設定外部化**: 設定値は設定ファイルに集約

### 2. エラーハンドリング

- サービス層でのビジネスロジックエラー処理
- ルート層での HTTP エラーレスポンス
- ユーザーフレンドリーなエラーメッセージ

### 3. セキュリティ

- ファイルアップロード時の拡張子チェック
- ファイル名のサニタイズ（secure_filename 使用）
- SQL インジェクション対策（DynamoDB 使用）

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
# Pythonパスの確認
export PYTHONPATH=$PYTHONPATH:/path/to/DynamoDB_test/app

# または仮想環境の再作成
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 今後の改善点

1. **認証・認可**: ユーザー管理機能の追加
2. **ログ機能**: 操作ログの記録
3. **バリデーション強化**: より詳細な入力検証
4. **テスト**: 単体テスト・結合テストの追加
5. **API 文書化**: OpenAPI/Swagger 対応
6. **デプロイ**: Docker 化・本番環境対応
