import boto3, json, pprint

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url="http://localhost:8000",
    region_name="ap-northeast-1",
    aws_access_key_id="dummy",
    aws_secret_access_key="dummy",
)

table = dynamodb.Table("Movies")

# 全件スキャン（注意：大規模なら分割）
response = table.scan()
items = response["Items"]

# 見やすく出力
pprint.pp(items)              # コンソール用
print(json.dumps(items, indent=2, ensure_ascii=False))  # JSON 文字列で保存も可
