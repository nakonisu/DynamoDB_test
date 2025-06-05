import boto3
from decimal import Decimal
import json
import time

# DynamoDB接続設定
dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url="http://localhost:8000",
    region_name="ap-northeast-1",
    aws_access_key_id="dummy",
    aws_secret_access_key="dummy",
)


def create_alarm_sounds_table():
    """警報音管理テーブルを作成"""
    try:
        table = dynamodb.create_table(
            TableName="AlarmSounds",
            KeySchema=[
                {"AttributeName": "sound_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "sound_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        print("AlarmSounds テーブルが作成されました")

        # サンプルデータを挿入
        sample_sounds = [
            {
                "sound_id": "fire_alarm_001",
                "sound_name": "火災警報音",
                "s3_key": "ref/fire_alarm_001.wav",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            },
            {
                "sound_id": "evacuation_alarm_001",
                "sound_name": "避難警報音",
                "s3_key": "ref/evacuation_alarm_001.wav",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            },
            {
                "sound_id": "emergency_siren_001",
                "sound_name": "緊急サイレン",
                "s3_key": "ref/emergency_siren_001.wav",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            },
        ]

        for sound in sample_sounds:
            table.put_item(Item=sound)

        print("サンプル警報音データを挿入しました")

    except Exception as e:
        print(f"AlarmSounds テーブル作成エラー: {e}")


def create_devices_table():
    """デバイステーブルを作成"""
    try:
        table = dynamodb.create_table(
            TableName="Devices",
            KeySchema=[
                {"AttributeName": "device_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "device_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        print("Devices テーブルが作成されました")

        # サンプルデータを挿入
        sample_devices = [
            {
                "device_id": "7CDDE907C7EF",
                "device_configs": [
                    {
                        "sound_id": "fire_alarm_001",
                        "threshold": {
                            "auto": Decimal("21.5"),
                            "manual": Decimal("25.0"),
                        },
                    },
                    {
                        "sound_id": "evacuation_alarm_001",
                        "threshold": {"auto": Decimal("18.0")},
                    },
                ],
                "detection_status": True,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            },
            {
                "device_id": "A1B2C3D4E5F6",
                "device_configs": [
                    {
                        "sound_id": "emergency_siren_001",
                        "threshold": {
                            "auto": Decimal("20.0"),
                            "manual": Decimal("22.5"),
                        },
                    }
                ],
                "detection_status": False,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            },
        ]

        for device in sample_devices:
            table.put_item(Item=device)

        print("サンプルデバイスデータを挿入しました")

    except Exception as e:
        print(f"Devices テーブル作成エラー: {e}")


def delete_old_movies_table():
    """古いMoviesテーブルを削除"""
    try:
        table = dynamodb.Table("Movies")
        table.delete()
        print("古いMoviesテーブルを削除しました")
    except Exception as e:
        print(f"Moviesテーブル削除エラー（存在しない可能性があります）: {e}")


if __name__ == "__main__":
    print("=== 警報音管理システム マイグレーション開始 ===")

    # 古いテーブルを削除
    delete_old_movies_table()

    # 新しいテーブルを作成
    create_alarm_sounds_table()
    create_devices_table()

    print("=== マイグレーション完了 ===")
