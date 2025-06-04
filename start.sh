#!/bin/bash

# 警報音管理システム起動スクリプト

echo "=== 警報音管理システム起動 ==="

# DynamoDBの起動確認・起動
echo "1. DynamoDB起動確認..."
if ! docker ps | grep -q dynamodb-local; then
    echo "DynamoDBを起動しています..."
    cd DB && docker-compose up -d
    cd ..
    echo "DynamoDBが起動しました。"
    sleep 3
else
    echo "DynamoDBは既に起動済みです。"
fi

# 仮想環境のアクティベート
echo "2. 仮想環境をアクティベート..."
source venv/bin/activate

# テーブル作成（既存の場合はスキップ）
echo "3. DynamoDBテーブル確認・作成..."
python DB/migrate.py

# Flaskアプリケーション起動
echo "4. Flaskアプリケーション起動..."
echo "ブラウザで http://127.0.0.1:5000 にアクセスしてください"
echo "停止するには Ctrl+C を押してください"
python app.py
