from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import boto3
from decimal import Decimal
import time
import os
import random
from datetime import datetime

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url="http://localhost:8000",
    region_name="ap-northeast-1",
    aws_access_key_id="dummy",
    aws_secret_access_key="dummy",
)

alarm_sounds_table = dynamodb.Table("AlarmSounds")
devices_table = dynamodb.Table("Devices")

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Flashメッセージ用

# Jinjaテンプレート用のカスタムフィルタを追加
@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime(timestamp):
    """タイムスタンプを日本語の日時文字列に変換"""
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y年%m月%d日 %H:%M')
    return '-'

# アップロード設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'm4a'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB制限

# アップロードディレクトリが存在しない場合は作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """許可されたファイル拡張子かチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# DynamoDBのDecimalをJSONシリアライズ可能に変換
def decimal_to_float(item):
    if isinstance(item, dict):
        return {k: decimal_to_float(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [decimal_to_float(v) for v in item]
    elif isinstance(item, Decimal):
        return float(item)
    return item

# ID自動生成関数
def generate_next_sound_id():
    """警報音IDを自動生成（数字）"""
    res = alarm_sounds_table.scan()
    items = res.get("Items", [])
    if not items:
        return "1"
    
    # 既存のIDから最大値を取得
    max_id = 0
    for item in items:
        try:
            current_id = int(item["sound_id"])
            max_id = max(max_id, current_id)
        except ValueError:
            # 数字でないIDは無視
            continue
    
    return str(max_id + 1)

def generate_next_device_id():
    """デバイスIDを自動生成（数字）"""
    res = devices_table.scan()
    items = res.get("Items", [])
    if not items:
        return "1"
    
    # 既存のIDから最大値を取得
    max_id = 0
    for item in items:
        try:
            current_id = int(item["device_id"])
            max_id = max(max_id, current_id)
        except ValueError:
            # 数字でないIDは無視
            continue
    
    return str(max_id + 1)

def generate_random_threshold():
    """ランダムな閾値を生成（Lambda実装予定のため仮実装）"""
    return round(random.uniform(15.0, 30.0), 1)

def fix_existing_file_paths():
    """既存データのlocal_pathを修正"""
    try:
        res = alarm_sounds_table.scan()
        items = res.get("Items", [])
        
        for item in items:
            sound_id = item["sound_id"]
            s3_key = item.get("s3_key", "")
            local_path = item.get("local_path")
            
            # local/で始まるs3_keyがあり、local_pathが不正な場合
            if s3_key.startswith("local/"):
                filename = s3_key.replace("local/", "")
                expected_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                # local_pathが不正または存在しない場合に修正
                if not local_path or not os.path.isabs(local_path) or local_path != expected_path:
                    if os.path.exists(expected_path):
                        alarm_sounds_table.update_item(
                            Key={"sound_id": sound_id},
                            UpdateExpression="SET local_path = :path",
                            ExpressionAttributeValues={":path": expected_path}
                        )
                        print(f"警報音 {sound_id} のパスを修正しました: {expected_path}")
        
    except Exception as e:
        print(f"パス修正エラー: {e}")

# ルーティング
@app.route("/")
def index():
    # アプリ起動時にパスを修正
    fix_existing_file_paths()
    return redirect(url_for('alarm_sounds_page'))

@app.route("/alarm-sounds-page")
def alarm_sounds_page():
    """警報音管理ページ"""
    res = alarm_sounds_table.scan()
    alarm_sounds = decimal_to_float(res.get("Items", []))
    return render_template("alarm_sounds.html", alarm_sounds=alarm_sounds)

@app.route("/devices-page")
def devices_page():
    """デバイス管理ページ"""
    res = devices_table.scan()
    devices = decimal_to_float(res.get("Items", []))
    
    # 警報音リストも取得（デバイス設定で使用）
    alarm_res = alarm_sounds_table.scan()
    alarm_sounds = decimal_to_float(alarm_res.get("Items", []))
    
    return render_template("devices.html", devices=devices, alarm_sounds=alarm_sounds)

# ============ 警報音管理 API ============

@app.route("/alarm-sounds", methods=["GET"])
def list_alarm_sounds():
    """警報音一覧取得"""
    res = alarm_sounds_table.scan()
    items = decimal_to_float(res.get("Items", []))
    return jsonify(items)

@app.route("/alarm-sounds", methods=["POST"])
def add_alarm_sound():
    """警報音追加"""
    try:
        # ID自動生成
        sound_id = generate_next_sound_id()
        sound_name = request.form.get('sound_name')
        
        if not sound_name:
            flash('警報音名は必須です', 'error')
            return redirect(url_for('alarm_sounds_page'))
        
        # ファイルアップロード処理
        if 'sound_file' not in request.files:
            flash('音源ファイルを選択してください', 'error')
            return redirect(url_for('alarm_sounds_page'))
        
        file = request.files['sound_file']
        if file.filename == '':
            flash('音源ファイルを選択してください', 'error')
            return redirect(url_for('alarm_sounds_page'))
        
        if file and allowed_file(file.filename):
            # ファイル名を安全にする
            filename = secure_filename(file.filename)
            # ファイル名を{sound_id}.{拡張子}に変更
            file_extension = filename.rsplit('.', 1)[1].lower()
            new_filename = f"{sound_id}.{file_extension}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            
            # ファイル保存
            file.save(file_path)
            
            # DynamoDBに保存
            item = {
                "sound_id": sound_id,
                "sound_name": sound_name,
                "s3_key": f"local/{new_filename}",  # ローカルファイルパス
                "local_path": os.path.abspath(file_path),  # 絶対パスで保存
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
            alarm_sounds_table.put_item(Item=item)
            
            flash(f'警報音「{sound_name}」を登録しました（ID: {sound_id}）', 'success')
        else:
            flash('許可されていないファイル形式です（wav, mp3, ogg, m4a のみ）', 'error')
            
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('alarm_sounds_page'))

@app.route("/alarm-sounds/<sound_id>", methods=["GET"])
def get_alarm_sound(sound_id):
    """特定の警報音取得"""
    res = alarm_sounds_table.get_item(Key={"sound_id": sound_id})
    item = res.get("Item", {})
    return jsonify(decimal_to_float(item))

@app.route("/alarm-sounds/<sound_id>", methods=["PUT"])
def update_alarm_sound(sound_id):
    """警報音更新（API用）"""
    data = request.json
    alarm_sounds_table.update_item(
        Key={"sound_id": sound_id},
        UpdateExpression="SET sound_name = :name, s3_key = :s3_key, updated_at = :updated_at",
        ExpressionAttributeValues={
            ":name": data["sound_name"],
            ":s3_key": data.get("s3_key", f"ref/{sound_id}.wav"),
            ":updated_at": int(time.time()),
        }
    )
    return jsonify({"message": "警報音を更新しました"})

@app.route("/alarm-sounds/<sound_id>", methods=["POST"])
def update_alarm_sound_form(sound_id):
    """警報音更新（フォーム送信用）"""
    try:
        sound_name = request.form.get('sound_name')
        s3_key = request.form.get('s3_key')
        
        if not sound_name:
            flash('警報音名は必須です', 'error')
            return redirect(url_for('alarm_sounds_page'))
        
        alarm_sounds_table.update_item(
            Key={"sound_id": sound_id},
            UpdateExpression="SET sound_name = :name, s3_key = :s3_key, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":name": sound_name,
                ":s3_key": s3_key or f"ref/{sound_id}.wav",
                ":updated_at": int(time.time()),
            }
        )
        flash(f'警報音「{sound_name}」を更新しました', 'success')
    except Exception as e:
        flash(f'更新に失敗しました: {str(e)}', 'error')
    
    return redirect(url_for('alarm_sounds_page'))

@app.route("/alarm-sounds/<sound_id>/delete", methods=["POST"])
def delete_alarm_sound(sound_id):
    """警報音削除"""
    try:
        # ファイルも削除する場合（オプション）
        res = alarm_sounds_table.get_item(Key={"sound_id": sound_id})
        item = res.get("Item", {})
        if item:
            local_path = item.get("local_path")
            
            # local_pathがない場合はs3_keyから推測
            if not local_path:
                s3_key = item.get("s3_key", "")
                if s3_key.startswith("local/"):
                    filename = s3_key.replace("local/", "")
                    local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # 相対パスの場合は絶対パスに変換
            if local_path and not os.path.isabs(local_path):
                local_path = os.path.abspath(os.path.join(os.getcwd(), local_path))
            
            # ファイルが存在する場合は削除
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
        
        alarm_sounds_table.delete_item(Key={"sound_id": sound_id})
        flash('警報音を削除しました', 'success')
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'error')
    
    return redirect(url_for('alarm_sounds_page'))

@app.route("/devices/<device_id>/delete", methods=["POST"])  
def delete_device(device_id):
    """デバイス削除"""
    try:
        devices_table.delete_item(Key={"device_id": device_id})
        flash('デバイスを削除しました', 'success')
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'error')
    
    return redirect(url_for('devices_page'))

# ============ デバイス管理 API ============

@app.route("/devices", methods=["GET"])
def list_devices():
    """デバイス一覧取得"""
    res = devices_table.scan()
    items = decimal_to_float(res.get("Items", []))
    return jsonify(items)

@app.route("/devices", methods=["POST"])
def add_device():
    """デバイス追加"""
    try:
        # ID自動生成
        device_id = generate_next_device_id()
        
        # フォームからデータを取得
        sound_ids = request.form.getlist('sound_id[]')
        manual_thresholds = request.form.getlist('threshold_manual[]')
        detection_status = request.form.get('detection_status') == 'on'
        
        if not sound_ids or not sound_ids[0]:
            flash('警報音を少なくとも1つ選択してください', 'error')
            return redirect(url_for('devices_page'))
        
        # デバイス設定を構築
        device_configs = []
        for i, sound_id in enumerate(sound_ids):
            if sound_id:  # 空でない場合のみ追加
                threshold = {
                    "auto": Decimal(str(generate_random_threshold()))  # ランダム自動閾値
                }
                
                # 手動閾値が設定されている場合は追加
                if i < len(manual_thresholds) and manual_thresholds[i]:
                    threshold["manual"] = Decimal(str(float(manual_thresholds[i])))
                
                device_configs.append({
                    "sound_id": sound_id,
                    "threshold": threshold
                })
        
        # DynamoDBに保存
        item = {
            "device_id": device_id,
            "device_configs": device_configs,
            "detection_status": detection_status,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        devices_table.put_item(Item=item)
        
        flash(f'デバイスを登録しました（ID: {device_id}）', 'success')
        
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('devices_page'))

@app.route("/devices/<device_id>", methods=["GET"])
def get_device(device_id):
    """特定のデバイス取得"""
    res = devices_table.get_item(Key={"device_id": device_id})
    item = res.get("Item", {})
    return jsonify(decimal_to_float(item))

@app.route("/devices/<device_id>", methods=["PUT"])
def update_device(device_id):
    """デバイス更新（API用）"""
    data = request.json
    
    # device_configsのthresholdをDecimalに変換
    configs = data.get("device_configs", [])
    for config in configs:
        if "threshold" in config:
            threshold = config["threshold"]
            for key, value in threshold.items():
                threshold[key] = Decimal(str(value))
    
    devices_table.update_item(
        Key={"device_id": device_id},
        UpdateExpression="SET device_configs = :configs, detection_status = :status, updated_at = :updated_at",
        ExpressionAttributeValues={
            ":configs": configs,
            ":status": data.get("detection_status", True),
            ":updated_at": int(time.time()),
        }
    )
    return jsonify({"message": "デバイスを更新しました"})

@app.route("/devices/<device_id>", methods=["POST"])
def update_device_form(device_id):
    """デバイス更新（フォーム送信用）"""
    try:
        detection_status = request.form.get('detection_status') == 'on'
        sound_ids = request.form.getlist('sound_id[]')
        manual_thresholds = request.form.getlist('threshold_manual[]')
        
        # デバイス設定を構築
        device_configs = []
        for i, sound_id in enumerate(sound_ids):
            if sound_id:  # 空でない場合のみ追加
                threshold = {
                    "auto": Decimal(str(generate_random_threshold()))  # ランダム自動閾値
                }
                
                # 手動閾値が設定されている場合は追加
                if i < len(manual_thresholds) and manual_thresholds[i]:
                    threshold["manual"] = Decimal(str(float(manual_thresholds[i])))
                
                device_configs.append({
                    "sound_id": sound_id,
                    "threshold": threshold
                })
        
        devices_table.update_item(
            Key={"device_id": device_id},
            UpdateExpression="SET device_configs = :configs, detection_status = :status, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":configs": device_configs,
                ":status": detection_status,
                ":updated_at": int(time.time()),
            }
        )
        flash(f'デバイス設定を更新しました', 'success')
    except Exception as e:
        flash(f'更新に失敗しました: {str(e)}', 'error')
    
    return redirect(url_for('devices_page'))

@app.route("/devices/<device_id>/effective-thresholds", methods=["GET"])
def get_effective_thresholds(device_id):
    """デバイスの有効な閾値を取得（manual優先、なければauto）"""
    res = devices_table.get_item(Key={"device_id": device_id})
    item = res.get("Item", {})
    
    if not item:
        return jsonify({"error": "デバイスが見つかりません"}), 404
        
    effective_configs = []
    for cfg in item.get("device_configs", []):
        threshold = cfg.get("threshold", {})
        effective = threshold.get("manual", threshold.get("auto"))
        effective_configs.append({
            "sound_id": cfg["sound_id"],
            "effective_threshold": float(effective) if effective else None
        })
    
    return jsonify(effective_configs)

@app.route("/sound-file/<path:filename>", methods=["GET"])
def serve_sound_file(filename):
    """音声ファイルを提供"""
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route("/play-sound/<sound_id>")
def play_sound(sound_id):
    """警報音ファイルを提供"""
    try:
        # DynamoDBから音声ファイル情報を取得
        res = alarm_sounds_table.get_item(Key={"sound_id": sound_id})
        item = res.get("Item", {})
        
        if not item:
            return jsonify({"error": "警報音が見つかりません"}), 404
        
        # ローカルファイルパスを確認・修正
        local_path = item.get("local_path")
        
        # local_pathがない場合やパスが正しくない場合の処理
        if not local_path:
            # s3_keyからファイル名を推測してローカルパスを構築
            s3_key = item.get("s3_key", "")
            if s3_key.startswith("local/"):
                filename = s3_key.replace("local/", "")
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            else:
                return jsonify({"error": "音声ファイルのパス情報がありません"}), 404
        
        # 相対パスの場合は絶対パスに変換
        if not os.path.isabs(local_path):
            local_path = os.path.abspath(os.path.join(os.getcwd(), local_path))
        
        # ファイルの存在確認
        if not os.path.exists(local_path):
            return jsonify({"error": f"音声ファイルが見つかりません: {local_path}"}), 404
        
        # ファイル拡張子に基づいてMIMEタイプを設定
        file_extension = os.path.splitext(local_path)[1].lower()
        mimetype_map = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4'
        }
        mimetype = mimetype_map.get(file_extension, 'audio/wav')
        
        # ファイルを送信
        return send_file(local_path, as_attachment=False, mimetype=mimetype)
        
    except Exception as e:
        return jsonify({"error": f"音声ファイルの取得に失敗しました: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8082)
