import os
import uuid
import bleach
import traceback
import threading
import json
import sys
from .cut import crop_image
from pathlib import Path
from datetime import datetime, timedelta
from flask import (Blueprint, request, jsonify, current_app, render_template,
                   url_for, send_from_directory, flash, redirect, session)
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from sqlalchemy import desc, or_
from PIL import Image, ImageDraw, ImageFont, ImageStat
import numpy as np
import ffmpeg
from collections import Counter

from extensions import db
from .models import Post, PostMedia, User, Like, Comment
from .models import Reaction
from models import UserRole, MuteLog, PostReport

# Ana dizindeki modellere erişim için path ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

forum_bp = Blueprint('forum', __name__, static_folder='static', static_url_path='/forum/static')

# --- AYARLAR VE SABİTLER (GÜNCELLENDİ) ---
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
VIDEO_EXTENSIONS = {'mp4', 'mov'}
AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'aac'}
DOCUMENT_EXTENSIONS = {
    'docx', 'pdf', 'txt', 'xls', 'html', 'zip', 'rar', '7z',
    'tar', 'gz', 'css', 'js', 'php', 'py', 'json', 'xml', 'cs', 'sql', 'cpp'
}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS

# Resim Limitleri
MAX_IMAGE_COUNT = 7
MAX_IMAGE_SIZE_MB = 6
MAX_TOTAL_IMAGE_SIZE_MB = 42

# Video Limitleri
MAX_VIDEO_COUNT = 1
MAX_VIDEO_SIZE_MB = 50

# YENİ: Ses Limiti
MAX_AUDIO_COUNT = 1
MAX_AUDIO_SIZE_MB = 20

# YENİ: Belge Limiti
MAX_DOCUMENT_COUNT = 1
MAX_DOCUMENT_SIZE_MB = 70

# İçerik Limiti
MAX_CONTENT_LENGTH_CHARS = 1000

# --- YENİ: SPAM KONTROL SABİTLERİ (Daha Hoşgörülü Ayarlarla) ---
MIN_POST_INTERVAL_SECONDS = 10 # İki gönderi arasındaki minimum süre (10 saniye)
MIN_SPAM_CHECK_LENGTH = 20   # Sadece 20 karakterden uzun metinler spam filtresine girer
MIN_UNIQUE_WORD_RATIO = 0.2 # İçerikteki benzersiz kelime oranı ("spam spam spam" için düşüktür)
MAX_REPETITION_PERCENTAGE = 50 # İçerikteki en sık tekrar eden harfin yüzdesi ("aaaaa" için yüksektir)

# GÜNCELLENDİ: Aşırı büyük harf kontrolü kaldırıldı ve Ortalama Kelime Uzunluğu eklendi
def is_content_spammy(content: str) -> bool:
    """
    Bir metnin SPAM OLABİLECEĞİNE dair şüpheleri analiz eder.
    Kısa ve normal metinlerde oldukça hoşgörülüdür.
    """
    content_length = len(content)
    # 1. Kural: Metin çok kısaysa, asla spam değildir. ("merhaba" gibi durumlar için)
    if content_length < MIN_SPAM_CHECK_LENGTH:
        return False

    # 2. Katman: Anlamsız Tekrarlayan Karakter Analizi (örn: 'aaaaaaaaa')
    char_counts = Counter(content)
    most_common_char_count = char_counts.most_common(1)[0][1]
    repetition_percentage = (most_common_char_count / content_length) * 100
    if repetition_percentage > MAX_REPETITION_PERCENTAGE:
        current_app.logger.warning(f"SPAM ŞÜPHESİ (Tekrarlayan Karakter): %{repetition_percentage:.2f}")
        return True

    words = content.lower().split()
    word_count = len(words)

    # 4. YENİ KATMAN: Anlamsız uzun kelimeler (örn: 'jbsfıhsuıfwufuwbıasdasd')
    # "jbsfıhsuıfwufuwbı" gibi anlamsız ve tek kelimeden oluşan spamları yakalar.
    if word_count > 0 and content_length > MIN_SPAM_CHECK_LENGTH:
        avg_word_length = content_length / word_count
        # Eğer metin 25 karakterden uzunsa VE ortalama kelime uzunluğu 20'den fazlaysa
        if avg_word_length > 20: 
             current_app.logger.warning(f"SPAM ŞÜPHESİ (Anlamsız Uzunluk): Ortalama Kelime Uzunluğu -> {avg_word_length:.2f}")
             return True
             
    # 3. Katman: Düşük Benzersiz Kelime Oranı (örn: 'bedava ürün bedava ürün bedava ürün')
    if word_count > 5:
        unique_words_count = len(set(words))
        unique_ratio = unique_words_count / len(words)
        if unique_ratio < MIN_UNIQUE_WORD_RATIO:
            current_app.logger.warning(f"SPAM ŞÜPHESİ (Düşük Benzersiz Kelime): Oran -> {unique_ratio:.2f}")
            return True

    return False # Bu testlerden geçtiyse, içerik temizdir.

@forum_bp.route("/posts/<int:post_id>/report", methods=["POST"])
@login_required
def report_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error_key": "post_not_found"}), 404

    data = request.get_json()
    reason_key = data.get('reason')
    
    if not reason_key:
        return jsonify({"error": "Sebep belirtilmedi"}), 400

    try:
        # Aynı kullanıcı aynı postu tekrar şikayet etmesin (Spam koruması)
        existing_report = PostReport.query.filter_by(
            post_id=post_id, 
            reporter_id=current_user.id
        ).first()

        if existing_report:
             return jsonify({"success": True, "message_key": "report_success"}) # Zaten etmişse de başarılı dönelim, spamı önleyelim

        new_report = PostReport(
            post_id=post_id,
            reporter_id=current_user.id,
            reason=reason_key
        )
        db.session.add(new_report)
        db.session.commit()
        
        current_app.logger.info(f"User {current_user.username} reported Post {post_id} for: {reason_key}")
        
        return jsonify({"success": True, "message_key": "report_success"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Raporlama hatası: {e}")
        return jsonify({"error_key": "report_error"}), 500
        
@forum_bp.route("/user/status")
@login_required
def get_user_forum_status():
    """Kullanıcının forumla ilgili durumunu (örn: mola ve sebebi) döndürür."""
    cooldown_end_iso = None
    cooldown_reason_key = None # GÜNCELLENDİ: Sebep artık bir anahtar
    if current_user.post_cooldown_until and current_user.post_cooldown_until > datetime.utcnow():
        cooldown_end_iso = current_user.post_cooldown_until.isoformat() + "Z"
        cooldown_reason_key = current_user.cooldown_reason # Sebebi (anahtarı) gönder

    return jsonify({
        "cooldown_until": cooldown_end_iso,
        "cooldown_reason_key": cooldown_reason_key
    })

# --- FİLİGRAN FONKSİYONLARI ---

def get_image_corner_brightness(image, box):
    """Verilen bir resim ve kutu içindeki alanın ortalama parlaklığını döndürür."""
    try:
        corner = image.crop(box).convert('L')
        stat = ImageStat.Stat(corner)
        return stat.mean[0]
    except Exception:
        return 128

# routes.py'ye bu yeni route'u ekleyin
@forum_bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error_key": "comment_not_found"}), 404
    
    # Yorum sahibi veya kurucu silme yetkisine sahip
    if comment.user_id != current_user.id and current_user.role != UserRole.kurucu:
        return jsonify({"error_key": "comment_delete_unauthorized"}), 403
    
    try:
        post_id = comment.post_id
        db.session.delete(comment)
        
        # Yorum sayacını güncelle
        user_comment_counts = json.loads(current_user.post_comment_counts or '{}')
        if str(post_id) in user_comment_counts:
            user_comment_counts[str(post_id)] = max(0, user_comment_counts[str(post_id)] - 1)
            current_user.post_comment_counts = json.dumps(user_comment_counts)
        
        db.session.commit()
        return jsonify({"success": True, "message_key": "comment_delete_success", "comments_count": Comment.query.filter_by(post_id=post_id).count()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Yorum silinirken hata: {e}")
        return jsonify({"error_key": "comment_delete_error"}), 500

@forum_bp.route("/comments/<int:comment_id>/mute_author", methods=["POST"])
@login_required
def mute_comment_author(comment_id):
    # Sadece kurucu yapabilir
    if current_user.role != UserRole.kurucu:
        return jsonify({"error_key": "mute_unauthorized"}), 403

    data = request.get_json()
    password = data.get('password')
    duration_key = data.get('duration')

    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error_key": "comment_not_found"}), 404
        
    user_to_mute = comment.author
    if not user_to_mute:
        return jsonify({"error_key": "user_not_found"}), 404

    # Kural kontrolleri
    if user_to_mute.id == current_user.id:
        return jsonify({"error_key": "cannot_mute_self"}), 400
    if user_to_mute.role == UserRole.kurucu:
        return jsonify({"error_key": "cannot_mute_kurucu"}), 403

    # Şifre doğrulama
    if not current_user.check_password(password):
        return jsonify({"error_key": "invalid_password"}), 403

    # Süre hesaplama
    duration_map = {
        '10m': timedelta(minutes=10), '30m': timedelta(minutes=30), '1h': timedelta(hours=1),
        '3h': timedelta(hours=3), '5h': timedelta(hours=5), '1d': timedelta(days=1),
        '3d': timedelta(days=3), '5d': timedelta(days=5), '1w': timedelta(weeks=1),
        '1mo': timedelta(days=30), '3mo': timedelta(days=90), '5mo': timedelta(days=150),
        '1y': timedelta(days=365)
    }
    duration_delta = duration_map.get(duration_key)
    if not duration_delta:
        return jsonify({"error_key": "invalid_mute_duration"}), 400
        
    try:
        cooldown_end_time = datetime.utcnow() + duration_delta
        
        user_to_mute.post_cooldown_until = cooldown_end_time
        user_to_mute.cooldown_reason = "mute_reason_comment" # GÜNCELLENDİ: Çeviri anahtarı
        
        # MuteLog'a kayıt
        new_mute_log = MuteLog(
            user_id=user_to_mute.id,
            admin_id=current_user.id,
            mute_end_time=cooldown_end_time,
            reason=f"Yorum üzerinden susturuldu. Yorum ID: {comment_id}, Süre: {duration_key}"
        )
        db.session.add(new_mute_log)

        db.session.commit()
        
        current_app.logger.info(f"KURUCU EYLEMİ: '{current_user.username}', '{user_to_mute.username}' kullanıcısını yorum nedeniyle {duration_key} süreyle susturdu.")
        
        return jsonify({"success": True, "message_key": "mute_success", "username": user_to_mute.username, "duration": duration_key})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Kullanıcı susturma hatası: {e}")
        return jsonify({"error_key": "mute_server_error"}), 500
 
def add_watermark_to_image(image_path):
    """
    Resimlere standart, küçük ve profesyonel 'TOOLVISION' filigranı ekler.
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        txt = Image.new("RGBA", img.size, (255, 255, 255, 0))
        
        font_size = max(15, min(45, int(img.width * 0.02)))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        d = ImageDraw.Draw(txt)
        
        text_bbox = d.textbbox((0, 0), "TOOLVISION", font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        margin = int(min(img.width, img.height) * 0.02)
        x = img.width - text_width - margin
        y = img.height - text_height - margin

        corner_box = (x, y, x + text_width, y + text_height)
        brightness = get_image_corner_brightness(img.convert("RGB"), corner_box)

        if brightness > 127:
            watermark_color = (0, 0, 0, 128)
        else:
            watermark_color = (255, 255, 255, 128)

        d.text((x, y), "TOOLVISION", font=font, fill=watermark_color)

        watermarked = Image.alpha_composite(img, txt)
        watermarked.convert("RGB").save(image_path, format=img.format, quality=95)

    except Exception as e:
        current_app.logger.error(f"Resme filigran eklenirken hata: {e} | Dosya: {image_path}")
        pass

def compress_and_tag_video(video_path):
    """
    Videoyu H.264 (libx264) ile yeniden kodlayarak dosya boyutunu ciddi şekilde düşürür,
    kaliteyi korunmaya yakın tutar (CRF=20, preset=medium), hızlı başlatma için 'faststart' uygular
    ve meta veriye 'TOOLVISION' açıklamasını ekler. Başarılıysa çıktıyı atomik olarak değiştirir.
    """
    try:
        src = Path(video_path)
        tmp = src.with_name(f"{src.stem}_compressed.mp4")

        in_stream = ffmpeg.input(str(src))
        out_stream = ffmpeg.output(
            in_stream,
            str(tmp),
            vcodec='libx264',
            crf=20,
            preset='medium',
            pix_fmt='yuv420p',
            acodec='aac',
            audio_bitrate='192k',
            movflags='+faststart',
            metadata='comment=TOOLVISION'
        )

        ffmpeg.run(out_stream, overwrite_output=True, quiet=True)

        if os.path.exists(tmp):
            os.replace(tmp, src)
            current_app.logger.info(f"Video sıkıştırıldı ve etiketlendi: {video_path}")
        else:
            current_app.logger.error(f"Sıkıştırılmış video oluşturulamadı: {tmp}")
    except ffmpeg.Error as e:
        current_app.logger.error(f"Video sıkıştırma hatası: {e.stderr.decode('utf8')}")
    except Exception as e:
        current_app.logger.error(f"Video sıkıştırma genel hata: {e}")

def generate_video_thumbnail(video_path, thumbnail_path):
    """
    Bir videonun ilk saniyesinden bir kare yakalar ve bunu bir JPEG olarak kaydeder.
    """
    try:
        (
            ffmpeg
            .input(str(video_path), ss=1)
            .output(str(thumbnail_path), vframes=1, qp=4)
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )
        current_app.logger.info(f"Video için kapak fotoğrafı oluşturuldu: {thumbnail_path}")
        return True
    except ffmpeg.Error as e:
        current_app.logger.error(f"Kapak fotoğrafı oluşturulurken ffmpeg hatası: {e.stderr.decode()}")
        return False
    except Exception as e:
        current_app.logger.error(f"Kapak fotoğrafı oluşturulurken genel hata: {e}")
        return False

# --- Arka plan video işleme fonksiyonu (Artık daha hızlı) ---
def process_video_in_background(app, video_path):
    """
    Flask uygulama bağlamında videoyu sıkıştır ve etiketle.
    """
    with app.app_context():
        compress_and_tag_video(video_path)

@forum_bp.route("/posts/create", methods=["POST"])
@login_required
def create_post():
    # --- 0. Katman: Mola Kontrolü ---
    if current_user.post_cooldown_until and current_user.post_cooldown_until > datetime.utcnow():
        return jsonify({
            "error_key": "cooldown_active",
            "cooldown_active": True,
            "cooldown_until": current_user.post_cooldown_until.isoformat() + "Z"
        }), 429

    # --- 1. Katman: Zaman Bazlı Sıklık Kontrolü ---
    if current_user.last_post_time:
        time_since_last_post = (datetime.utcnow() - current_user.last_post_time).total_seconds()
        if time_since_last_post < MIN_POST_INTERVAL_SECONDS:
            wait_time = int(MIN_POST_INTERVAL_SECONDS - time_since_last_post)
            return jsonify({"error_key": "cooldown_too_fast", "wait_time": wait_time}), 429

    # --- Form Verilerini Al ---
    content = request.form.get('content', '').strip()
    media_files = request.files.getlist('media_files')
    video_thumbnails = request.files.getlist('video_thumbnails')
    crop_data_list_json = request.form.get('crop_data', '[]')
    captcha_answer = request.form.get('captcha_answer', None)
    sanitized_content = bleach.clean(content)
    
    captcha_verified = False

    # --- YENİ: Akıllı Filtreleme Mantığı (Güncellendi) ---
    is_spammy = is_content_spammy(sanitized_content)

    if is_spammy:
        # SPAM ALGILANDI - CAPTCHA gerekiyor
        
        # Eğer CAPTCHA cevabı yoksa, CAPTCHA modalı göster
        if not captcha_answer:
            current_app.logger.warning(f"Kullanıcı '{current_user.username}' için spam şüphesi. CAPTCHA isteniyor. Mevcut uyarı sayısı: {current_user.captcha_fail_count}/3")
            return jsonify({
                "requires_captcha": True,
                "message_key": "captcha_required"
            })
        
        # CAPTCHA cevabı var, kontrol et
        correct_answer = session.get('captcha_answer')
        if correct_answer and captcha_answer.lower() == correct_answer.lower():
            # CAPTCHA DOĞRU - sayacı ARTIR ve devam et
            current_user.captcha_fail_count += 1
            current_user.last_captcha_fail_time = datetime.utcnow()
            captcha_verified = True
            session.pop('captcha_answer', None)
            
            current_app.logger.info(f"Kullanıcı '{current_user.username}' CAPTCHA'yı doğru çözdü. Yeni uyarı sayısı: {current_user.captcha_fail_count}/3")
        else:
            # CAPTCHA YANLIŞ - sayacı ARTIR ve hata döndür
            current_user.captcha_fail_count += 1
            current_user.last_captcha_fail_time = datetime.utcnow()
            db.session.commit() # Sayacı kaydet
            
            current_app.logger.warning(f"Kullanıcı '{current_user.username}' CAPTCHA'yı yanlış çözdü. Yeni uyarı sayısı: {current_user.captcha_fail_count}/3")
            return jsonify({"error_key": "captcha_incorrect"}), 400
        
        # 3. hak kontrolü (doğru veya yanlış fark etmez)
        if current_user.captcha_fail_count >= 3:
            # 3 HAK DOLDU - mola ver
            cooldown_end_time = datetime.utcnow() + timedelta(hours=3)
            current_user.post_cooldown_until = cooldown_end_time
            current_user.cooldown_reason = "mute_reason_spam" # GÜNCELLENDİ: Çeviri anahtarı
            current_user.captcha_fail_count = 0 # Sayacı sıfırla
            db.session.commit()
            
            current_app.logger.warning(f"Kullanıcı '{current_user.username}' 3 spam uyarısına ulaştı ve 3 saat mola aldı.")
            return jsonify({
                "error_key": "cooldown_spam_limit",
                "cooldown_active": True,
                "cooldown_until": cooldown_end_time.isoformat() + "Z"
            }), 429
    
    # --- BURADAN SONRASI, GÖNDERİNİN TEMİZ OLDUĞU VEYA CAPTCHA'NIN DOĞRULANDIĞI DURUMDUR ---
    
    try:
        crop_data_list = json.loads(crop_data_list_json)
    except json.JSONDecodeError:
        return jsonify({"error_key": "invalid_crop_data"}), 400

    if not sanitized_content and not media_files:
        return jsonify({"error_key": "post_content_or_media_required"}), 400

    if len(sanitized_content) > MAX_CONTENT_LENGTH_CHARS:
        return jsonify({"error_key": "content_too_long", "limit": MAX_CONTENT_LENGTH_CHARS}), 400

    # Dosyaları türlerine göre ayır
    images, videos, audios, documents = [], [], [], []
    
    for file in media_files:
        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                images.append(file)
            elif ext in VIDEO_EXTENSIONS:
                videos.append(file)
            elif ext in AUDIO_EXTENSIONS:
                audios.append(file)
            elif ext in DOCUMENT_EXTENSIONS:
                documents.append(file)
            else:
                return jsonify({"error_key": "unsupported_file_type", "filename": file.filename}), 400

    # --- YENİ VE DAHA KATI KONTROL MANTIĞI ---
    media_types_count = sum([1 for media_list in [videos, audios, documents] if media_list])
    if media_types_count > 1:
        return jsonify({"error_key": "media_mix_error_1"}), 400
    if media_types_count > 0 and images:
        return jsonify({"error_key": "media_mix_error_2"}), 400
    # --- KONTROL MANTIĞI SONU ---

    # Resim kontrolleri
    if images:
        if len(images) > MAX_IMAGE_COUNT:
            return jsonify({"error_key": "image_count_limit", "limit": MAX_IMAGE_COUNT}), 413
        
        total_image_size = 0
        for img in images:
            img.seek(0, os.SEEK_END)
            file_size = img.tell()
            if file_size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                return jsonify({"error_key": "image_size_limit", "filename": img.filename, "limit": MAX_IMAGE_SIZE_MB}), 413
            total_image_size += file_size
            img.seek(0)
        
        if total_image_size > MAX_TOTAL_IMAGE_SIZE_MB * 1024 * 1024:
            return jsonify({"error_key": "image_total_size_limit", "limit": MAX_TOTAL_IMAGE_SIZE_MB}), 413

    # Video kontrolleri
    if videos:
        if len(videos) > MAX_VIDEO_COUNT:
            return jsonify({"error_key": "video_count_limit", "limit": MAX_VIDEO_COUNT}), 413
        
        video_file = videos[0]
        video_file.seek(0, os.SEEK_END)
        if video_file.tell() > MAX_VIDEO_SIZE_MB * 1024 * 1024:
            return jsonify({"error_key": "video_size_limit", "limit": MAX_VIDEO_SIZE_MB}), 413
        video_file.seek(0)

    # Ses kontrolleri
    if audios:
        if len(audios) > MAX_AUDIO_COUNT:
            return jsonify({"error_key": "audio_count_limit", "limit": MAX_AUDIO_COUNT}), 413
        
        audio_file = audios[0]
        audio_file.seek(0, os.SEEK_END)
        if audio_file.tell() > MAX_AUDIO_SIZE_MB * 1024 * 1024:
            return jsonify({"error_key": "audio_size_limit", "limit": MAX_AUDIO_SIZE_MB}), 413
        audio_file.seek(0)

    # Belge kontrolleri
    if documents:
        if len(documents) > MAX_DOCUMENT_COUNT:
            return jsonify({"error_key": "doc_count_limit", "limit": MAX_DOCUMENT_COUNT}), 413
        
        doc_file = documents[0]
        doc_file.seek(0, os.SEEK_END)
        if doc_file.tell() > MAX_DOCUMENT_SIZE_MB * 1024 * 1024:
            return jsonify({"error_key": "doc_size_limit", "limit": MAX_DOCUMENT_SIZE_MB}), 413
        doc_file.seek(0)

    # --- Dosya Kaydetme ve Veritabanı İşlemleri ---
    new_post = Post(content=sanitized_content, user_id=current_user.id)
    db.session.add(new_post)
    
    try:
        image_crop_index = 0
        video_thumb_index = 0
        files_to_process = images + videos + audios + documents
        
        for file in files_to_process:
            safe_original_filename = secure_filename(file.filename)
            extension = safe_original_filename.rsplit('.', 1)[1].lower()
            
            unique_id = uuid.uuid4().hex[:8]
            unique_filename_base = f"toolvision_{unique_id}_{Path(safe_original_filename).stem}"

            file_type = 'image' if extension in IMAGE_EXTENSIONS else \
                        'video' if extension in VIDEO_EXTENSIONS else \
                        'audio' if extension in AUDIO_EXTENSIONS else \
                        'document' if extension in DOCUMENT_EXTENSIONS else 'file'
            
            save_path_dir = Path(current_app.config['USER_MEDIA_FOLDER']) / file_type
            save_path_dir.mkdir(parents=True, exist_ok=True)
            
            unique_filename = f"{unique_filename_base}.{extension}"
            save_path_file = save_path_dir / unique_filename

            thumbnail_url_for_db = None

            if file_type == 'image':
                # --- YENİ AKILLI KIRPMA MANTIĞI BURADA ---
                crop_data_for_this_image = None
                if image_crop_index < len(crop_data_list) and crop_data_list[image_crop_index]:
                    crop_data_for_this_image = crop_data_list[image_crop_index]
                
                # Eğer frontend'den kırpma verisi gelmediyse, resmi ortadan kendimiz kırp
                else:
                    try:
                        with Image.open(file) as img:
                            width, height = img.size
                            # Resmin kısa kenarını bul
                            min_dim = min(width, height)
                            # Ortadan kare bir alan belirle
                            left = (width - min_dim) / 2
                            top = (height - min_dim) / 2
                            right = (width + min_dim) / 2
                            bottom = (height + min_dim) / 2
                            
                            crop_data_for_this_image = {
                                "x": int(left),
                                "y": int(top),
                                "width": int(min_dim),
                                "height": int(min_dim)
                            }
                            current_app.logger.info(f"'{safe_original_filename}' için kırpma verisi yoktu, otomatik olarak ortalandı.")
                    except Exception as e:
                        current_app.logger.error(f"Otomatik kırpma sırasında hata: {e}")
                        # Hata olursa kırpma verisi None kalacak ve orijinal resim kaydedilecek
                        crop_data_for_this_image = None
                
                # Kırpma işlemini yap
                crop_data_as_json = json.dumps(crop_data_for_this_image) if crop_data_for_this_image else None

                if crop_data_as_json:
                    file.seek(0) # Stream'i başa sar
                    crop_success = crop_image(
                        image_stream=file,
                        crop_data_json=crop_data_as_json,
                        save_path=str(save_path_file)
                    )
                    if not crop_success:
                        file.seek(0)
                        file.save(save_path_file)
                else:
                    file.seek(0)
                    file.save(save_path_file)
                # --- AKILLI KIRPMA MANTIĞI SONU ---
                
                add_watermark_to_image(str(save_path_file))
                image_crop_index += 1
            
            elif file_type == 'video':
                file.save(save_path_file)

                thumbnail_dir = save_path_dir / 'thumbnails'
                thumbnail_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_filename = f"{unique_filename_base}.jpg"
                thumbnail_save_path = thumbnail_dir / thumbnail_filename

                if video_thumb_index < len(video_thumbnails):
                    thumb_file = video_thumbnails[video_thumb_index]
                    try:
                        thumb_file.seek(0)
                    except Exception:
                        pass
                    thumb_file.save(thumbnail_save_path)
                    thumbnail_url_for_db = f"{file_type}/thumbnails/{thumbnail_filename}"
                    video_thumb_index += 1
                else:
                    if generate_video_thumbnail(save_path_file, thumbnail_save_path):
                        thumbnail_url_for_db = f"{file_type}/thumbnails/{thumbnail_filename}"

                # Video işleme
                app_context = current_app._get_current_object()
                video_thread = threading.Thread(
                    target=process_video_in_background,
                    args=(app_context, str(save_path_file))
                )
                video_thread.daemon = True
                video_thread.start()
            
            else:
                file.save(save_path_file)

            new_media = PostMedia(
                post=new_post,
                file_url=f"{file_type}/{unique_filename}",
                file_type=file_type,
                original_filename=file.filename,
                thumbnail_url=thumbnail_url_for_db
            )
            db.session.add(new_media)
        
        # Başarılı gönderiden sonra kullanıcının son gönderi zamanını güncelle
        current_user.last_post_time = datetime.utcnow()
        db.session.add(current_user)

        db.session.commit()
        return jsonify({"success": True, "message_key": "post_create_success", "post_id": new_post.id}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Gönderi oluşturulurken hata (İç Try): {e}\n{traceback.format_exc()}")
        return jsonify({"error_key": "post_create_error"}), 500

# --- DİĞER ROTALAR ---

@forum_bp.route("/")
@login_required
def forum_page():
    """
    Ana forum sayfasını render eder. 
    Kullanıcı giriş yaptığında ilk göreceği sayfadır.
    """
    # forum.html şablonunu render et ve şablona mevcut kullanıcı bilgilerini gönder.
    return render_template("forum.html", user=current_user)
    
@forum_bp.route("/view/post/<int:post_id>")
@login_required
def view_single_post(post_id):
    """
    Tek bir gönderiyi görüntülemek için forum sayfasını render eder.
    Bu, paylaşılabilir linkler için kullanılır.
    """
    # Gönderinin gerçekten var olup olmadığını kontrol edelim
    post = db.session.get(Post, post_id)
    if not post:
        flash("Gönderi bulunamadı veya silinmiş.", "danger")
        return redirect(url_for('forum.forum_page'))
            
    # forum.html şablonunu render et, kullanıcıyı ve post_id'yi geçir
    # JavaScript (forum_core.js) bu 'single_post_id' değişkenini arayacak
    return render_template("forum.html", user=current_user, single_post_id=post_id)
    
@forum_bp.route("/posts/<int:post_id>/likers", methods=["GET"])
@login_required
def get_post_likers(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error_key": "post_not_found"}), 404
    likes = Like.query.filter_by(post_id=post.id).order_by(Like.id.asc()).all()
    likers_list = []
    for like in likes:
        user = like.author
        likers_list.append({
            "id": user.id, "username": user.username,
            "profile_pic": user.profile_pic_url or url_for('static', filename='images/free.png'),
            "role": user.role.value
        })
    return jsonify(likers_list)

@forum_bp.route("/posts/all_with_like_status", methods=["GET"])
@login_required
def get_all_posts_with_like_status():
    try:
        user_likes = {like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()}
        posts_query = Post.query.order_by(Post.pinned.desc(), Post.timestamp.desc()).all()
        posts_list = []
        for post in posts_query:
            # Hide posts that have an approved report
            if PostReport.query.filter_by(post_id=post.id, decision='approved').first():
                continue
            first_liker_name = None
            first_like = post.likes.order_by(Like.id.asc()).first()
            if first_like:
                first_liker_name = first_like.author.username

            media_list = []
            for media in post.media_files:
                media_url = url_for('serve_user_media', filename=media.file_url)
                thumbnail_url = (
                    url_for('serve_user_media', filename=media.thumbnail_url)
                    if media.thumbnail_url
                    else url_for('static', filename='images/video_1_thumbnail.jpg')
                )
                
                media_list.append({
                    "url": media_url, 
                    "type": media.file_type,
                    "original_name": media.original_filename,
                    "thumbnail_url": thumbnail_url
                })

            # Aggregate reactions
            counts = {}
            for r in post.reactions.all():
                counts[r.type] = counts.get(r.type, 0) + 1
            my_reaction = None
            mr = Reaction.query.filter_by(user_id=current_user.id, post_id=post.id).first()
            if mr:
                my_reaction = mr.type

            posts_list.append({
                "id": post.id, "content": post.content,
                "timestamp": post.timestamp.isoformat() + "Z",
                "edited_at": post.edited_at.isoformat() + "Z" if post.edited_at else None,
                "author": { "id": post.user_id, "username": post.user.username,
                    "profile_pic": post.user.profile_pic_url or url_for('static', filename='images/free.png'),
                    "role": post.user.role.value },
                    "selected_frame_id": getattr(post.user, 'selected_frame_id', None),
                "media_files": media_list, "likes_count": post.likes.count(),
                "comments_count": post.comments.count(), "current_user_liked": post.id in user_likes,
                "first_liker_name": first_liker_name,
                "pinned": post.pinned,
                "pinned_by_user_id": post.pinned_by_user_id,
                "reaction_counts": counts,
                "current_user_reaction": my_reaction
            })
        return jsonify(posts_list)
    except Exception as e:
        current_app.logger.error(f"Gönderiler alınırken hata: {e}")
        return jsonify({"error_key": "post_fetch_error"}), 500

@forum_bp.route("/posts/<int:post_id>", methods=["GET"])
@login_required
def get_single_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error_key": "post_not_found"}), 404
    if PostReport.query.filter_by(post_id=post.id, decision='approved').first():
        return jsonify({"error_key": "post_not_found"}), 404

    user_liked_post = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first() is not None
    first_liker_name = None
    first_like = post.likes.order_by(Like.id.asc()).first()
    if first_like:
        first_liker_name = first_like.author.username
        
    media_list = []
    for media in post.media_files:
        media_url = url_for('serve_user_media', filename=media.file_url)
        thumbnail_url = (
            url_for('serve_user_media', filename=media.thumbnail_url)
            if media.thumbnail_url
            else url_for('static', filename='images/video_1_thumbnail.jpg')
        )
        
        media_list.append({
            "url": media_url, 
            "type": media.file_type, 
            "original_name": media.original_filename,
            "thumbnail_url": thumbnail_url
        })

    # Aggregate reactions
    counts = {}
    for r in post.reactions.all():
        counts[r.type] = counts.get(r.type, 0) + 1
    my_reaction = None
    mr = Reaction.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    if mr:
        my_reaction = mr.type

    post_data = {
        "id": post.id, "content": post.content,
        "timestamp": post.timestamp.isoformat() + "Z",
        "edited_at": post.edited_at.isoformat() + "Z" if post.edited_at else None,
        "author": { "id": post.user_id, "username": post.user.username,
            "profile_pic": post.user.profile_pic_url or url_for('static', filename='images/free.png'),
            "role": post.user.role.value },
        "media_files": media_list, "likes_count": post.likes.count(),
        "comments_count": post.comments.count(), "current_user_liked": user_liked_post,
        "first_liker_name": first_liker_name,
        "pinned": post.pinned,
        "pinned_by_user_id": post.pinned_by_user_id,
        "reaction_counts": counts,
        "current_user_reaction": my_reaction
    }
    return jsonify(post_data)

@forum_bp.route("/posts/<int:post_id>/like", methods=["POST"])
@login_required
def toggle_like_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error_key": "post_not_found"}), 404
    like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    try:
        if like:
            db.session.delete(like)
            liked = False
        else:
            new_like = Like(user_id=current_user.id, post_id=post.id)
            db.session.add(new_like)
            liked = True
        db.session.commit()
        first_liker_name = None
        first_like = post.likes.order_by(Like.id.asc()).first()
        if first_like:
            first_liker_name = first_like.author.username
        return jsonify({ "success": True, "likes_count": post.likes.count(), 
                         "user_liked": liked, "first_liker_name": first_liker_name })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Beğeni işlemi sırasında hata: {e}")
        return jsonify({"error_key": "like_error"}), 500

@forum_bp.route("/posts/<int:post_id>/comment", methods=["POST"])
@login_required
def create_comment(post_id):
    post = db.session.get(Post, post_id)
    if not post: 
        return jsonify({"error_key": "post_not_found"}), 404
    
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({"error_key": "comment_content_missing"}), 400
        
    content = data.get('content', '').strip()

    if not content: 
        return jsonify({"error_key": "comment_content_empty"}), 400
    
    # --- YENİ: YORUM LİMİT KONTROLÜ ---
    MAX_COMMENTS_PER_POST = 30
    
    # Kullanıcının bu posta yaptığı yorum sayısını al
    user_comment_counts = json.loads(current_user.post_comment_counts or '{}')
    current_count = user_comment_counts.get(str(post_id), 0)
    
    if current_count >= MAX_COMMENTS_PER_POST:
        return jsonify({"error_key": "comment_limit_reached", "limit": MAX_COMMENTS_PER_POST}), 400
    # --- LİMİT KONTROLÜ SONU ---
    
    sanitized_content = bleach.clean(content)
    
    try:
        new_comment = Comment(
            content=sanitized_content, 
            post_id=post.id, 
            user_id=current_user.id, 
            author=current_user
        )
        db.session.add(new_comment)
        
        # --- YENİ: YORUM SAYACINI GÜNCELLE ---
        user_comment_counts[str(post_id)] = current_count + 1
        current_user.post_comment_counts = json.dumps(user_comment_counts)
        # --- SAYAÇ GÜNCELLEME SONU ---
        
        db.session.commit()
        
        comment_data = { 
            "id": new_comment.id, 
            "content": new_comment.content, 
            "timestamp": new_comment.timestamp.isoformat() + "Z",
            "author": { 
                "id": new_comment.user_id, 
                "username": new_comment.author.username,
                "profile_pic": new_comment.author.profile_pic_url or url_for('static', filename='images/free.png'),
                "role": new_comment.author.role.value 
            } 
        }
        return jsonify({ 
            "success": True, 
            "comment": comment_data, 
            "comments_count": post.comments.count(),
            "user_comment_count": user_comment_counts[str(post_id)]  # Frontend için
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Yorum oluşturma sırasında hata: {e}")
        return jsonify({"error_key": "comment_create_error"}), 500

@forum_bp.route("/posts/<int:post_id>/comments", methods=["GET"])
@login_required
def get_comments(post_id):
    post = db.session.get(Post, post_id)
    if not post: return jsonify({"error_key": "post_not_found"}), 404
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.id.asc()).all()
    comments_list = []
    for comment in comments:
        comments_list.append({
            "id": comment.id, "content": comment.content,
            "timestamp": comment.timestamp.isoformat() + "Z",
            "author": { "id": comment.user_id, "username": comment.author.username,
                "profile_pic": comment.author.profile_pic_url or url_for('static', filename='images/free.png'),
                "role": comment.author.role.value }
        })
    return jsonify(comments_list)

@forum_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if not post: return jsonify({"error_key": "post_not_found"}), 404
    
    # --- YENİ VE DOĞRU KONTROL MANTIĞI ---
    
    is_owner = post.user_id == current_user.id
    is_kurucu = current_user.role == UserRole.kurucu
    
    # 1. Yetki Kontrolü: Ya sahip olmalı ya da kurucu
    if not is_owner and not is_kurucu:
        return jsonify({"error_key": "delete_unauthorized"}), 403
        
    # 2. Kurucu Şifre Kontrolü (EKSİK OLAN KISIM BURASIYDI)
    if is_kurucu:
        # Eğer silen kişi kurucu ise, JS'den (forum_interactions.js)
        # JSON içinde bir şifre gelmesi zorunludur.
        data = request.get_json()
        if not data:
            # Bu durum, JS'nin JSON göndermemesi durumunda oluşur.
            # Kurucu senaryosunda bu bir hatadır.
            return jsonify({"error_key": "delete_captcha_required"}), 400
        
        password = data.get('password')
        if not password or not current_user.check_password(password):
            # Şifre yanlışsa veya yoksa işlemi reddet
            return jsonify({"error_key": "delete_captcha_incorrect"}), 403
    
    # 3. Silme İşlemi
    # Buraya gelindiyse ya şifresini doğrulayan bir kurucudur
    # ya da şifreye ihtiyacı olmayan normal bir gönderi sahibidir.
    try:
        for media in post.media_files:
            if media.file_url:
                file_path = Path(current_app.config['USER_MEDIA_FOLDER']) / media.file_url
                if file_path.exists(): file_path.unlink()
            if media.thumbnail_url:
                thumbnail_path = Path(current_app.config['USER_MEDIA_FOLDER']) / media.thumbnail_url
                if thumbnail_path.exists(): thumbnail_path.unlink()
        
        # Gönderiye bağlı tüm medya, beğeni ve yorumları da sil (Cascade ayarlıysa)
        db.session.delete(post) 
        db.session.commit()
        return jsonify({"success": True, "message_key": "post_delete_success"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Gönderi silinirken hata: {e}")
        return jsonify({"error_key": "post_delete_error"}), 500
        
@forum_bp.route("/posts/<int:post_id>/edit", methods=["POST"])
@login_required
def edit_post(post_id):
    post = db.session.get(Post, post_id)
    if not post: return jsonify({"error_key": "post_not_found"}), 404
    if post.user_id != current_user.id: return jsonify({"error_key": "edit_unauthorized"}), 403
    data = request.get_json()
    if not data or 'content' not in data: return jsonify({"error_key": "edit_content_missing"}), 400
    content = data.get('content', '').strip()
    if not content: return jsonify({"error_key": "edit_content_empty"}), 400
    sanitized_content = bleach.clean(content)
    if len(sanitized_content) > MAX_CONTENT_LENGTH_CHARS:
        return jsonify({"error_key": "edit_too_long", "limit": MAX_CONTENT_LENGTH_CHARS}), 400
    try:
        post.content = sanitized_content
        post.edited_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"success": True, "message_key": "post_edit_success", "post_id": post.id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Gönderi düzenlenirken hata: {e}")
        return jsonify({"error_key": "post_edit_error"}), 500

@forum_bp.route("/users/<int:user_id>/mute", methods=["POST"])
@login_required
def mute_user(user_id):
    # 1. Yetki Kontrolü: Sadece Kurucu yapabilir
    if current_user.role != UserRole.kurucu:
        return jsonify({"error_key": "mute_unauthorized"}), 403

    # 2. Veri Alımı ve Doğrulama
    data = request.get_json()
    password = data.get('password')
    duration_key = data.get('duration')

    user_to_mute = db.session.get(User, user_id)
    if not user_to_mute:
        return jsonify({"error_key": "user_not_found"}), 404
        
    # 3. Kural Kontrolleri
    if user_to_mute.id == current_user.id:
        return jsonify({"error_key": "cannot_mute_self"}), 400
    if user_to_mute.role == UserRole.kurucu:
        return jsonify({"error_key": "cannot_mute_kurucu"}), 403

    # 4. Şifre Doğrulama
    if not current_user.check_password(password):
        return jsonify({"error_key": "invalid_password"}), 403

    # 5. Süre Hesaplama
    duration_map = {
        '10m': timedelta(minutes=10), '30m': timedelta(minutes=30), '1h': timedelta(hours=1),
        '3h': timedelta(hours=3), '5h': timedelta(hours=5), '1d': timedelta(days=1),
        '3d': timedelta(days=3), '5d': timedelta(days=5), '1w': timedelta(weeks=1),
        '1mo': timedelta(days=30), '3mo': timedelta(days=90), '5mo': timedelta(days=150),
        '1y': timedelta(days=365)
    }
    duration_delta = duration_map.get(duration_key)
    if not duration_delta:
        return jsonify({"error_key": "invalid_mute_duration"}), 400
        
    # 6. Veritabanını Güncelleme ve Loglama
    try:
        cooldown_end_time = datetime.utcnow() + duration_delta
        
        # --- ESKİ KISIM (DEĞİŞMEDİ) ---
        user_to_mute.post_cooldown_until = cooldown_end_time
        user_to_mute.cooldown_reason = "mute_reason_post" # GÜNCELLENDİ: Çeviri anahtarı
        
        # --- YENİ EKLENEN KISIM ---
        # Artık admin panelinin görebilmesi için MuteLog'a kayıt oluşturuyoruz.
        new_mute_log = MuteLog(
            user_id=user_to_mute.id,
            admin_id=current_user.id,
            mute_end_time=cooldown_end_time,
            reason=f"Forum gönderisi üzerinden susturuldu. Süre: {duration_key}"
        )
        db.session.add(new_mute_log)
        # --- YENİ KISIM SONU ---

        db.session.commit()
        
        current_app.logger.info(f"KURUCU EYLEMİ: '{current_user.username}', '{user_to_mute.username}' kullanıcısını {duration_key} süreyle susturdu.")
        
        return jsonify({"success": True, "message_key": "mute_success", "username": user_to_mute.username, "duration": duration_key})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Kullanıcı susturma hatası: {e}")
        return jsonify({"error_key": "mute_server_error"}), 500

@forum_bp.route("/users/<int:user_id>/posts", methods=["GET"])
@login_required
def get_user_posts(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error_key": "user_not_found"}), 404
    posts_query = Post.query.filter(Post.user_id == user.id).order_by(Post.timestamp.desc()).all()
    user_likes = {like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()}
    posts_list = []
    for post in posts_query:
        if PostReport.query.filter_by(post_id=post.id, decision='approved').first():
            continue
        first_liker_name = None
        first_like = post.likes.order_by(Like.id.asc()).first()
        if first_like:
            first_liker_name = first_like.author.username

        media_list = []
        for media in post.media_files:
            media_url = url_for('serve_user_media', filename=media.file_url)
            thumbnail_url = (
                url_for('serve_user_media', filename=media.thumbnail_url)
                if media.thumbnail_url
                else url_for('static', filename='images/video_1_thumbnail.jpg')
            )
            
            media_list.append({
                "url": media_url, 
                "type": media.file_type,
                "original_name": media.original_filename,
                "thumbnail_url": thumbnail_url
            })

        posts_list.append({
            "id": post.id, "content": post.content,
            "timestamp": post.timestamp.isoformat() + "Z",
            "edited_at": post.edited_at.isoformat() + "Z" if post.edited_at else None,
            "author": { "id": post.user_id, "username": post.user.username,
                "profile_pic": post.user.profile_pic_url or url_for('static', filename='images/free.png'),
                "role": post.user.role.value },
            "media_files": media_list, "likes_count": post.likes.count(),
            "comments_count": post.comments.count(), "current_user_liked": post.id in user_likes,
            "first_liker_name": first_liker_name,
            "pinned": post.pinned,
            "pinned_by_user_id": post.pinned_by_user_id
        })
    return jsonify(posts_list)

@forum_bp.route("/user_media/<path:filename>")
@login_required
def serve_user_media(filename):
    return send_from_directory(current_app.config['USER_MEDIA_FOLDER'], filename)

@forum_bp.route("/search", methods=["GET"])
@login_required
def search_posts():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error_key": "search_query_empty"}), 400
    if len(query) < 2:
        return jsonify({"error_key": "search_query_too_short"}), 400

    try:
        search_terms = query.split()
        conditions = []
        for term in search_terms:
            conditions.append(Post.content.ilike(f'%{term}%'))
        
        posts_query = Post.query.filter(or_(*conditions)).order_by(Post.timestamp.desc()).all()
        user_likes = {like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()}
        posts_list = []
        for post in posts_query:
            if PostReport.query.filter_by(post_id=post.id, decision='approved').first():
                continue
            first_liker_name = None
            first_like = post.likes.order_by(Like.id.asc()).first()
            if first_like:
                first_liker_name = first_like.author.username

            media_list = []
            for media in post.media_files:
                media_url = url_for('serve_user_media', filename=media.file_url)
                thumbnail_url = (
                    url_for('serve_user_media', filename=media.thumbnail_url)
                    if media.thumbnail_url
                    else url_for('static', filename='images/video_1_thumbnail.jpg')
                )
                
                media_list.append({
                    "url": media_url, 
                    "type": media.file_type,
                    "original_name": media.original_filename,
                    "thumbnail_url": thumbnail_url
                })

            posts_list.append({
                "id": post.id, "content": post.content,
                "timestamp": post.timestamp.isoformat() + "Z",
                "edited_at": post.edited_at.isoformat() + "Z" if post.edited_at else None,
                "author": { "id": post.user_id, "username": post.user.username,
                    "profile_pic": post.user.profile_pic_url or url_for('static', filename='images/free.png'),
                    "role": post.user.role.value },
                "media_files": media_list, "likes_count": post.likes.count(),
                "comments_count": post.comments.count(), "current_user_liked": post.id in user_likes,
                "first_liker_name": first_liker_name,
                "pinned": post.pinned
            })
        return jsonify(posts_list)
    except Exception as e:
        current_app.logger.error(f"Arama sırasında hata: {e}")
        return jsonify({"error_key": "search_error"}), 500
@forum_bp.route("/posts/<int:post_id>/pin", methods=["POST"])
@login_required
def pin_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error_key": "post_not_found"}), 404
    if post.pinned:
        return jsonify({"error_key": "post_already_pinned"}), 400
    role = current_user.role
    allowed_roles = [UserRole.premium, UserRole.dev, UserRole.kurucu, UserRole.caylak_admin, UserRole.usta_admin]
    if role not in allowed_roles:
        return jsonify({"error_key": "pin_unauthorized"}), 403
    try:
        limit_map = {UserRole.premium: 20, UserRole.dev: 70}
        if role in limit_map:
            user_limit = limit_map[role]
            if getattr(current_user, 'pin_count', 0) >= user_limit:
                return jsonify({"error_key": "pin_limit_reached"}), 403
        post.pinned = True
        post.pinned_by_user_id = current_user.id
        if role in limit_map:
            current_user.pin_count = (getattr(current_user, 'pin_count', 0) or 0) + 1
        db.session.commit()
        return jsonify({"success": True, "pinned": True, "pinned_by_user_id": post.pinned_by_user_id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Pin işlemi sırasında hata: {e}")
        return jsonify({"error_key": "post_edit_error"}), 500

@forum_bp.route("/posts/<int:post_id>/unpin", methods=["POST"])
@login_required
def unpin_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error_key": "post_not_found"}), 404
    role = current_user.role
    allowed_roles = [UserRole.premium, UserRole.dev, UserRole.kurucu, UserRole.caylak_admin, UserRole.usta_admin]
    if role not in allowed_roles:
        return jsonify({"error_key": "pin_unauthorized"}), 403
    # Only founder or the user who pinned it can unpin
    is_founder = role == UserRole.kurucu
    is_pin_owner = post.pinned_by_user_id == current_user.id
    if not is_founder and not is_pin_owner:
        return jsonify({"error_key": "unpin_unauthorized"}), 403
    try:
        post.pinned = False
        db.session.commit()
        return jsonify({"success": True, "pinned": False})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unpin işlemi sırasında hata: {e}")
        return jsonify({"error_key": "post_edit_error"}), 500
@forum_bp.route("/posts/<int:post_id>/react", methods=["POST"])
@login_required
def react_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"error_key": "post_not_found"}), 404
    data = request.get_json() or {}
    rtype = data.get('type')
    allowed = {'like','heart','smile','surprise','sad','angry','remove'}
    if rtype not in allowed:
        return jsonify({"error_key":"reaction_type_invalid"}), 400
    try:
        current = Reaction.query.filter_by(user_id=current_user.id, post_id=post.id).first()
        if rtype == 'remove':
            if current:
                db.session.delete(current)
        else:
            if current:
                current.type = rtype
            else:
                db.session.add(Reaction(user_id=current_user.id, post_id=post.id, type=rtype))
        db.session.commit()

        counts = {}
        for r in post.reactions.all():
            counts[r.type] = counts.get(r.type, 0) + 1
        return jsonify({"success": True, "reaction_counts": counts, "current_user_reaction": (None if rtype=='remove' else rtype)})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reaction error: {e}")
        return jsonify({"error_key": "reaction_error"}), 500