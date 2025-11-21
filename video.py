# video.py

from flask import Blueprint, render_template, jsonify, request, send_from_directory, abort, current_app, Response
from flask_login import login_required, current_user
from models import UserRole, db, VideoLog
import os
from utils import record_log
from datetime import datetime
import mimetypes

video_bp = Blueprint('video', __name__, template_folder='templates', static_folder='static')

# GÜNCELLENDİ: VIDEO_DATA
VIDEO_DATA = [
    {
        "key": "video_1",
        "title_lang_key": "video_1_title", # Bu anahtar JS'de çevrilecek
        "video_file": "youtube", # YouTube videosu olduğunu belirtir
        "youtube_id": "9VHpxSrIhvk", # Örnek bir "Kodlama Nedir?" video ID'si
        "thumbnail": None, # Artık kullanılmayacak, HTML'de ID'den çekilecek
        "tools": [] # Araçlar kaldırıldı
    },
    {
        "key": "video_2",
        "title_lang_key": "video_2_title",
        "video_file": "video_2.mp4",
        "thumbnail": "video_2_thumbnail.jpg",
        "tools": [
            {"name": "Aimbot Entegrasyon Kiti", "file": "aimbot_kit.zip", "lang_key": "video_2_tool_1"},
        ]
    },
    {
        "key": "video_3",
        "title_lang_key": "video_3_title",
        "video_file": "video_3.mp4",
        "thumbnail": "video_3_thumbnail.png",
        "tools": []
    },
]
# ... (Diğer video verileri buraya eklenebilir)
# ...

def get_video_access_level(user_role):
    if user_role in [UserRole.dev, UserRole.caylak_admin, UserRole.usta_admin, UserRole.kurucu]:
        return float('inf')
    elif user_role == UserRole.premium:
        return 2 # Premium 2 video izleyebilsin
    else:
        return 1

# === GÜNCELLENMİŞ GÜVENLİK VE STREAMING ROTASI ===
@video_bp.route('/stream/<path:filename>')
@login_required
def stream_video(filename):
    # YENİ: YouTube videoları bu rotayı kullanmaz
    if filename == "youtube":
        abort(403) 
        
    referer = request.headers.get("Referer")
    host_url = request.host_url
    if not referer or not referer.startswith(host_url):
        current_app.logger.warning(f"Doğrudan/İzinsiz video erişim denemesi engellendi: Kullanıcı '{current_user.username}', Video: '{filename}', Referer: '{referer}'")
        abort(403)
        
    video_index = next((i for i, v in enumerate(VIDEO_DATA) if v["video_file"] == filename), -1)
    if video_index == -1: abort(404)
    
    access_level = get_video_access_level(current_user.role)
    if (video_index + 1) > access_level:
        current_app.logger.warning(f"Yetkisiz video erişim denemesi: Kullanıcı '{current_user.username}', Video: '{filename}'")
        abort(403)

    video_path = os.path.join(current_app.root_path, 'static', 'videos', filename)
    if not os.path.exists(video_path): abort(404)

    # === VİDEO İLERLETME (Streaming) KISMI ===
    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)
    
    start = 0
    end = file_size - 1
    
    if range_header:
        range_value = range_header.strip().split('=')[1]
        parts = range_value.split('-')
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
    
    chunk_size = (end - start) + 1
    
    def generate_chunks():
        with open(video_path, 'rb') as f:
            f.seek(start)
            bytes_read = 0
            while bytes_read < chunk_size:
                read_size = min(1024 * 1024, chunk_size - bytes_read)
                data = f.read(read_size)
                if not data:
                    break
                bytes_read += len(data)
                yield data

    mimetype = mimetypes.guess_type(filename)[0] or 'video/mp4'
    resp = Response(generate_chunks(), 206, mimetype=mimetype, content_type=mimetype, direct_passthrough=True)
    resp.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
    resp.headers.add('Accept-Ranges', 'bytes')
    resp.headers.add('Content-Length', str(chunk_size))
    return resp

# --- Diğer Rotalar (Değişiklik Yok) ---
@video_bp.route('/videos')
@login_required
def videos_page():
    access_level = get_video_access_level(current_user.role)
    processed_videos = []
    for i, video in enumerate(VIDEO_DATA):
        video_copy = video.copy()
        video_copy["is_locked"] = (i + 1) > access_level
        
        # YENİ: YouTube ID'sini de kopyala (varsa)
        video_copy["youtube_id"] = video.get("youtube_id", None) 
        
        processed_videos.append(video_copy)
    return render_template('videos.html', user=current_user, videos=processed_videos)

@video_bp.route('/download_tool/<filename>')
@login_required
def download_tool(filename):
    # ... (Bu fonksiyonda değişiklik yok, Video 1'in tool listesi boş olduğu için
    #      doğal olarak indirme yetkisi vermeyecektir) ...
    can_download = False
    access_level = get_video_access_level(current_user.role)
    for i, video in enumerate(VIDEO_DATA):
        if (i + 1) > access_level: continue
        for tool in video.get("tools", []):
            if tool["file"] == filename:
                can_download = True
                break
        if can_download: break
    if not can_download: abort(403)
    applications_path = os.path.join(current_app.root_path, 'static', 'applications')
    return send_from_directory(applications_path, filename, as_attachment=True)

@video_bp.route('/videos/log_progress', methods=['POST'])
@login_required
def log_video_progress():
    # ... (Bu fonksiyonda değişiklik yok, video_key üzerinden çalıştığı için
    #      hem YouTube hem de local videoları loglayabilir) ...
    data = request.json
    video_key = data.get('video_key')
    current_time = data.get('currentTime')
    if not video_key or current_time is None: return jsonify({"error": "Eksik veri"}), 400
    try:
        watch_time = int(float(current_time))
        video_index = next((i for i, v in enumerate(VIDEO_DATA) if v['key'] == video_key), -1)
        if video_index == -1: return jsonify({"error": "Geçersiz video"}), 404
        access_level = get_video_access_level(current_user.role)
        if (video_index + 1) > access_level: return jsonify({"error": "Yetkisiz işlem"}), 403
        log = VideoLog.query.filter_by(user_id=current_user.id, video_key=video_key).first()
        if not log:
            log = VideoLog(user_id=current_user.id, video_key=video_key)
            db.session.add(log)
            record_log(current_user, f"'{video_key}' videosunu izlemeye başladı.")
        log.watch_time_seconds = watch_time
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Video log kaydı hatası: {e}")
        return jsonify({"error": "Sunucu hatası"}), 500