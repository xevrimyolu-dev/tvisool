import os
import uuid
import shutil
import traceback
import secrets
import logging
import json
import struct
from user_agents import parse
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
import re
from flask_wtf.csrf import CSRFProtect
import secrets
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from werkzeug.middleware.proxy_fix import ProxyFix
from models import MuteLog
from sqlalchemy.orm import joinedload
import requests
from dotenv import load_dotenv
load_dotenv()

from flask import (Flask, request, jsonify, send_from_directory,
                   render_template, redirect, url_for, flash, session, send_file, g, current_app, redirect, url_for)
from flask_login import (LoginManager, current_user, login_user,
                       logout_user, login_required)
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash
from flask_limiter import Limiter
from extensions import db
from flask_limiter.util import get_remote_address
from sqlalchemy import func, or_, desc
from flask_apscheduler import APScheduler
from apscheduler.jobstores.base import ConflictingIdError

from config import Config
from frames import FRAMES, get_user_frames, set_user_frames
from models import User, ActivityLog, TemporaryFile, PageVisitLog, UserRole, Permission, VideoLog, FeatureUsageLog, PurchaseIntent, PostReport
from forum.models import Post
from sqlalchemy.orm import joinedload
import forum.models
from utils import record_log

from decorators import admin_required, usta_admin_required, kurucu_required, permission_required

import pak_parser
import repacker_engine
import obb_repack
import obb_unpack

logging.basicConfig(
    filename='activity.log',
    level=logging.INFO,
    format='[%(asctime)s] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_EMAIL_DOMAINS = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "mail.com", "yandex.com", "protonmail.com"}

MAX_PROFILE_PIC_SIZE_BYTES = 10 * 1024 * 1024

RECEIPT_UPLOAD_FOLDER = Path('static/receipt')
MAX_RECEIPT_SIZE_BYTES = 10 * 1024 * 1024 # 10 MB
ALLOWED_RECEIPT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_host=1, x_proto=1)
app.config.from_object(Config)

csrf = CSRFProtect(app)

DEVICE_LIMIT = 2

SUBSCRIPTION_DATA = {
    'free': {
        'features': {
            'pak_unpack_limit': '20 MB',
            'pak_repack_limit': '20 MB',
            'obb_unpack_limit': '200 MB',
            'obb_repack_limit': '170 MB',
            'daily_limit': '7 İşlem / 3 Saat Bekleme',
            'config_features': '1 Config Özelliği',
            'coding_videos': '1 Kodlama Videosu'
        }
    },
    'premium': {
        'features': {
            'pak_unpack_limit': '100 MB',
            'pak_repack_limit': '100 MB',
            'obb_unpack_limit': '900 MB',
            'obb_repack_limit': '870 MB',
            'daily_limit': '70 İşlem / 1 Saat Bekleme',
            'config_features': '12 Config Özelliği',
            'coding_videos': '12 Kodlama Videosu'
        },
        'prices': {
            '1w': [2.04, 50, 2.36, 208],
            '1m': [4.90, 120, 5.66, 500],
            '3m': [15.12, 370, 17.47, 1542],
            '5m': [20.43, 500, 23.60, 2083],
            '1y': [24.52, 600, 28.33, 2500],
            'permanent': [57.21, 1400, 66.10, 5833]
        },
        'old_prices': {
            '1w': [11.99, 399, 12.84, 1593],
            '1m': [16.98, 598, 17.32, 1798],
            '3m': [45.97, 1793, 49.99, 4231],
            '5m': [74.03, 2979, 80.97, 7499],
            '1y': [155.99, 6994, 179.88, 15979],
            'permanent': [310.93, 13893, 349.92, 31699]
        }
    },
    'dev': {
        'features': {
            'pak_unpack_limit': '6 GB',
            'pak_repack_limit': '5 GB',
            'obb_unpack_limit': '7 GB',
            'obb_repack_limit': '6 GB',
            'daily_limit': 'Sınırsız',
            'config_features': 'Tüm Config Özellikleri',
            'coding_videos': 'Tüm Videolar + Özel İçerikler'
        },
        'prices': {
            '1w': [3.27, 80, 3.78, 333],
            '1m': [6.54, 160, 7.55, 667],
            '3m': [16.76, 410, 19.36, 1708],
            '5m': [24.52, 600, 28.33, 2500],
            '1y': [32.69, 800, 37.77, 3333],
            'permanent': [65.39, 1600, 75.54, 6667]
        },
        'old_prices': {
            '1w': [13.99, 459, 14.99, 1683],
            '1m': [19.98, 679, 18.54, 1883],
            '3m': [49.97, 1949, 53.97, 4699],
            '5m': [78.42, 3148, 89.37, 8021],
            '1y': [176.88, 7179, 201.97, 17982],
            'permanent': [399.99, 14158, 459.99, 39995]
        }
    }
}

ROLE_LIMITS = {
    UserRole.ücretsiz: {
        'pak_max_size': 20 * 1024 * 1024,                  # 20 MB
        'obb_max_size': 2 * 1024 * 1024 * 1024,            # 2 GB
        'repack_pak_modified_max_size': 20 * 1024 * 1024,  # 20 MB
        'repack_obb_modified_max_size': 100 * 1024 * 1024, # 100 MB
    },
    UserRole.premium: {
        'pak_max_size': 100 * 1024 * 1024,                 # 100 MB
        'obb_max_size': 900 * 1024 * 1024,                 # 900 MB
        'repack_pak_modified_max_size': 50 * 1024 * 1024,  # 50 MB
        'repack_obb_modified_max_size': 300 * 1024 * 1024, # 300 MB
    },
    UserRole.dev: {
        'pak_max_size': 5 * 1024 * 1024 * 1024,            # 5 GB
        'obb_max_size': 5 * 1024 * 1024 * 1024,            # 5 GB
        'repack_pak_modified_max_size': 100 * 1024 * 1024, # 100 MB
        'repack_obb_modified_max_size': 1 * 1024 * 1024 * 1024, # 1 GB
    },
    # Admin rolleri 'dev' ile aynı limitlere sahip olacak
    UserRole.caylak_admin: 'dev',
    UserRole.usta_admin: 'dev',
    UserRole.kurucu: 'dev',
}

PAK_UNPACK_MAINTENANCE = False
PAK_RPACK_MAINTENANCE = False

OCR_KEYWORDS = {
    "deposit", "date", "check", "usdt", "completed", "fee", "wallet", "crypto",
    "address", "amount", "binance", "network", "spot", "receipt", "payment",
    "pay", "transaction", "status", "upi", "bank", "sent", "money", "paid",
    "paytm", "successfully", "details", "split", "google", "payments", "from",
    "id", "to", "invoice", "total", "purchase", "description", "merchant",
    "paypal", "appear", "hash", "txhash", "block", "confirmations", "confirms",
    "explorer", "tronscan", "etherscan", "trc20", "receiver", "recipient",
    "sender", "memo", "tag", "value", "decimals", "success", "successful",
    "pending", "reference", "ref", "no", "order", "mobile", "phone", "number",
    "vpa", "transferred", "account", "a/c", "google", "pay", "phonepe", "balance",
    "debit", "credit", "tax", "kdv", "subtotal", "document", "print", "issued",
    "statement", "tckn", "isim", "soyisim", "swift", "code", "iban", "routing",
    "wire", "transfer", "ach", "sepa", "clearing", "intermediary", "institution",
    "remittance", "advice", "originator", "beneficiary", "teller", "slip",
    "branch", "time", "stamp", "currency", "usd", "eur", "try", "gbp", "jpy",
    "krw", "cad", "aud", "rate", "exchange", "due", "discount", "adjustment",
    "shipping", "handling", "service", "charge", "tip", "gratuity", "payable",
    "net", "gross", "sales", "order", "quote", "quotation", "estimate",
    "refund", "return", "note", "cancellation", "void", "reversal",
    "authorization", "approval", "terminal", "batch", "pos", "register",
    "cashback", "loyalty", "points", "membership", "card", "store", "name",
    "website", "email", "support", "customer", "service", "hotline",
    "headquarters", "location", "city", "state", "zip", "postal", "country",
    "signature", "witness", "verified", "authentication", "digital", "token",
    "qrcode", "barcode", "screenshot", "attached", "file", "download", "save",
    "preview", "generated", "expiry", "valid", "until", "expires", "period",
    "monthly", "annual", "quarterly", "for"
}
        
@app.route('/admin/muted_users')
@login_required
@admin_required
def get_muted_users():
    """
    Admin paneli için aktif ve pasif susturma kayıtlarını döndürür.
    """
    try:
        now = datetime.utcnow()

        # Aktif susturmalar: Bitiş zamanı henüz gelmemiş olanlar
        # Eager loading (joinedload) ile kullanıcı bilgilerini tek sorguda çekerek performansı artırıyoruz.
        active_mutes_query = MuteLog.query.options(joinedload(MuteLog.user)).filter(MuteLog.mute_end_time > now).order_by(MuteLog.mute_end_time.asc()).all()

        # Pasif (geçmiş) susturmalar: Bitiş zamanı geçmiş olanlar
        inactive_mutes_query = MuteLog.query.options(joinedload(MuteLog.user)).filter(MuteLog.mute_end_time <= now).order_by(MuteLog.mute_end_time.desc()).limit(50).all() # Son 50 kaydı gösterelim

        def format_mute_data(mute_log):
            """Tek bir susturma kaydını JSON formatına çevirir."""
            user = mute_log.user
            # Varsayılan profil resmi mantığı
            default_pic = url_for('static', filename=f'images/{"free" if user.role.value == "ücretsiz" else user.role.value}.png')
            return {
                "id": mute_log.id,
                "mute_end_time": mute_log.mute_end_time.isoformat() + "Z", # JavaScript'in kolayca anlaması için ISO formatı
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "role": user.role.value,
                    "profile_pic": user.profile_pic_url or default_pic
                }
            }

        active_mutes = [format_mute_data(m) for m in active_mutes_query]
        inactive_mutes = [format_mute_data(m) for m in inactive_mutes_query]

        return jsonify({
            "active_mutes": active_mutes,
            "inactive_mutes": inactive_mutes
        })

    except Exception as e:
        app.logger.error(f"Susturulan kullanıcılar alınırken hata: {e}")
        return jsonify({"error": "Veriler alınırken sunucuda bir hata oluştu."}), 500

@app.route('/store_fingerprint', methods=['POST'])
def store_fingerprint():
    """
    AJAX ile gelen parmak izini kullanıcının session'ına kaydeder.
    """
    data = request.get_json()
    fingerprint = data.get('fingerprint')
    if fingerprint:
        session['fingerprint'] = fingerprint
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Fingerprint not provided'}), 400

@app.route('/create_purchase_intent', methods=['POST'])
@login_required
def create_purchase_intent():
    """
    Kullanıcının satın alma niyetini (hangi planı/süreyi/fiyatı seçtiğini)
    veritabanına kaydeder ve benzersiz bir intent_id döndürür.
    """
    data = request.get_json()
    role = data.get('role')
    duration = data.get('duration')
    price = data.get('price')

    if not all([role, duration, price]):
        return jsonify({"error": "Eksik plan bilgisi."}), 400

    try:
        # --- YENİ SPAM KORUMASI ---
        # Kullanıcının zaten onay bekleyen bir talebi var mı?
        existing_pending_intent = PurchaseIntent.query.filter_by(
            user_id=current_user.id,
            status='WAITING_FOR_ADMIN'
        ).first()

        if existing_pending_intent:
            app.logger.warning(f"Kullanıcı {current_user.username} - bekleyen bir talebi varken yeni bir satın alma niyeti oluşturmaya çalıştı (Engellendi).")
            # 409 Conflict (Çakışma) durum koduyla yeni çeviri anahtarını döndür.
            return jsonify({"error": "pending_approval_error"}), 409
        # --- KORUMA SONU ---

        # Yeni niyet kaydı oluştur
        new_intent = PurchaseIntent(
            user_id=current_user.id,
            role=role,
            duration=duration,
            price=price,
            status='PENDING'
        )
        db.session.add(new_intent)
        db.session.commit()

        # Yönetici takibi için log kaydı oluştur
        log_message = f"Satın alma niyeti oluşturuldu: {role.upper()} ({duration}) - Fiyat: {price}"
        record_log(
            user=current_user,
            action_description=log_message,
            file_type='SUBSCRIPTION',
            original_file_name=f"{role.upper()}_{duration}",
            original_file_size_mb=0 # Dosya olmadığı için 0
        )

        app.logger.info(f"Kullanıcı {current_user.username} - {log_message}")

        # YÖNLENDİRME GÜNCELLEMESİ: Artık yönlendiriyoruz
        return jsonify({
            "success": True,
            "intent_id": new_intent.intent_id,
            "message": "Niyet başarıyla kaydedildi.",
            "redirect_url": url_for('payment_options_page', intent_id=new_intent.intent_id) # YENİ YÖNLENDİRME
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Satın alma niyeti kaydedilirken hata: {e}")
        return jsonify({"error": "Niyetinizi kaydederken sunucuda bir hata oluştu."}), 500

def allowed_receipt_file(filename):
    """Dosya adının izin verilen dekont uzantılarından birine sahip olup olmadığını kontrol eder."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_RECEIPT_EXTENSIONS

def is_real_image(file_stream):
    """
    Dosyanın gerçekten bir resim olup olmadığını doğrular (örn: .exe'nin adını .png yapmak gibi).
    """
    try:
        # Dosya akışını başa sar (eğer daha önce okunduysa)
        file_stream.seek(0)
        # Resmi Pillow ile açmayı dene
        image = Image.open(file_stream)
        # Resim bütünlüğünü doğrula
        image.verify()

        # verify() sonrası dosyayı tekrar açmak gerekir
        file_stream.seek(0)
        # Yüklemeyi tekrar yapıp temel bir işlem yapmayı dene (örn: format)
        Image.open(file_stream).format

        file_stream.seek(0) # Akışı sonraki işlemler için tekrar başa sar
        return True
    except Exception as e:
        app.logger.warning(f"Resim doğrulama hatası (Dosya gerçek bir resim olmayabilir): {e}")
        return False

# --- YENİ check_receipt_keywords FONKSİYONU ---

def check_receipt_keywords(image_path):
    """
    Bir resim dosyasını ocr.space API'ye gönderir, metni alır ve anahtar kelimeleri arar.
    Bulunan ilk TAM KELİME eşleşmesini (string) veya None döndürür.
    """

    # 1. API Anahtarını Config'den al
    api_key = app.config.get('OCR_SPACE_API_KEY')
    if not api_key:
        app.logger.error("KRİTİK HATA: OCR_SPACE_API_KEY config'de tanımlanmamış.")
        return None

    try:
        # 2. API'ye göndermek için verileri hazırla
        # 'tur' (Türkçe) dilini seçiyoruz. İngilizce kelimeleri de tanıyacaktır.
        payload = {
            'apikey': api_key,
            'language': 'tur',
            'detectOrientation': True
        }

        # 3. Resmi aç ve API'ye POST isteği gönder
        with open(str(image_path), 'rb') as f:
            r = requests.post(
                'https://api.ocr.space/parse/image',
                files={'file': (Path(image_path).name, f, 'image/jpeg')}, # Dosya tipini belirtebiliriz
                data=payload,
                timeout=30 # 30 saniye zaman aşımı
            )

        # 4. API'den gelen cevabı işle
        r.raise_for_status() # Hatalı HTTP kodu varsa (500, 403 vb.) hata fırlat
        result = r.json()

        # 5. ocr.space hata kontrolü (API anahtarı yanlışsa vb.)
        if not result.get('IsErroredOnProcessing') is False:
            error_message = result.get('ErrorMessage', ['Bilinmeyen OCR hatası'])[0]
            app.logger.error(f"ocr.space API Hatası: {error_message}")
            return None

        if not result.get('ParsedResults'):
            app.logger.warning(f"ocr.space dekontta hiç metin bulamadı: {image_path}")
            return None

        # 6. Metni al ve birleştir
        full_text = ""
        for page in result.get('ParsedResults', []):
            full_text += page.get('ParsedText', '') + "\n"

        full_text = full_text.lower() # Küçük harfe çevir

        if not full_text:
            app.logger.warning(f"ocr.space metin döndürdü ancak içerik boş: {image_path}")
            return None

        app.logger.info(f"ocr.space API Çıktısı (ilk 500 karakter): {full_text[:500]}")

        # 7. Anahtar kelime arama (Bu kısım sizde zaten doğruydu)
        for keyword in OCR_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword) + r'\b', full_text):
                app.logger.info(f"Dekont doğrulandı! Bulunan TAM KELİME: '{keyword}'")
                return keyword # <-- Tam kelime eşleşmesi bulundu

        app.logger.warning(f"Dekont doğrulaması başarısız. Anahtar kelime (tam kelime olarak) bulunamadı. Metin: {full_text[:200]}...")
        return None

    except requests.exceptions.HTTPError as e:
        app.logger.error(f"ocr.space API'ye bağlanırken HTTP hatası (API Key?): {e.response.text}", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        app.logger.error(f"ocr.space API'ye bağlanırken ağ hatası: {e}", exc_info=True)
        return None
    except Exception as e:
        app.logger.error(f"ocr.space işlemi sırasında kritik hata: {e}", exc_info=True)
        return None

@app.route('/subscriptions')
@login_required
def subscriptions_page():
    uf = get_user_frames(current_user.id)
    active_frame_id = uf.get("active")
    return render_template('subscriptions.html', user=current_user, subscription_data=SUBSCRIPTION_DATA, active_frame_id=active_frame_id)

@app.route('/user/frames', methods=['GET', 'POST'])
@login_required
def user_frames():
    if request.method == 'GET':
        data = get_user_frames(current_user.id)
        return jsonify({"allowed": FRAMES, **data})
    data = request.get_json() or {}
    active = data.get('active')
    result = set_user_frames(current_user.id, active)
    return jsonify({"success": True, **result})

def ultimate_key_func():
    """
    Bu fonksiyon, her istek için daha zeki bir kimlik oluşturur.
    """
    # 1. Öncelik: Eğer kullanıcı sisteme giriş yapmışsa, en güvenli ve benzersiz
    # kimlik kendi kullanıcı ID'sidir. Bu, onu aynı IP'deki herkesten ayırır.
    if current_user.is_authenticated:
        return str(current_user.id)

    # 2. Öncelik: Eğer kullanıcı anonim ise (giriş/kayıt sayfasındaysa),
    # IP adresi ile tarayıcı bilgisini (User-Agent) birleştirerek bir kimlik oluştur.
    # Bu, aynı IP'den gelen bot ile gerçek kullanıcıyı birbirinden ayırır.
    else:
        user_agent = request.headers.get('User-Agent', 'unknown-agent')
        return f"{get_remote_address()}-{user_agent}"

# DÜZENLEME: Limiter yapılandırması
limiter = Limiter(
    key_func=ultimate_key_func,
    default_limits=["5000 per day", "300 per hour"],
    storage_uri="memory://",
)

scheduler = APScheduler()

def generate_captcha_image():
    """
    Rastgele bir matematik sorusu içeren bir CAPTCHA resmi oluşturur,
    doğru cevabı session'a kaydeder ve resmi döndürür.
    """
    try:
        # Rastgele sayılar ve bir operatör seç
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operator = random.choice(['+', '-'])

        if operator == '+' and num1 + num2 < 20:
            question = f"{num1} + {num2} = ?"
            answer = str(num1 + num2)
        else: # Çıkarma işlemi veya toplama 20'yi geçerse
            # Negatif sonuç çıkmasın diye büyükten küçüğü çıkar
            if num1 < num2:
                num1, num2 = num2, num1 # Sayıları yer değiştir
            question = f"{num1} - {num2} = ?"
            answer = str(num1 - num2)

        # Doğru cevabı kullanıcının session'ına güvenli bir şekilde kaydet
        session['captcha_answer'] = answer

        # Pillow ile resmi oluştur
        image = Image.new('RGB', (180, 60), color = (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # Windows'ta genellikle bulunan bir fontu kullanmaya çalışalım.
        # Eğer sunucu Linux ise, font yolunu değiştirmeniz gerekebilir (örn: '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        try:
            font = ImageFont.truetype("arial.ttf", 35)
        except IOError:
            font = ImageFont.load_default() # Font bulunamazsa varsayılanı kullan

        # Soru metnini resmin üzerine çiz
        draw.text((10, 10), question, fill=(0, 0, 0), font=font)

        # Botların okumasını zorlaştırmak için biraz "gürültü" ekleyelim
        for _ in range(10):
            draw.line(
                (random.randint(0, 180), random.randint(0, 60),
                 random.randint(0, 180), random.randint(0, 60)),
                fill=(random.randint(100,200), random.randint(100,200), random.randint(100,200))
            )

        # Resmi dosyaya kaydetmek yerine hafızada bir byte dizisine dönüştür
        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io

    except Exception as e:
        app.logger.error(f"CAPTCHA resmi oluşturulurken hata: {e}")
        return None

@app.route('/captcha.png')
def serve_captcha():
    """CAPTCHA resmini sunan rota."""
    img_io = generate_captcha_image()
    if img_io is None:
        return "CAPTCHA oluşturulamadı.", 500

    # Tarayıcının resmi cache'lememesi için başlık ekliyoruz
    response = send_file(img_io, mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def allowed_image_file(filename):
    """Dosya adının izin verilen resim uzantılarından birine sahip olup olmadığını kontrol eder."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def get_limits_for_user(user):
    """Kullanıcının rolüne göre geçerli limitleri döndürür."""
    user_limits = ROLE_LIMITS.get(user.role)
    # Eğer rol 'dev' gibi başka bir role yönlendirilmişse, o rolün limitlerini al
    if isinstance(user_limits, str):
        return ROLE_LIMITS.get(UserRole(user_limits))
    # Eğer rol tanımlı değilse, en düşük yetkili rol olan 'ücretsiz' limitlerini uygula
    if not user_limits:
        return ROLE_LIMITS.get(UserRole.ücretsiz)
    return user_limits

def generate_backup_code(length=5):
    """Güvenli, alfanümerik, tek kullanımlık bir yedek kod üretir."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@app.before_request
def before_request_tasks():
    # CSP Nonce oluşturma
    # g (global request object), bir istek boyunca veri saklamak için kullanılır.
    g.csp_nonce = secrets.token_hex(16)

    # Session token kontrolünü de buraya taşıyabiliriz.
    if current_user.is_authenticated:
        if 'user_token' not in session or session['user_token'] != current_user.session_token:
            logout_user()
            flash("Başka bir konumdan giriş yapıldığı veya oturumunuz sonlandırıldığı için çıkış yapıldı.", "warning")
            if request.method == "GET":
                return redirect(url_for('welcome'))

@app.before_request
def check_session_token():
    if current_user.is_authenticated:
        if 'user_token' not in session or session['user_token'] != current_user.session_token:
            logout_user()
            flash("Başka bir konumdan giriş yapıldığı veya oturumunuz sonlandırıldığı için çıkış yapıldı.", "warning")
            if request.method == "GET":
                return redirect(url_for('welcome'))

### YENİ: Süresi dolan rolleri kontrol edip güncelleyen fonksiyon ###
def check_expired_roles():
    """Süresi dolmuş rolleri kontrol eder ve kullanıcıları 'ücretsiz' role geri döndürür."""
    with app.app_context():
        try:
            now = datetime.utcnow()
            # role_expiry_date'i geçmiş ve rolü 'ücretsiz' olmayan kullanıcıları bul
            expired_users = User.query.filter(
                User.role_expiry_date.isnot(None),
                User.role_expiry_date < now,
                User.role != UserRole.ücretsiz
            ).all()

            if not expired_users:
                return

            app.logger.info(f"{len(expired_users)} kullanıcının rol süresi doldu. Güncelleme başlıyor...")
            for user in expired_users:
                old_role = user.role.value
                user.role = UserRole.ücretsiz
                user.role_expiry_date = None
                # Log kaydı, sistem tarafından yapıldığını belirtmek için user_id olmadan yapılabilir veya özel bir sistem kullanıcısı oluşturulabilir.
                # Şimdilik basit bir loglama yapalım.
                app.logger.info(f"Kullanıcı ID {user.id} ({user.username}), süresi dolduğu için '{old_role}' rolünden 'ücretsiz' rolüne düşürüldü.")

            db.session.commit()
            app.logger.info("Rol süre kontrolü ve güncelleme görevi başarıyla tamamlandı.")
        except Exception as e:
            app.logger.error(f"Süresi dolan rolleri kontrol etme görevi sırasında hata: {e}")
            db.session.rollback()

# YENİ: 24 saati geçmiş spam uyarılarını sıfırlayan fonksiyon
def reset_daily_captcha_fails():
    """Spam filtresine son takılmasının üzerinden 24 saat geçen kullanıcıların uyarı sayısını sıfırlar."""
    with app.app_context():
        try:
            # Son hatasının üzerinden 24 saat geçmiş ve hala uyarı sayısı olan kullanıcıları bul
            expiration_time = datetime.utcnow() - timedelta(hours=24)
            users_to_reset = User.query.filter(
                User.captcha_fail_count > 0,
                User.last_captcha_fail_time < expiration_time
            ).all()

            if not users_to_reset:
                return # Sıfırlanacak kullanıcı yoksa görevi bitir.

            app.logger.info(f"{len(users_to_reset)} kullanıcının günlük spam uyarısı sıfırlanıyor...")
            for user in users_to_reset:
                user.captcha_fail_count = 0

            db.session.commit()
            app.logger.info("Günlük spam uyarı sıfırlama görevi başarıyla tamamlandı.")
        except Exception as e:
            app.logger.error(f"Günlük spam uyarıları sıfırlanırken hata: {e}")
            db.session.rollback()

def cleanup_expired_files():
    """Süresi 10 dakikayı geçmiş geçici dosyaları sunucudan ve veritabanından siler."""
    with app.app_context():
        try:
            expiration_time = datetime.utcnow() - timedelta(minutes=10)
            expired_files = TemporaryFile.query.filter(TemporaryFile.created_at < expiration_time).all()

            if not expired_files:
                return

            app.logger.info(f"{len(expired_files)} adet süresi dolmuş dosya bulundu. Temizlik başlıyor...")
            for temp_file in expired_files:
                try:
                    if os.path.exists(temp_file.file_path):
                        os.remove(temp_file.file_path)
                        app.logger.info(f"Süresi dolan dosya silindi: {temp_file.file_path}")
                    else:
                        app.logger.warning(f"Dosya bulunamadı ama veritabanı kaydı silinecek: {temp_file.file_path}")
                    db.session.delete(temp_file)
                except Exception as e:
                    app.logger.error(f"Temizlik sırasında dosya silinirken hata ({temp_file.file_path}): {e}")

            db.session.commit()
            app.logger.info("Dosya temizlik görevi başarıyla tamamlandı.")
        except Exception as e:
            app.logger.error(f"Temizlik görevi sırasında kritik bir hata oluştu: {e}")
            db.session.rollback()

def delayed_cleanup(file_id, file_path):
    """Belirli bir süre sonra tek bir dosyayı ve veritabanı kaydını temizler."""
    with app.app_context():
        try:
            app.logger.info(f"Gecikmeli temizlik başlıyor: {file_path}")
            if os.path.exists(file_path):
                os.remove(file_path)
                app.logger.info(f"Gecikmeli temizlik: Dosya silindi -> {file_path}")
            else:
                app.logger.warning(f"Gecikmeli temizlik: Dosya zaten silinmiş -> {file_path}")

            temp_file_record = db.session.get(TemporaryFile, file_id)
            if temp_file_record:
                db.session.delete(temp_file_record)
                db.session.commit()
                app.logger.info(f"Gecikmeli temizlik: Veritabanı kaydı silindi -> ID: {file_id}")
            else:
                 app.logger.warning(f"Gecikmeli temizlik: Veritabanı kaydı bulunamadı -> ID: {file_id}")

        except Exception as e:
            app.logger.error(f"Gecikmeli temizlik sırasında hata oluştu ({file_path}): {e}")
            db.session.rollback()

db.init_app(app)
limiter.init_app(app)

from video import video_bp
from features import features_bp
from forum.routes import forum_bp

app.register_blueprint(video_bp)
app.register_blueprint(features_bp)
app.register_blueprint(forum_bp, url_prefix='/forum')

migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'welcome'

oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

UPLOAD_FOLDER = Path('uploads')
RESULT_FOLDER = Path('results')
PROFILE_PICS_FOLDER = Path('static/profile_pics')
USER_MEDIA_FOLDER = Path('user_media')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER
app.config['USER_MEDIA_FOLDER'] = USER_MEDIA_FOLDER

app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024 * 1024
MAX_OBB_SIZE_BYTES = int(1.3 * 1024 * 1024 * 1024)
MAX_PAK_SIZE_BYTES = 100 * 1024 * 1024

UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULT_FOLDER.mkdir(exist_ok=True)
PROFILE_PICS_FOLDER.mkdir(exist_ok=True)
USER_MEDIA_FOLDER.mkdir(exist_ok=True)

ALLOWED_EMAIL_DOMAINS = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "mail.com"}

@app.context_processor
def inject_uuid():
    return dict(uuid=uuid)

@app.route('/media/<path:filename>')
@login_required
def serve_user_media(filename):
    return send_from_directory(
        current_app.config['USER_MEDIA_FOLDER'],
        filename
    )

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/payment_options/<uuid:intent_id>')
@login_required
def payment_options_page(intent_id):
    """
    Kullanıcının satın alma niyetine (intent_id) göre ödeme yöntemlerini seçtiği sayfayı gösterir.
    """
    # intent_id'yi UUID nesnesi olarak aldık, string'e çevirip sorguluyoruz
    intent = PurchaseIntent.query.filter_by(intent_id=str(intent_id), user_id=current_user.id, status='PENDING').first()

    if not intent:
        flash("Geçersiz veya süresi dolmuş bir satın alma niyetine eriştiniz.", "danger")
        return redirect(url_for('subscriptions_page'))

    # Ödeme transfer detaylarını Python tarafında tanımlayalım
    payment_details = {
        'crypto': {
            'label_key': 'payment_crypto',
            'logo': url_for('static', filename='images/crypto_logo.png'),
            'info': "Deposit: USDT, Network: Tron (TRC20)",
            'transfer_value': "TN88cp3MDNKHrF7inCzfaZsRzFBFqiAP2V"
        },
        'famapp': {
            'label_key': 'payment_famapp',
            'logo': url_for('static', filename='images/famapp_logo.png'),
            'info': "UPI ID:",
            'transfer_value': "asilismail@fam"
        },
        'paytm': {
            'label_key': 'payment_paytm',
            'logo': url_for('static', filename='images/paytm_logo.png'),
            'info': "UPI ID:",
            'transfer_value': "notyet"
        },
        'paypal': {
            'label_key': 'payment_paypal',
            'logo': url_for('static', filename='images/paypal_logo.png'),
            'info': "E-MAIL:",
            'transfer_value': "erkanww62@gmail.com"
        }
    }

    # YENİ: Dekont klasörünün var olduğundan emin ol
    RECEIPT_UPLOAD_FOLDER.mkdir(exist_ok=True)

    uf = get_user_frames(current_user.id)
    active_frame_id = uf.get("active")
    return render_template('payment_options.html',
                           user=current_user,
                           intent=intent,
                           payment_details=payment_details,
                           active_frame_id=active_frame_id)

def check_action_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Giriş yapmalısınız."}), 401

        # GÜNCELLENDİ: Yeni admin rollerini de sınırsız olarak ekledik
        if current_user.role.value in ['dev', 'caylak_admin', 'usta_admin', 'kurucu']:
            return func(*args, **kwargs)

        can_act, message = current_user.can_perform_action()
        if not can_act:
            record_log(current_user, f"İşlem denemesi başarısız: Limit aşıldı.")
            return jsonify({"error": message}), 429

        response = func(*args, **kwargs)

        status_code = -1
        if isinstance(response, tuple):
            status_code = response[1]
        elif hasattr(response, 'status_code'):
            status_code = response.status_code

        if 200 <= status_code < 300:
            current_user.increment_action_count()
            db.session.commit()

        return response
    return wrapper

@app.route('/submit_payment_proof', methods=['POST'])
@login_required
@limiter.limit("500 per hour") 
def submit_payment_proof():

    # 1. Form Verilerini Al (Telefon kaldırıldı, Name yerine Username geldi)
    intent_id = request.form.get('intent_id')
    custom_username = request.form.get('custom_username', '').strip() # İsmin yerine bunu alıyoruz
    email = request.form.get('email', '').strip()

    if 'receipt_file' not in request.files:
        return jsonify({"success": False, "error": "Dekont dosyası eksik."}), 400

    receipt_file = request.files['receipt_file']

    # 2. Intent'i Doğrula
    intent = PurchaseIntent.query.filter_by(intent_id=intent_id, user_id=current_user.id, status='PENDING').first()
    if not intent:
        return jsonify({"success": False, "error": "Geçersiz veya süresi dolmuş satın alma oturumu."}), 404

    # --- GÜVENLİK KONTROLÜ (3 Deneme / 4 Saat Kuralı) ---
    if current_user.receipt_fail_count >= 3 and current_user.last_receipt_fail_time:
        time_since_fail = datetime.utcnow() - current_user.last_receipt_fail_time

        if time_since_fail < timedelta(hours=4):
            # Kullanıcı kilitli
            remaining_time = timedelta(hours=4) - time_since_fail
            app.logger.warning(f"Kullanıcı {current_user.username} (KİLİTLİ) dekont göndermeyi denedi.")

            # Frontend'e 429 hatası ve kalan süreyi saniye olarak gönder
            return jsonify({
                "success": False,
                "error": "TOO_MANY_ATTEMPTS",
                "remaining_time_seconds": remaining_time.total_seconds()
            }), 429

        else:
            # 4 saat dolmuş, sayacı sıfırla
            app.logger.info(f"Kullanıcı {current_user.username} için 4 saatlik kilit açıldı.")
            current_user.receipt_fail_count = 0
            current_user.last_receipt_fail_time = None
    # --- GÜVENLİK KONTROLÜ SONU ---

    # 3. Alan Uzunluklarını Doğrula
    # E-posta kontrolü:
    if not (1 < len(email) <= 35):
        return jsonify({"success": False, "error": "E-posta 35 karakterden uzun olamaz."}), 400
    
    # Kullanıcı adı kontrolü (İsteğe bağlı, zaten readonly ama yine de kontrol edelim)
    if not custom_username:
         custom_username = current_user.username # Boşsa mevcut kullanıcı adını kullan

    # 4. Dosya Doğrulaması (PY Tarafı)
    if not receipt_file.filename or not allowed_receipt_file(receipt_file.filename):
        return jsonify({"success": False, "error": "Geçersiz dosya türü. Sadece png, jpg, jpeg veya webp."}), 400

    # Dosya boyutunu güvenli bir şekilde al
    receipt_file.seek(0, os.SEEK_END)
    file_size = receipt_file.tell()
    receipt_file.seek(0)
    if file_size > MAX_RECEIPT_SIZE_BYTES:
        return jsonify({"success": False, "error": "Dosya boyutu çok büyük (Maks 10MB)."}), 413

    # 5. Dosyanın Gerçek Bir Resim Olduğunu Doğrula
    if not is_real_image(receipt_file):
        return jsonify({"success": False, "error": "Dosya bozuk veya geçerli bir resim değil."}), 400

    # 6. Geçici Olarak Kaydet ve OCR İşlemini Başlat
    temp_filename = f"temp_{uuid.uuid4().hex}_{secure_filename(receipt_file.filename)}"
    temp_path = UPLOAD_FOLDER / temp_filename

    try:
        receipt_file.save(temp_path)

        # 7. OCR ile Anahtar Kelime Kontrolü
        found_keyword = check_receipt_keywords(temp_path)

        if found_keyword:
            # Doğrulandı! Kalıcı olarak taşı.
            permanent_filename = f"{current_user.id}_{intent_id[:8]}_{uuid.uuid4().hex}.webp"
            permanent_path = RECEIPT_UPLOAD_FOLDER / permanent_filename

            # WebP olarak kaydet (Yerden tasarruf için)
            img = Image.open(temp_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(permanent_path, 'WEBP', quality=80)

            # Veritabanını güncelle
            intent.status = 'WAITING_FOR_ADMIN' # Durumu "Yönetici Onayı Bekliyor" yap
            intent.customer_name = custom_username # GÜNCELLENDİ: Kullanıcı adını kaydediyoruz
            intent.customer_phone = None # GÜNCELLENDİ: Telefon alanını boş bırakıyoruz
            intent.customer_email = email
            intent.receipt_image_path = permanent_path.as_posix()
            intent.payment_notified_at = datetime.utcnow()

            # Başarılı: Kullanıcının sayacını sıfırla
            current_user.receipt_fail_count = 0
            current_user.last_receipt_fail_time = None

            db.session.commit()

            app.logger.info(f"Kullanıcı {current_user.username} (Intent: {intent_id}) ödeme kanıtı yükledi ve DOĞRULANDI (Kelime: {found_keyword}).")

            # Log kaydı
            log_message = f"Ödeme kanıtı doğrulandı (Anahtar kelime: '{found_keyword}')"
            record_log(current_user, log_message, "SUBSCRIPTION", permanent_filename)

            # Geçici dosyayı sil
            os.remove(temp_path)

            return jsonify({"success": True, "verified": True})

        else:
            # Doğrulanmadı! Geçici dosyayı sil.
            os.remove(temp_path)
            app.logger.warning(f"Kullanıcı {current_user.username} (Intent: {intent_id}) geçersiz bir dekont yükledi.")
            record_log(current_user, "Geçersiz ödeme kanıtı yükledi (Doğrulanamadı)", "SUBSCRIPTION")

            # Başarısız: Sayacı artır ve kilidi ayarla
            current_user.receipt_fail_count += 1
            if current_user.receipt_fail_count >= 3:
                current_user.last_receipt_fail_time = datetime.utcnow()
                app.logger.warning(f"Kullanıcı {current_user.username} 3. kez hata yaptı. 4 saat kilitlendi.")

            db.session.commit() # Sayaç değişikliğini kaydet

            return jsonify({"success": True, "verified": False})

    except Exception as e:
        app.logger.error(f"Dekont işlenirken KRİTİK HATA (Intent: {intent_id}): {e}")
        # Hata olursa geçici dosyayı temizle
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"success": False, "error": "Sunucu hatası: Dekont işlenemedi."}), 500

@app.route('/')
def welcome():
    if current_user.is_authenticated:
        # DEĞİŞİKLİK BURADA: Artık 'index' yerine doğrudan foruma yönlendiriyoruz.
        return redirect(url_for('forum.forum_page'))

    # BU KISIM KORUNDU: CAPTCHA gösterme bayrağını session'a ekle
    if request.args.get('show_captcha'):
        session['show_captcha'] = True

    return render_template('welcome.html')

# Yardımcı fonksiyon: Okunabilir cihaz adı oluştur
def get_readable_device_name(ua_string):
    """
    User-Agent string'ini alıp "Chrome on Windows" gibi
    anlaşılır bir cihaza/tarayıcıya dönüştürür.
    """
    if not ua_string:
        return "Bilinmeyen Cihaz"

    user_agent = parse(ua_string)

    # Cihaz türünü belirle (PC, Tablet, Telefon)
    if user_agent.is_pc:
        # PC ise işletim sistemini cihaz olarak kabul et
        device = user_agent.os.family
    elif user_agent.is_tablet:
        device = user_agent.device.family
    elif user_agent.is_mobile:
        device = user_agent.device.family
    else:
        device = "Bilinmeyen"

    browser = user_agent.browser.family

    # "Generic Smartphone" gibi anlamsız isimleri temizle
    if "Generic" in device:
        device = user_agent.os.family # Onun yerine işletim sistemini kullan

    return f"{browser} on {device}"

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('forum.forum_page'))

    # Honeypot (Bal Küpü) Bot Kontrolü
    if request.form.get('website_field'): # Bu alan sadece botlar tarafından doldurulur.
        app.logger.warning(f"BOT YAKALANDI (Honeypot - Login): IP -> {request.remote_addr}")
        # Botlara ipucu vermemek için normal bir hata mesajıyla yönlendirme yapıyoruz.
        flash('Kullanıcı adı/e-posta veya şifre hatalı.', 'danger')
        return redirect(url_for('welcome', from_='login'))

    # --- Giriş Mantığı ---
    identifier = request.form.get('login_identifier')
    password = request.form.get('password')
    fingerprint = request.form.get('fingerprint')

    if not all([identifier, password, fingerprint]):
        flash('Kullanıcı adı/e-posta, şifre ve parmak izi gereklidir.', 'danger')
        return redirect(url_for('welcome', from_='login'))

    user = User.query.filter(or_(func.lower(User.username) == func.lower(identifier), User.email == identifier)).first()

    if user and user.check_password(password) and user.status == 'active':
        readable_name = get_readable_device_name(request.user_agent.string)
        now = datetime.utcnow()
        app.logger.info(f"'{user.username}' için giriş denemesi. Gelen fingerprint: {fingerprint}")

        # --- YENİ VE DOĞRU CİHAZ KONTROL MANTIĞI ---

        # 1. Adım: Gelen cihaz zaten kayıtlı mı?
        if user.device_1_fingerprint == fingerprint:
            app.logger.info("Giriş başarılı: Cihaz Slot 1'de bulundu. Bilgiler güncelleniyor.")
            user.device_1_last_login = now
            user.device_1_name = readable_name

        elif user.device_2_fingerprint == fingerprint:
            app.logger.info("Giriş başarılı: Cihaz Slot 2'de bulundu. Bilgiler güncelleniyor.")
            user.device_2_last_login = now
            user.device_2_name = readable_name

        # 2. Adım: Cihaz kayıtlı değilse, boş slot var mı?
        elif user.device_1_fingerprint is None:
            app.logger.info("Giriş başarılı: Yeni cihaz Slot 1'e kaydedildi.")
            user.device_1_fingerprint = fingerprint
            user.device_1_name = readable_name
            user.device_1_last_login = now

        elif user.device_2_fingerprint is None:
            app.logger.info("Giriş başarılı: Yeni cihaz Slot 2'ye kaydediledi.")
            user.device_2_fingerprint = fingerprint
            user.device_2_name = readable_name
            user.device_2_last_login = now

        # 3. Adım: Tüm slotlar dolu ve cihaz eşleşmiyorsa, girişi engelle.
        else:
            app.logger.warning(f"Giriş reddedildi: '{user.username}' için boş slot bulunamadı. Cihaz limiti dolu.")
            flash(f'Cihaz limitine ulaştınız (2/2). Giriş yapmak için kayıtlı bir cihazınızı kullanın veya bir yöneticiden eski bir cihazınızı kaldırmasını isteyin.', 'danger')
            return redirect(url_for('welcome', from_='login'))

        # --- KONTROL MANTIĞI SONU ---

        user.session_token = str(uuid.uuid4())
        db.session.commit()

        login_user(user, remember=True)
        session['user_token'] = user.session_token

        record_log(user, f"Başarıyla giriş yaptı ({readable_name}).")

        # --- YÖNLENDİRME GÜNCELLEMESİ BURADA ---
        # Eğer URL'de 'next' parametresi varsa (yani bir linkten geldiyse),
        # kullanıcıyı o linke yönlendir.
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        # Eğer 'next' parametresi yoksa, varsayılan ana sayfaya yönlendir.
        return redirect(url_for('forum.forum_page'))
        # --- GÜNCELLEME SONU ---

    elif user and user.status == 'deleted':
        flash('Bu hesap silinmiştir...', 'danger')
    else:
        flash('Kullanıcı adı/e-posta veya şifre hatalı.', 'danger')

    return redirect(url_for('welcome', from_='login'))

@app.route('/register', methods=['POST'])
@limiter.limit("15 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('forum.forum_page'))

    # Honeypot (Bal Küpü) Bot Kontrolü
    if request.form.get('website_field'):
        app.logger.warning(f"BOT YAKALANDI (Honeypot - Register): IP -> {request.remote_addr}")
        flash('Hesap oluşturulurken beklenmedik bir hata oluştu.', 'danger')
        return redirect(url_for('welcome', from_='register'))

    # CAPTCHA Doğrulama
    if session.get('show_captcha'):
        user_captcha_answer = request.form.get('captcha_answer', '').strip()
        correct_answer = session.get('captcha_answer')

        if not user_captcha_answer or user_captcha_answer != correct_answer:
            flash('Doğrulama kodu yanlış.', 'danger')
            return redirect(url_for('welcome', from_='register', show_captcha='true'))

        # CAPTCHA başarılı, temizle
        session.pop('show_captcha', None)
        session.pop('captcha_answer', None)

    # --- Kayıt Mantığı (Güvenlik kontrolleri ile) ---
    email = request.form.get('email', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    fingerprint = request.form.get('fingerprint')
    has_error = False

    # Zorunlu alan kontrolü
    if not all([email, username, password, fingerprint]):
        flash('Tüm alanları doldurmanız gerekmektedir.', 'danger')
        has_error = True

    # Karakter limiti kontrolleri
    if len(username) > 15:
        flash('Kullanıcı adı en fazla 15 karakter olabilir.', 'danger')
        has_error = True

    if len(email) > 25:
        flash('E-posta adresi en fazla 25 karakter olabilir.', 'danger')
        has_error = True

    if len(password) > 20:
        flash('Şifre en fazla 20 karakter olabilir.', 'danger')
        has_error = True

    # Kullanıcı adı format kontrolü
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        flash('Kullanıcı adı sadece harf, rakam ve alt çizgi (_) içerebilir ve 3-20 karakter uzunluğunda olmalıdır.', 'danger')
        has_error = True

    # E-posta domain kontrolü
    try:
        domain = email.split('@')[1]
        if domain not in ALLOWED_EMAIL_DOMAINS:
            flash('Sadece güvenilir e-posta sağlayıcıları kabul edilmektedir.', 'danger')
            has_error = True
    except IndexError:
        flash('Geçerli bir e-posta adresi giriniz.', 'danger')
        has_error = True

    # Şifre güçlülük kontrolü
    if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        flash('Şifre en az 8 karakter uzunluğunda olmalı, bir büyük harf ve bir özel karakter içermelidir.', 'danger')
        has_error = True

    # E-posta ve kullanıcı adı benzersizlik kontrolü
    if User.query.filter(User.email == email).first():
        flash('Bu e-posta adresi zaten kullanılıyor.', 'danger')
        has_error = True

    if User.query.filter(func.lower(User.username) == func.lower(username)).first():
        flash('Bu kullanıcı adı zaten alınmış.', 'danger')
        has_error = True

    # Hata varsa CAPTCHA gösterimini aktif et ve yönlendir
    if has_error:
        session['show_captcha'] = True  # Hata durumunda CAPTCHA göster
        return redirect(url_for('welcome', from_='register', show_captcha='true'))

    try:
        # Yeni kullanıcı oluştur
        new_user = User(
            username=username,
            email=email,
            browser_fingerprint=fingerprint,
            status='active',
            backup_code=generate_backup_code(),
            session_token=str(uuid.uuid4())
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Başarılı kayıt logu
        record_log(new_user, "Başarıyla kayıt oldu.")
        flash('Hesabınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz.', 'success')

        return redirect(url_for('welcome', from_='login'))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Kayıt sırasında veritabanı hatası: {e}")
        flash('Hesap oluşturulurken beklenmedik bir hata oluştu.', 'danger')
        return redirect(url_for('welcome', from_='register'))

# --- YENİ: ŞİFRE SIFIRLAMA ROTALARI ---
@app.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('forum.forum_page'))

    if request.method == 'POST':
        email = request.form.get('email')
        backup_code = request.form.get('backup_code')

        user = User.query.filter_by(email=email).first()

        if user and user.backup_code == backup_code.upper():
            # Kod doğru, kullanıcıyı sıfırlama için session'a kaydet
            session['user_to_reset_id'] = user.id
            flash('Yedek kod doğrulandı. Lütfen yeni şifrenizi belirleyin.', 'success')
            return redirect(url_for('reset_password_with_code'))
        else:
            flash('E-posta veya yedek kod hatalı.', 'danger')
            return redirect(url_for('welcome', from_='forgot_password'))

    # GET isteği için şifremi unuttum formunu göster
    return redirect(url_for('welcome', from_='forgot_password'))

@app.route('/reset_password_with_code', methods=['GET', 'POST'])
def reset_password_with_code():
    if 'user_to_reset_id' not in session:
        flash('Şifre sıfırlama talebi geçersiz veya süresi dolmuş.', 'warning')
        return redirect(url_for('welcome'))

    user = db.session.get(User, session['user_to_reset_id'])
    if not user:
        session.pop('user_to_reset_id', None)
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('welcome'))

    if request.method == 'POST':
        new_password = request.form.get('password')

        # YENİ: Karakter limiti kontrolü
        if len(new_password) > 20:
            flash('Yeni şifre en fazla 20 karakter olabilir.', 'danger')
            return render_template('reset_password_form.html')

        if len(new_password) < 8 or not re.search(r'[A-Z]', new_password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            flash('Şifre en az 8 karakter uzunluğunda olmalı, bir büyük harf ve bir özel karakter içermelidir.', 'danger')
            return render_template('reset_password_form.html')

        user.set_password(new_password)
        user.backup_code = generate_backup_code()
        user.session_token = str(uuid.uuid4())

        db.session.commit()

        record_log(user, "Yedek kod ile şifresini başarıyla sıfırladı.")
        session.pop('user_to_reset_id', None)
        flash('Şifreniz başarıyla güncellendi. Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('welcome', from_='login'))

    return render_template('reset_password_form.html')

# *** YENİ ROTA: Anlık kullanıcı adı kontrolü için ***
@app.route('/check_username', methods=['POST'])
def check_username():
    username = request.json.get('username')
    if not username or len(username) < 3:
        return jsonify({"available": False, "reason": "too_short"})

    # Veritabanında kullanıcı adını küçük/büyük harf duyarsız ara
    user_exists = User.query.filter(func.lower(User.username) == func.lower(username)).first()

    if user_exists:
        return jsonify({"available": False, "reason": "taken"})
    else:
        return jsonify({"available": True})

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    # Bu fonksiyon, bir kullanıcının Ayarlar menüsünden kendi hesabını silmesi içindir.
    user_to_delete = current_user

    if user_to_delete.role == UserRole.kurucu:
        return jsonify({"error": "Kurucu hesabı bu yolla silinemez."}), 403

    try:
        # İsteğiniz doğrultusunda, kullanıcıyı DB'den silmek yerine durumunu güncelliyoruz.
        # Bu, sohbet geçmişi gibi ilişkili verilerin korunmasını sağlar.
        user_to_delete.status = 'deleted'

        # Kullanıcı adını ve e-postasını, yeniden kaydı engellemek için korurken,
        # tekrar giriş yapmasını engellemek için şifresini sıfırlıyoruz.
        user_to_delete.password_hash = generate_password_hash(str(uuid.uuid4()))

        # Diğer tüm aktif oturumlarını sonlandırıyoruz.
        user_to_delete.session_token = str(uuid.uuid4())

        record_log(user_to_delete, "Kullanıcı kendi hesabını sildi (devre dışı bıraktı).")

        # Değişiklikleri kaydet
        db.session.commit()

        # Kullanıcıyı sistemden çıkar
        logout_user()

        flash('Hesabınız ve ilişkili tüm verileriniz başarıyla devre dışı bırakıldı.', 'success')
        return jsonify({"success": True, "redirect_url": url_for('welcome')})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Hesap silinirken hata (User ID: {user_to_delete.id}): {e}")
        return jsonify({"error": "Hesap silinirken bir sunucu hatası oluştu."}), 500

@app.route('/google/login')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/google/auth')
def google_auth():
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get('userinfo')
        if not userinfo:
            raise Exception("Kullanıcı bilgisi (userinfo) token içinde bulunamadı.")
    except Exception as e:
        app.logger.error(f"Google Auth error: {e}")
        flash("Google ile kimlik doğrulama sırasında bir hata oluştu. Lütfen tekrar deneyin.", "danger")
        # Hata durumunda 'login' formu 'welcome' sayfasında olduğu için oraya yönlendiriyoruz.
        return redirect(url_for('welcome'))

    email = userinfo.get('email')
    if not email:
        flash("Google hesabınızdan e-posta bilgisi alınamadı.", "danger")
        return redirect(url_for('welcome'))

    # Session'dan parmak izini al (JS ile /store_fingerprint'e gönderilen)
    fingerprint = session.pop('fingerprint', None)
    readable_name = get_readable_device_name(request.user_agent.string)
    now = datetime.utcnow()

    user = User.query.filter_by(email=email).first()

    if user:
        # --- MEVCUT KULLANICI GİRİŞ AKIŞI ---
        # Normal /login rotasındaki cihaz kontrol mantığını buraya da uyguluyoruz

        app.logger.info(f"Google Login (Mevcut Kullanıcı): '{user.username}' için giriş denemesi. Fingerprint: {fingerprint}")

        if fingerprint:
            if user.device_1_fingerprint == fingerprint:
                user.device_1_last_login = now
                user.device_1_name = readable_name
            elif user.device_2_fingerprint == fingerprint:
                user.device_2_last_login = now
                user.device_2_name = readable_name
            elif user.device_1_fingerprint is None:
                user.device_1_fingerprint = fingerprint
                user.device_1_name = readable_name
                user.device_1_last_login = now
            elif user.device_2_fingerprint is None:
                user.device_2_fingerprint = fingerprint
                user.device_2_name = readable_name
                user.device_2_last_login = now
            else:
                app.logger.warning(f"Google Login reddedildi: '{user.username}' için boş slot bulunamadı.")
                flash(f'Cihaz limitine ulaştınız (2/2). Giriş yapmak için kayıtlı bir cihazınızı kullanın.', 'danger')
                return redirect(url_for('welcome'))
        else:
            app.logger.warning(f"Google Login: {user.username} için session'da fingerprint bulunamadı. Cihaz kontrolü atlanıyor.")

        # Session token'ı yenile ve veritabanına kaydet
        user.session_token = str(uuid.uuid4())
        db.session.commit()

        # Kullanıcıyı sisteme giriş yaptır
        login_user(user, remember=True)
        session['user_token'] = user.session_token

        record_log(user, "Google ile başarıyla giriş yaptı.")
        # Doğrudan foruma yönlendir
        return redirect(url_for('forum.forum_page'))

    else:
        # --- YENİ KULLANICI OTOMATİK KAYIT AKIŞI ---
        app.logger.info(f"Google Login (Yeni Kullanıcı): '{email}' için otomatik kayıt başlıyor. Fingerprint: {fingerprint}")

        # 1. Benzersiz kullanıcı adı oluştur (Bu kod sizde zaten vardı)
        new_username = userinfo.get('name', 'kullanici').replace(" ", "")
        while User.query.filter(func.lower(User.username) == func.lower(new_username)).first():
            new_username = f"{new_username}_{str(uuid.uuid4())[:4]}"

        # 2. Güvenli, rastgele bir şifre oluştur (Kullanıcı bunu bilmeyecek)
        random_password = secrets.token_urlsafe(16)

        # 3. Yeni kullanıcıyı oluştur ve TÜM GEREKLİ ALANLARI doldur
        try:
            new_user = User(
                username=new_username,
                email=email,
                status='active',
                # Rastgele şifreyi hash'leyerek kaydet
                password_hash=generate_password_hash(random_password),
                # Yeni kullanıcıya bir yedek kod oluştur
                backup_code=generate_backup_code(),
                # Session token'ı ayarla
                session_token=str(uuid.uuid4()),
                # Cihaz bilgilerini doğrudan ilk slota kaydet
                device_1_fingerprint=fingerprint,
                device_1_name=readable_name,
                device_1_last_login=now
            )

            db.session.add(new_user)
            db.session.commit()

            # 4. Kullanıcıyı anında sisteme giriş yaptır
            login_user(new_user, remember=True)
            session['user_token'] = new_user.session_token

            record_log(new_user, "Google ile yeni hesap başarıyla oluşturuldu.")
            flash('Google hesabınızla başarıyla kayıt oldunuz! ToolVision\'a hoş geldiniz.', 'success')

            # 5. Doğrudan foruma yönlendir
            return redirect(url_for('forum.forum_page'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Google ile yeni kullanıcı kaydı sırasında kritik hata: {e}")
            flash('Hesabınız oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
            return redirect(url_for('welcome'))

@app.route('/logout')
@login_required
def logout():
    # YENİ: Şifre değiştirme sonrası özel mesaj
    reason = request.args.get('reason')
    if reason == 'password_changed':
        flash("Şifreniz değiştirildi, lütfen yeni şifrenizle tekrar giriş yapın.", "warning") # warning kategorisi mavi bir flash mesajı gösterir
    else:
        record_log(current_user, "Güvenli çıkış yaptı.")

    logout_user()
    session.pop('user_token', None)
    return redirect(url_for('welcome'))

# --- ANA UYGULAMA ROTALARI ---
@app.route('/index')
@login_required
def index():
    # Bu rota artık sadece araçları içeren 'atölye' sayfasını gösterir.
    uf = get_user_frames(current_user.id)
    active_frame_id = uf.get("active")
    return render_template('index.html', user=current_user, active_frame_id=active_frame_id)

@app.route('/profile_pics/<filename>')
def serve_profile_pic(filename):
    return send_from_directory(app.config['PROFILE_PICS_FOLDER'], filename)

@app.route('/update_profile_pic', methods=['POST'])
@login_required
def update_profile_pic():
    if 'profile_pic' not in request.files:
        return jsonify({"error": "Dosya bulunamadı"}), 400

    file = request.files['profile_pic']

    # --- DOSYA BOYUTU KONTROLÜ (Aynen kalır) ---
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_PROFILE_PIC_SIZE_BYTES:
        limit_mb = MAX_PROFILE_PIC_SIZE_BYTES / 1024 / 1024
        return jsonify({"error": f"Dosya boyutu çok büyük. Maksimum boyut {limit_mb} MB olabilir."}), 413

    # --- DOSYA TÜRÜ KONTROLÜ (Aynen kalır) ---
    if file.filename == '' or not allowed_image_file(file.filename):
        return jsonify({"error": "Geçersiz veya desteklenmeyen dosya türü. Sadece PNG, JPG, JPEG, GIF yükleyebilirsiniz."}), 400

    # --- YENİ "HARDCORE" SIKIŞTIRMA ALGORİTMASI ---
    try:
        img = Image.open(file.stream)
        img = ImageOps.exif_transpose(img)
        crop_json = request.form.get('crop_data')
        if crop_json:
            try:
                cd = json.loads(crop_json)
                x = int(cd.get('x', 0))
                y = int(cd.get('y', 0))
                w = int(cd.get('width', 0))
                h = int(cd.get('height', 0))
                if w > 0 and h > 0:
                    if x < 0: x = 0
                    if y < 0: y = 0
                    if x >= img.width: x = img.width - 1
                    if y >= img.height: y = img.height - 1
                    w = min(w, img.width - x)
                    h = min(h, img.height - y)
                    img = img.crop((x, y, x + w, y + h))
            except Exception:
                pass

        max_dim = max(img.width, img.height)
        if max_dim > 512:
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)

        # 4. Şeffaflık (PNG) varsa, beyaz arka planla birleştir ve RGB formatına dönüştür
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
            background.paste(img, img.getchannel('A'))
            img = background.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 5. YENİ DOSYA ADI: .webp uzantısı kullan
        original_stem = Path(secure_filename(file.filename)).stem
        filename = f"{current_user.id}_{uuid.uuid4().hex}_{original_stem}.webp" # .jpg -> .webp
        file_path = app.config['PROFILE_PICS_FOLDER'] / filename

        # 6. Varsa eski profil resmini sunucudan sil
        if current_user.profile_pic_url and 'profile_pics' in current_user.profile_pic_url:
            old_pic_path_str = current_user.profile_pic_url.split('/')[-1]
            old_pic_path = app.config['PROFILE_PICS_FOLDER'] / old_pic_path_str
            if old_pic_path.exists():
                os.remove(old_pic_path)

        # 7. KAYDETME AYARLARI (yüksek kalite)
        img.save(file_path, 'WEBP', quality=92, optimize=True)

        # 8. Kullanıcının veritabanı kaydını yeni dosya yoluyla güncelle
        current_user.profile_pic_url = url_for('serve_profile_pic', filename=filename)
        db.session.commit()

        record_log(current_user, f"Profil resmi güncellendi (hardcore sıkıştırıldı): '{filename}'")

        return jsonify({"success": True, "profile_pic_url": current_user.profile_pic_url})

    except Exception as e:
        app.logger.error(f"Profil resmi işlenirken hata: {e}")
        traceback.print_exc()

        # --- GÜVENLİK AĞI (FALLBACK) ---
        # Eğer WebP kaydetme başarısız olursa (sunucuda destek yoksa) JPEG'e geri dön
        if "unknown file extension" in str(e) or "encoder" in str(e) or "WEBP" in str(e):
            app.logger.warning("WebP formatı sunucuda desteklenmiyor olabilir. JPEG'e (fallback) dönülüyor.")
            try:
                # 5b. JPEG Fallback dosya adı
                original_stem = Path(secure_filename(file.filename)).stem
                filename_jpg = f"{current_user.id}_{uuid.uuid4().hex}_{original_stem}.jpg"
                file_path_jpg = app.config['PROFILE_PICS_FOLDER'] / filename_jpg

                # 6b. Eski resmi sil (tekrar)
                if current_user.profile_pic_url and 'profile_pics' in current_user.profile_pic_url:
                    old_pic_path_str = current_user.profile_pic_url.split('/')[-1]
                    old_pic_path = app.config['PROFILE_PICS_FOLDER'] / old_pic_path_str
                    if old_pic_path.exists(): os.remove(old_pic_path)

                # 7b. JPEG olarak yüksek kalite ile kaydet
                img.save(file_path_jpg, 'JPEG', quality=92, optimize=True)

                # 8b. Veritabanını güncelle
                current_user.profile_pic_url = url_for('serve_profile_pic', filename=filename_jpg)
                db.session.commit()

                record_log(current_user, f"Profil resmi güncellendi (JPEG fallback sıkıştırıldı): '{filename_jpg}'")
                return jsonify({"success": True, "profile_pic_url": current_user.profile_pic_url})

            except Exception as e_fallback:
                app.logger.error(f"JPEG Fallback sırasında da KRİTİK HATA: {e_fallback}")
                traceback.print_exc()
                return jsonify({"error": "Resim işlenirken (JPEG fallback) bir hata oluştu."}), 500

        # WebP dışı başka bir hata ise
        return jsonify({"error": "Profil resmi işlenirken bir hata oluştu."}), 500

@app.route('/get_user_info')
@login_required
def get_user_info():
    default_profile_pic_name = 'free.png' if current_user.role == UserRole.ücretsiz else f'{current_user.role.value}.png'
    default_profile_pic_url = url_for('static', filename=f'images/{default_profile_pic_name}')

    return jsonify({
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "profile_pic_url": current_user.profile_pic_url or default_profile_pic_url,
        "backup_code": current_user.backup_code
    })

@app.route('/update_username', methods=['POST'])
@login_required
def update_username():
    # Sadece beklediğimiz veriyi al, fazlasını görmezden gel
    data = request.get_json()
    if not data or 'username' not in data:
        return jsonify({"error_key": "username_cannot_be_empty"}), 400

    new_username = data.get('username')
    if not new_username:
        return jsonify({"error_key": "username_cannot_be_empty"}), 400

    # YENİ: Karakter limiti kontrolü
    if len(new_username) > 15:
        return jsonify({"error_key": "username_too_long"}), 400

    if current_user.username.lower() == new_username.lower():
        return jsonify({"success": True, "message_key": "username_already_up_to_date"})

    if User.query.filter(func.lower(User.username) == func.lower(new_username), User.id != current_user.id).first():
        return jsonify({"error_key": "username_already_taken"}), 409

    old_username = current_user.username
    current_user.username = new_username
    try:
        db.session.commit()
        record_log(current_user, f"Kullanıcı adını '{old_username}' -> '{new_username}' olarak güncelledi.")
        return jsonify({"success": True, "message_key": "username_updated_success"})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Kullanıcı adı güncellenirken hata: {e}")
        return jsonify({"error": "Kullanıcı adı güncellenirken bir hata oluştu."}), 500

### DÜZELTME: İki tane olan 'change_password' rotasından biri silindi. Sadece bu versiyon kaldı. ###
@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')

    if not old_password or not new_password:
        return jsonify({"error": {"key": "password_fields_required"}}), 400

    # YENİ: Karakter limiti kontrolü
    if len(new_password) > 20:
        return jsonify({"error": {"key": "password_validation_error", "details": "şifre en fazla 20 karakter olmalı"}}), 400

    if not current_user.check_password(old_password):
        return jsonify({"error": {"key": "current_password_incorrect"}}), 401

    if current_user.check_password(new_password):
        return jsonify({"error": {"key": "password_same_as_old"}}), 400

    password_errors = []
    if len(new_password) < 8:
        password_errors.append("en az 8 karakter uzunluğunda olmalı")
    if not re.search(r'[A-Z]', new_password):
        password_errors.append("en az bir büyük harf içermeli")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        password_errors.append("en az bir özel karakter içermeli")

    if password_errors:
        return jsonify({"error": {"key": "password_validation_error", "details": ", ".join(password_errors)}}), 400

    current_user.set_password(new_password)
    current_user.session_token = str(uuid.uuid4())
    try:
        db.session.commit()
        record_log(current_user, "Şifresini başarıyla değiştirdi.")
        # YENİ: Başarı mesajı güncellendi ve logout_required bayrağı eklendi
        return jsonify({
            "success": True,
            "message": {"key": "password_updated_success_redirect"},
            "logout_required": True
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": {"key": "server_error_on_password_change"}}), 500

@app.route('/log_frontend_failure', methods=['POST'])
@login_required
def log_frontend_failure():
    """
    Dosya yüklemesi başlamadan JS tarafında yakalanan
    (örn: boyut limiti aşıldı) hataları loglamak için kullanılır.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Eksik veri"}), 400

    action_type = data.get('action_type')
    file_name = data.get('file_name', 'Bilinmeyen Dosya')
    file_size_mb = data.get('file_size_mb', 0)
    limit_mb = data.get('limit_mb', 0)

    log_message = ""
    log_category = "Genel"

    try:
        # OBB Hataları
        if action_type == 'unpack_obb_fail':
            log_message = f"Unpack OBB denemesi başarısız: Boyut limiti aşıldı. (Dosya: {file_size_mb:.2f} MB, Limit: {limit_mb:.0f} MB)"
            log_category = "OBB"

        elif action_type == 'repack_obb_fail_original':
            log_message = f"Repack OBB denemesi başarısız: Orijinal dosya boyutu limiti aşıldı. (Dosya: {file_size_mb:.2f} MB, Limit: {limit_mb:.0f} MB)"
            log_category = "OBB"

        elif action_type == 'repack_obb_fail_modified':
            log_message = f"Repack OBB denemesi başarısız: Değiştirilen dosyalar limiti aşıldı. (Toplam Boyut: {file_size_mb:.2f} MB, Limit: {limit_mb:.0f} MB)"
            log_category = "OBB"
            
        # YENİ: PAK Hataları
        elif action_type == 'unpack_pak_fail':
            log_message = f"Unpack PAK denemesi başarısız: Boyut limiti aşıldı. (Dosya: {file_size_mb:.2f} MB, Limit: {limit_mb:.0f} MB)"
            log_category = "PAK"

        elif action_type == 'repack_pak_fail_original':
            log_message = f"Repack PAK denemesi başarısız: Orijinal dosya boyutu limiti aşıldı. (Dosya: {file_size_mb:.2f} MB, Limit: {limit_mb:.0f} MB)"
            log_category = "PAK"
            
        elif action_type == 'repack_pak_fail_modified':
            log_message = f"Repack PAK denemesi başarısız: Değiştirilen dosyalar limiti aşıldı. (Toplam Boyut: {file_size_mb:.2f} MB, Limit: {limit_mb:.0f} MB)"
            log_category = "PAK"

        else:
            return jsonify({"error": "Geçersiz eylem türü"}), 400

        record_log(
            user=current_user,
            action_description=log_message,
            file_type=log_category,
            original_file_name=file_name,
            original_file_size_mb=file_size_mb
        )

        return jsonify({"success": True, "message": "Log kaydedildi."}), 200

    except Exception as e:
        app.logger.error(f"Frontend log kaydı sırasında hata: {e}")
        return jsonify({"error": "Loglama sırasında sunucu hatası"}), 500

# --- YENİ EKLENECEK ROTA: Yerel Köprü İşlemlerini Loglamak İçin ---
@app.route('/log_local_action', methods=['POST'])
@login_required
def log_local_action():
    """
    Yerel köprü (Bridge) üzerinden yapılan işlemlerin (Unpack/Repack)
    sonucunu sunucuya bildirir ve veritabanına loglar.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Eksik veri"}), 400
        
    action_type = data.get('action_type', 'Yerel İşlem')
    file_name = data.get('file_name', 'Bilinmeyen')
    file_size_mb = data.get('file_size_mb', 0)
    status = data.get('status', 'Bilinmiyor')
    
    # Dosya tipini action_type stringinden çıkar (PAK veya OBB içeriyor mu?)
    file_type = "Genel"
    if "PAK" in action_type.upper(): file_type = "PAK"
    elif "OBB" in action_type.upper(): file_type = "OBB"
    
    log_message = f"{action_type}: {status}"
    
    try:
        record_log(
            user=current_user,
            action_description=log_message,
            file_type=file_type,
            original_file_name=file_name,
            original_file_size_mb=file_size_mb
        )
        # Başarılı işlemlerde kullanıcının işlem sayısını artır
        if status.startswith("Başarılı"):
            # Admin rolleri hariç (onlar zaten sınırsız)
            if current_user.role.value not in ['dev', 'caylak_admin', 'usta_admin', 'kurucu']:
                current_user.increment_action_count()
                db.session.commit()
        
        return jsonify({"success": True}), 200
    except Exception as e:
        app.logger.error(f"Yerel loglama hatası: {e}")
        return jsonify({"error": "Sunucu hatası"}), 500

@app.route('/get_user_limits')
@login_required
def get_user_limits():
    limits_info = current_user.get_remaining_actions()

    # Get the raw byte limits for the user's role
    user_byte_limits = get_limits_for_user(current_user)

    limits_info['byte_limits'] = {
        'pak_max_size': user_byte_limits['pak_max_size'],
        'obb_max_size': user_byte_limits['obb_max_size'],
        'repack_pak_modified_max_size': user_byte_limits['repack_pak_modified_max_size'],
        'repack_obb_modified_max_size': user_byte_limits['repack_obb_modified_max_size']
    }

    limits_info['role_expiry_date'] = current_user.role_expiry_date.isoformat() if current_user.role_expiry_date else None

    # --- YENİ EKLEME (KİLİT DURUMUNU BİLDİRME) ---
    limits_info['receipt_lockout_until_seconds'] = 0 # Varsayılan (kilit yok)

    if current_user.receipt_fail_count >= 3 and current_user.last_receipt_fail_time:
        time_since_fail = datetime.utcnow() - current_user.last_receipt_fail_time
        if time_since_fail < timedelta(hours=4):
            remaining_time = timedelta(hours=4) - time_since_fail
            limits_info['receipt_lockout_until_seconds'] = int(remaining_time.total_seconds())
    # --- EKLEME SONU ---

    response = jsonify(limits_info)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ### YENİ ROTA: Kullanıcının dil tercihini güncelleme ###
@app.route('/update_language', methods=['POST'])
@login_required
def update_language():
    language = request.json.get('language')
    if language and language != current_user.selected_language:
        try:
            old_lang = current_user.selected_language
            current_user.selected_language = language
            db.session.commit()
            record_log(current_user, f"Dil tercihini '{old_lang}' -> '{language}' olarak güncelledi.")
            return jsonify({"success": True})
        except Exception as e:
            app.logger.error(f"Dil güncellenirken hata: {e}")
            db.session.rollback()
            return jsonify({"success": False, "error": "Sunucu hatası"}), 500
    return jsonify({"success": True}) # Dil aynıysa veya geçersizse bile başarılı dönsün.

# ### YENİ ROTA: Kullanıcının sayfa geçiş süresini kaydetme ###
@app.route('/record_page_visit', methods=['POST'])
@login_required
def record_page_visit():
    data = request.json
    page_id = data.get('page_id')
    duration_seconds = data.get('duration_seconds')

    if not page_id or duration_seconds is None:
        return jsonify({"error": "Eksik veri"}), 400

    try:
        duration_seconds = int(duration_seconds)
        if duration_seconds > 0:
            log = PageVisitLog(
                user_id=current_user.id,
                page_id=page_id,
                duration_seconds=duration_seconds
            )
            db.session.add(log)
            db.session.commit()
            # Bu logu ActivityLog'a atmaya gerek yok, PageVisitLog kendi başına bir log.
            return jsonify({"success": True})
        return jsonify({"success": True}) # Süre 0 ise log kaydı yok.
    except ValueError:
        return jsonify({"error": "Geçersiz süre formatı"}), 400
    except Exception as e:
        app.logger.error(f"Sayfa ziyaret süresi kaydedilirken hata: {e}")
        db.session.rollback()
        return jsonify({"error": "Sunucu hatası"}), 500


# --- ADMIN PANELİ ROTALARI ---
# app.py

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # 1. Kurucu bilgilerini al (e-posta sansürleme için)
    kurucu_user = User.query.filter_by(role=UserRole.kurucu).first()

    # 2. Kullanıcıları role göre filtrele
    if current_user.role == UserRole.kurucu:
        all_users_query = User.query.order_by(User.id.desc())
    else:
        all_users_query = User.query.filter(User.status != 'deleted').order_by(User.id.desc())
    all_users = all_users_query.all()

    # 3. Genel istatistikleri ve analizleri çek
    all_actions = ActivityLog.query.all()
    all_page_visits = PageVisitLog.query.all()

    # Kullanıcı bazında toplam aksiyonları verimli bir şekilde say
    user_action_counts = {}
    for log in all_actions:
        user_action_counts[log.user_id] = user_action_counts.get(log.user_id, 0) + 1

    # Sayfa ziyaret süreleri analizi
    page_duration_analysis = {}
    for visit in all_page_visits:
        page_id = visit.page_id
        duration = visit.duration_seconds
        if page_id not in page_duration_analysis:
            page_duration_analysis[page_id] = {'total_duration': 0, 'count': 0}
        page_duration_analysis[page_id]['total_duration'] += duration
        page_duration_analysis[page_id]['count'] += 1

    page_visit_stats = {}
    for page_id, data in page_duration_analysis.items():
        if data['count'] > 0:
            avg_duration = data['total_duration'] / data['count']
            page_visit_stats[page_id] = f"{avg_duration:.2f} saniye (Ort.)"

    # En çok değiştirilen dosyalar
    modified_files_query = db.session.query(ActivityLog.modified_files_names).filter(ActivityLog.modified_files_names.isnot(None)).all()
    all_modified_files = []
    for files_json, in modified_files_query:
        try:
            all_modified_files.extend(json.loads(files_json))
        except (json.JSONDecodeError, TypeError):
            continue
    from collections import Counter
    top_modified_files = Counter(all_modified_files).most_common(10)

    # Dosya boyutu analizi
    file_size_analysis = {
        'pak_unpack': {'count': 0, 'total_size_mb': 0.0},
        'obb_unpack': {'count': 0, 'total_size_mb': 0.0}
    }
    size_query = db.session.query(ActivityLog.action, func.sum(ActivityLog.original_file_size_mb), func.count(ActivityLog.id))\
        .filter(ActivityLog.original_file_size_mb.isnot(None))\
        .group_by(ActivityLog.action).all()

    for action, total_size, count in size_query:
        if 'Unpack PAK' in action:
            file_size_analysis['pak_unpack']['count'] += count if count else 0
            file_size_analysis['pak_unpack']['total_size_mb'] += total_size if total_size else 0
        elif 'Unpack OBB' in action:
            file_size_analysis['obb_unpack']['count'] += count if count else 0
            file_size_analysis['obb_unpack']['total_size_mb'] += total_size if total_size else 0

    # --- Özellik Kullanım İstatistikleri ---
    feature_usage_query = db.session.query(FeatureUsageLog.feature_key, func.count(FeatureUsageLog.id))\
        .group_by(FeatureUsageLog.feature_key)\
        .order_by(desc(func.count(FeatureUsageLog.id))).limit(10).all()

    # features.py dosyasından özellik isimlerini alalım (Sadece key ve isim)
    from features import FEATURE_DATA
    feature_names_map = {item['key']: item['name'] for item in FEATURE_DATA}

    top_used_features = []
    for key, count in feature_usage_query:
        # Key'i, okunabilir isme çevirerek listeye ekle
        feature_name = feature_names_map.get(key, key)
        top_used_features.append({'name': feature_name, 'count': count})

    # --- Kullanıcı Analiz ve Potansiyel Hesaplama ---
    enriched_users = []
    potential_counts = {'Düşük': 0, 'Orta': 0, 'Yüksek': 0}

    # En aktif kullanıcı ve dil kullanımı için başlangıç değişkenleri
    most_active_user = {'name': 'N/A', 'actions': -1}
    lang_usage = {}

    for user in all_users:
        display_email = user.email
        if kurucu_user and user.id == kurucu_user.id and current_user.role != UserRole.kurucu:
            display_email = re.sub(r'^(.)[^@]+', r'\1***', user.email)

        total_actions = user_action_counts.get(user.id, 0)

        potential_score = (total_actions * 1) + (user.limit_hit_count * 5)

        if potential_score > 20: potential_category = 'Yüksek'
        elif potential_score > 5: potential_category = 'Orta'
        else: potential_category = 'Düşük'

        if user.status != 'deleted':
             potential_counts[potential_category] += 1

        # En aktif kullanıcıyı bulma
        if total_actions > most_active_user['actions']:
            most_active_user['name'] = user.username
            most_active_user['actions'] = total_actions

        # Dil kullanımını sayma
        lang = user.selected_language
        lang_usage[lang] = lang_usage.get(lang, 0) + 1

        enriched_users.append({
            'user': user,
            'email': display_email,
            'total_actions': total_actions,
            'potential_category': potential_category,
            'role_expiry_date': user.role_expiry_date.strftime('%Y-%m-%d %H:%M') if user.role_expiry_date else None,
            'backup_code': user.backup_code
        })

    # --- VİDEO İZLENME İSTATİSTİKLERİ ---
    video_stats = {}
    all_video_logs = VideoLog.query.all()

    # VIDEO_DATA'yı video.py'den import et
    from video import VIDEO_DATA

    # Video isimlerini kolay erişim için bir sözlüğe alalım
    video_titles = {v['key']: v['title_lang_key'] for v in VIDEO_DATA}

    # Her video için izlenme verilerini topla
    video_log_analysis = {}
    for log in all_video_logs:
        if log.video_key not in video_log_analysis:
            video_log_analysis[log.video_key] = {'total_watch_seconds': 0, 'view_count': 0}
        video_log_analysis[log.video_key]['total_watch_seconds'] += log.watch_time_seconds
        video_log_analysis[log.video_key]['view_count'] += 1 # Her log bir izlenme sayılabilir

    # Ortalama izlenme süresini hesapla
    for key, data in video_log_analysis.items():
        if data['view_count'] > 0:
            avg_seconds = data['total_watch_seconds'] / data['view_count']
            video_title = video_titles.get(key, key) # Başlığı al
            video_stats[video_title] = f"{avg_seconds / 60:.1f} dakika (Ort.)"

    # Genel İstatistikleri Hazırla
    stats = {
        'total_users': User.query.filter_by(status='active').count(),
        'total_actions': len(all_actions),
        'high_potential_count': potential_counts['Yüksek'],
        'file_size_analysis': file_size_analysis,
        'top_modified_files': top_modified_files,
        'most_active_user_name': most_active_user['name'],
        'page_visit_stats': page_visit_stats,
        'lang_usage': lang_usage,
        'video_watch_stats': video_stats,
        'top_used_features': top_used_features  # YENİ: Özellik kullanım istatistikleri
    }

    pie_chart_labels = list(potential_counts.keys())
    pie_chart_data = list(potential_counts.values())

    available_permissions = Permission.query.all() if current_user.role == UserRole.kurucu else []

    return render_template('admin.html',
                           enriched_users=enriched_users,
                           stats=stats,
                           pie_chart_labels=pie_chart_labels,
                           pie_chart_data=pie_chart_data,
                           available_permissions=available_permissions)

@app.route('/admin/get_intents')
@login_required
@admin_required
def get_intents():
    """
    Admin paneli için 'Onay Bekleyen' (Aktif) ve 'İşlenmiş' (Pasif)
    ödeme niyetlerini (PurchaseIntent) döndürür.
    """
    try:
        # Aktif Niyetler: Sadece OCR'den geçmiş, yönetici onayı bekleyenler
        active_intents_query = PurchaseIntent.query.options(
            joinedload(PurchaseIntent.user) # Kullanıcı verilerini tek sorguda çek
        ).filter(
            PurchaseIntent.status == 'WAITING_FOR_ADMIN'
        ).order_by(PurchaseIntent.created_at.asc()).all()

        # Pasif Niyetler: Tamamlanmış veya reddedilmiş olanlar (son 50)
        passive_intents_query = PurchaseIntent.query.options(
            joinedload(PurchaseIntent.user)
        ).filter(
            or_(PurchaseIntent.status == 'COMPLETED', PurchaseIntent.status == 'CANCELLED')
        ).order_by(PurchaseIntent.payment_notified_at.desc()).limit(50).all()

        def format_intent_data(intent):
            """Bir niyet kaydını JSON formatına çevirir."""
            user = intent.user
            # Varsayılan profil resmi mantığı
            default_pic = url_for('static', filename=f'images/{"free" if user.role.value == "ücretsiz" else user.role.value}.png')

            # Receipt URL oluşturma
            receipt_url = None
            if intent.receipt_image_path:
                # DB'deki yolu hem \ hem de / için düzelt
                relative_path = intent.receipt_image_path.replace('static\\', '').replace('static/', '')
                # Kalan \ işaretlerini / ile değiştir
                relative_path = relative_path.replace('\\', '/')
                receipt_url = url_for('static', filename=relative_path)

            return {
                "id": intent.id,
                "status": intent.status,
                "role": intent.role,
                "duration": intent.duration,
                "price": intent.price,
                "customer_name": intent.customer_name, # Artık bu Kullanıcı Adı
                # customer_phone SİLİNDİ
                "customer_email": intent.customer_email,
                "receipt_image_path": receipt_url,
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "current_role": user.role.value,
                    "profile_pic": user.profile_pic_url or default_pic
                }
            }

        active_intents = [format_intent_data(i) for i in active_intents_query]
        passive_intents = [format_intent_data(i) for i in passive_intents_query]

        return jsonify({
            "active_intents": active_intents,
            "passive_intents": passive_intents
        })

    except Exception as e:
        app.logger.error(f"Ödeme niyetleri (intents) alınırken hata: {e}")
        return jsonify({"error": "Veriler alınırken sunucuda bir hata oluştu."}), 500


@app.route('/admin/process_intent', methods=['POST'])
@login_required
@kurucu_required  # Sadece KURUCU bu işlemi yapabilir
def process_intent():
    """
    Bir ödeme niyetini onaylar (COMPLETED) veya reddeder (CANCELLED).
    Onaylanırsa, kullanıcıya rolü ve süreyi atar.
    """
    data = request.get_json()
    intent_id = data.get('intent_id')
    action = data.get('action') # 'approve' veya 'reject'

    if not intent_id or action not in ['approve', 'reject']:
        return jsonify({"error": "Eksik veya geçersiz veri."}), 400

    intent = PurchaseIntent.query.filter_by(
        id=intent_id,
        status='WAITING_FOR_ADMIN'
    ).first()

    if not intent:
        return jsonify({"error": "İşlem yapılacak niyet kaydı bulunamadı veya zaten işlenmiş."}), 404

    user_to_change = intent.user
    if not user_to_change:
         return jsonify({"error": "Niyetle ilişkili kullanıcı bulunamadı."}), 404

    try:
        if action == 'approve':
            # 1. Rolü ve Süreyi Ata
            new_role_enum = UserRole(intent.role)
            duration_key = intent.duration
            new_expiry_date = None
            duration_text_for_log = "Kalıcı (Süresiz)"

            duration_map = {
                '1h': timedelta(hours=1), '2d': timedelta(days=2), '1w': timedelta(weeks=1),
                '1m': timedelta(days=30), '3m': timedelta(days=90), '5m': timedelta(days=150),
                '1y': timedelta(days=365)
            }

            if duration_key in duration_map:
                new_expiry_date = datetime.utcnow() + duration_map[duration_key]
                duration_text_for_log = f"Süre: {duration_key}"
            elif duration_key == 'permanent':
                new_expiry_date = None # Kalıcı
            else:
                # Geçersiz bir süre varsa (örn: '1w' yerine '1w' gelmişse)
                 return jsonify({"error": f"Geçersiz süre formatı: {duration_key}"}), 400

            # Kullanıcı bilgilerini güncelle
            old_role = user_to_change.role.value
            user_to_change.role = new_role_enum
            user_to_change.role_expiry_date = new_expiry_date
            user_to_change.action_count = 0 # Limitlerini sıfırla
            user_to_change.last_action_time = None

            # 2. Niyetin durumunu güncelle
            intent.status = 'COMPLETED'

            db.session.commit()

            # 3. Logla
            log_message = f"'{user_to_change.username}' kullanıcısının ödemesini ONAYLADI. Rol: '{intent.role}', {duration_text_for_log}"
            record_log(current_user, log_message, "SUBSCRIPTION_ADMIN")
            record_log(user_to_change, f"Yönetici rol ataması yaptı. Yeni rol: '{intent.role}', {duration_text_for_log}", "SUBSCRIPTION")

            return jsonify({"success": True, "message": "Ödeme onaylandı ve rol atandı."})

        elif action == 'reject':
            # 1. Niyetin durumunu 'CANCELLED' (Reddedildi/İptal Edildi) olarak ayarla
            intent.status = 'CANCELLED'
            db.session.commit()

            # 2. Logla
            log_message = f"'{user_to_change.username}' kullanıcısının ödemesini REDDETTİ. (Rol: {intent.role})"
            record_log(current_user, log_message, "SUBSCRIPTION_ADMIN")

            return jsonify({"success": True, "message": "Ödeme reddedildi."})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Niyet işlenirken (Intent ID: {intent_id}) kritik hata: {e}")
        return jsonify({"error": "İşlem sırasında beklenmedik bir sunucu hatası oluştu."}), 500

# --- YENİ: ADMIN İÇİN CİHAZ YÖNETİMİ ROTALARI ---
@app.route('/admin/get_devices/<int:user_id>')
@login_required
@usta_admin_required
def get_user_devices(user_id):
    user = db.session.get(User, user_id)
    if not user:
        app.logger.error(f"Cihaz sorgusu başarısız: Kullanıcı ID {user_id} bulunamadı.")
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    # --- HATA AYIKLAMA İÇİN LOGLAMA ---
    # Fonksiyona girdiğimizde veritabanındaki değerlerin ne olduğunu görelim.
    app.logger.info(f"Kullanıcı '{user.username}' için cihazlar sorgulanıyor...")
    app.logger.info(f"  -> Slot 1 Fingerprint DB'de: '{user.device_1_fingerprint}' (Tipi: {type(user.device_1_fingerprint)})")
    app.logger.info(f"  -> Slot 2 Fingerprint DB'de: '{user.device_2_fingerprint}' (Tipi: {type(user.device_2_fingerprint)})")

    if current_user.role == UserRole.usta_admin and user.role in [UserRole.usta_admin, UserRole.kurucu]:
        return jsonify({"error": "Bu kullanıcının cihazlarını görme yetkiniz yok."}), 403

    devices_data = []

    # Düzeltme: Kontrolü daha açık hale getirelim -> None değilse VE boş string değilse
    if user.device_1_fingerprint is not None and user.device_1_fingerprint != '':
        app.logger.info("Slot 1 dolu olarak algılandı, listeye ekleniyor.")
        devices_data.append({
            "slot_index": 1,
            "name": user.device_1_name or "Bilinmeyen Cihaz 1",
            "last_login": user.device_1_last_login.strftime('%Y-%m-%d %H:%M:%S') if user.device_1_last_login else "N/A"
        })

    if user.device_2_fingerprint is not None and user.device_2_fingerprint != '':
        app.logger.info("Slot 2 dolu olarak algılandı, listeye ekleniyor.")
        devices_data.append({
            "slot_index": 2,
            "name": user.device_2_name or "Bilinmeyen Cihaz 2",
            "last_login": user.device_2_last_login.strftime('%Y-%m-%d %H:%M:%S') if user.device_2_last_login else "N/A"
        })

    app.logger.info(f"Sonuç olarak frontend'e {len(devices_data)} cihaz gönderiliyor.")
    return jsonify(devices_data)

@app.route('/admin/delete_device', methods=['POST'])
@login_required
@kurucu_required
def delete_device():
    user_id = request.json.get('user_id')
    slot_index = request.json.get('slot_index')

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    try:
        if slot_index == 1:
            user.device_1_fingerprint = None
            user.device_1_name = None
            user.device_1_last_login = None
            slot_name_for_log = "1. cihaz slotu"
        elif slot_index == 2:
            user.device_2_fingerprint = None
            user.device_2_name = None
            user.device_2_last_login = None
            slot_name_for_log = "2. cihaz slotu"
        else:
            return jsonify({"error": "Geçersiz cihaz slotu"}), 400

        # !!! EN ÖNEMLİ DEĞİŞİKLİK !!!
        # Aşağıdaki satır, aktif olan telefon oturumu gibi diğer tüm oturumları sonlandırdığı için kaldırıldı.
        # user.session_token = str(uuid.uuid4())

        # Sadece cihaz slotuyla ilgili değişiklikleri veritabanına kaydet.
        db.session.commit()

        record_log(current_user, f"'{user.username}' kullanıcısının {slot_name_for_log}nu boşalttı.")

        # Flash mesajı, artık oturumun sonlandırılmadığını belirtecek şekilde güncellendi.
        flash(f"{user.username} kullanıcısının cihazı başarıyla kaldırıldı. Kullanıcının aktif oturumu devam ediyor.", "success")
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Cihaz silinirken hata: {e}")
        return jsonify({"error": "Sunucu hatası"}), 500

### DÜZELTME: Log butonu sorunu giderildi. Artık token kontrolü yerine standart admin yetkisi kontrol ediliyor. ###
@app.route('/admin/get_logs/<int:user_id>')
@login_required
@admin_required
def get_user_logs(user_id):
    user_to_view = db.session.get(User, user_id)
    if not user_to_view:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    role_hierarchy = {
        'ücretsiz': 0, 'premium': 1, 'dev': 2,
        'caylak_admin': 3, 'usta_admin': 4, 'kurucu': 5
    }

    current_user_level = role_hierarchy.get(current_user.role.value, -1)
    target_user_level = role_hierarchy.get(user_to_view.role.value, -1)

    # DÜZELTME: Kural, '<' yerine '<=' olarak güncellendi.
    # Artık bir admin, kendi seviyesindeki başka bir adminin logunu göremez.
    if current_user.role != UserRole.kurucu and current_user_level <= target_user_level:
        return jsonify({"error": "Bu kullanıcının loglarını görme yetkiniz yok."}), 403

    logs = ActivityLog.query.filter_by(user_id=user_id).order_by(ActivityLog.timestamp.desc()).limit(100).all()
    log_data = [{"timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "action": log.action} for log in logs]
    return jsonify(log_data)

### TAM GÜNCEL HALİ ###
@app.route('/admin/change_role', methods=['POST'])
@login_required
@usta_admin_required # Sadece Usta Admin ve Kurucu bu rotaya erişebilir.
def change_role():
    # --- 1. GÜVENLİ VERİ ALIMI VE DOĞRULAMA ---
    user_id_str = request.form.get('user_id')
    new_role_str = request.form.get('role')
    duration = request.form.get('duration')

    if not user_id_str or not user_id_str.isdigit():
        flash("Geçersiz veya eksik kullanıcı ID'si.", "danger")
        return redirect(url_for('admin_dashboard'))

    user_to_change = db.session.get(User, int(user_id_str))
    if not user_to_change:
        flash("Değiştirilecek kullanıcı bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    try:
        new_role_enum = UserRole(new_role_str)
    except ValueError:
        flash("Geçersiz bir rol seçildi.", "danger")
        return redirect(url_for('admin_dashboard'))

    # --- 2. KRİTİK GÜVENLİK VE YETKİ KONTROLLERİ ---

    # Kendi rolünü değiştirme engeli (Kurucu hariç)
    if user_to_change.id == current_user.id and current_user.role != UserRole.kurucu:
        flash("Kendi rolünüzü değiştiremezsiniz.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Kurucunun rolü asla değiştirilemez
    if user_to_change.role == UserRole.kurucu:
        flash("Kurucunun rolü değiştirilemez.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Usta Admin, kendisiyle aynı seviyedeki veya üstündeki birini değiştiremez
    if current_user.role == UserRole.usta_admin and user_to_change.role in [UserRole.usta_admin, UserRole.kurucu]:
        flash("Başka bir yöneticinin veya kurucunun rolünü değiştirme yetkiniz yok.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Sadece Kurucu, başka bir kullanıcıyı yönetici yapabilir
    if new_role_enum in [UserRole.caylak_admin, UserRole.usta_admin, UserRole.kurucu] and current_user.role != UserRole.kurucu:
        flash("Sadece Kurucu, başka bir kullanıcıyı yönetici yapabilir.", "danger")
        return redirect(url_for('admin_dashboard'))

    # --- 3. SÜRE HESAPLAMA MANTIĞI ---
    new_expiry_date = None
    duration_text = "Süresiz" # Loglama için varsayılan metin

    roles_with_duration = [UserRole.premium, UserRole.dev, UserRole.caylak_admin, UserRole.usta_admin]
    if new_role_enum in roles_with_duration:
        if duration == 'permanent':
            new_expiry_date = None
            duration_text = "Kalıcı (Süresiz)"
        else:
            duration_map = {
                '1h': timedelta(hours=1), '2d': timedelta(days=2), '1w': timedelta(weeks=1),
                '1m': timedelta(days=30), '3m': timedelta(days=90), '5m': timedelta(days=150),
                '1y': timedelta(days=365)
            }
            if duration in duration_map:
                new_expiry_date = datetime.utcnow() + duration_map[duration]
                duration_text = f"Süre: {duration}" # Log için süreyi ayarla
            else:
                flash("Geçerli bir rol süresi seçin.", "danger")
                return redirect(url_for('admin_dashboard'))

    # --- 4. VERİTABANI İŞLEMİ VE HATA YÖNETİMİ ---
    try:
        old_role = user_to_change.role.value
        user_to_change.role = new_role_enum
        user_to_change.role_expiry_date = new_expiry_date

        # Rolü değişen kullanıcının limitlerini sıfırla
        user_to_change.action_count = 0
        user_to_change.last_action_time = None

        db.session.commit()

        # Detaylı log kaydı oluştur
        record_log(current_user, f"'{user_to_change.username}' kullanıcısının rolünü '{old_role}' -> '{new_role_str}' olarak değiştirdi. ({duration_text})")
        flash(f"{user_to_change.username} kullanıcısının rolü başarıyla güncellendi.", "success")

    except Exception as e:
        db.session.rollback() # Hata durumunda işlemi geri al
        app.logger.error(f"Rol değiştirilirken kritik hata: {e}")
        flash("Rol güncellenirken beklenmedik bir sunucu hatası oluştu.", "danger")

    return redirect(url_for('admin_dashboard'))

# YENİ: Acil Durum Silme (Çöp Kutusu) Rotası
@app.route('/admin/emergency_delete', methods=['POST'])
@login_required
@permission_required('emergency_delete') # Bu işlemi ya kurucu ya da 'emergency_delete' yetkisine sahip biri yapabilir.
def emergency_delete_user():
    user_id = request.json.get('user_id')

    # --- 1. GÜVENLİ GİRİŞ DOĞRULAMASI ---
    if not user_id:
        return jsonify({"error": "Kullanıcı ID'si belirtilmedi."}), 400 # Bad Request

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Geçersiz kullanıcı ID formatı."}), 400

    user_to_delete = db.session.get(User, user_id_int)

    # --- 2. YETKİ VE KURAL KONTROLLERİ ---
    if not user_to_delete:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404 # Not Found

    if user_to_delete.role == UserRole.kurucu:
        return jsonify({"error": "Kurucu hesabı silinemez."}), 403 # Forbidden

    if user_to_delete.id == current_user.id:
        return jsonify({"error": "Kendinizi devre dışı bırakamazsınız."}), 403 # Forbidden

    # --- 3. VERİTABANI İŞLEMİ VE HATA YÖNETİMİ ---
    try:
        # 1. Kullanıcının statüsünü 'deleted' yap.
        user_to_delete.status = 'deleted'
        # 2. Aktif oturumunu geçersiz kılmak için session_token'ı değiştir.
        user_to_delete.session_token = str(uuid.uuid4())

        db.session.commit()

        # 3. Kimin sildiğini ve kimi sildiğini detaylı logla.
        record_log(current_user, f"Acil müdahale ile '{user_to_delete.username}' kullanıcısını sildi (devre dışı bıraktı).")

        # 4. Arayüze hangi kullanıcının devre dışı bırakıldığını bildir.
        return jsonify({"success": True, "message": f"'{user_to_delete.username}' kullanıcısı başarıyla devre dışı bırakıldı."})

    except Exception as e:
        db.session.rollback() # Hata durumunda işlemi geri al.
        app.logger.error(f"Acil silme hatası (Hedef ID: {user_id_int}): {e}")
        return jsonify({"error": "İşlem sırasında beklenmedik bir sunucu hatası oluştu."}), 500 # Internal Server Error


# YENİ: Yetki Verme (+) Rotası
@app.route('/admin/grant_permission', methods=['POST'])
@login_required
@kurucu_required # Bu işlemi sadece kurucu yapabilir.
def grant_permission():
    # --- 1. GÜVENLİ VERİ ALIMI ---
    user_id_str = request.form.get('user_id')
    permission_id_str = request.form.get('permission_id')

    if not all([user_id_str, permission_id_str, user_id_str.isdigit(), permission_id_str.isdigit()]):
        flash("Geçersiz veya eksik bilgi gönderildi.", "danger")
        return redirect(url_for('admin_dashboard'))

    user = db.session.get(User, int(user_id_str))
    permission = db.session.get(Permission, int(permission_id_str))

    # --- 2. DETAYLI DOĞRULAMA VE HATA MESAJLARI ---
    if not user or not permission:
        flash("Kullanıcı veya yetki bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Özel yetkilerin sadece admin rollerine atanabilmesini sağla
    if user.role not in [UserRole.caylak_admin, UserRole.usta_admin]:
        flash("Özel yetkiler sadece yönetici rollerine atanabilir.", "danger")
        return redirect(url_for('admin_dashboard'))

    # --- 3. İŞLEM MANTIĞI VE LOGLAMA ---
    if permission in user.permissions:
        flash(f"'{user.username}' kullanıcısı zaten '{permission.name}' yetkisine sahip.", "info")
    else:
        try:
            user.permissions.append(permission)
            db.session.commit()

            # KRİTİK: Yetki verme işlemini logla
            record_log(current_user, f"'{user.username}' kullanıcısına '{permission.name}' yetkisini verdi.")
            flash(f"'{permission.name}' yetkisi '{user.username}' kullanıcısına başarıyla verildi.", "success")

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Yetki verilirken hata oluştu: {e}")
            flash("Yetki verilirken beklenmedik bir sunucu hatası oluştu.", "danger")

    return redirect(url_for('admin_dashboard'))


# YENİ: Yetki Geri Alma (x) Rotası
@app.route('/admin/revoke_permission', methods=['POST'])
@login_required
@kurucu_required # Bu işlemi sadece kurucu yapabilir.
def revoke_permission():
    # --- 1. GÜVENLİ VERİ ALIMI ---
    user_id_str = request.form.get('user_id')
    permission_id_str = request.form.get('permission_id')

    if not all([user_id_str, permission_id_str, user_id_str.isdigit(), permission_id_str.isdigit()]):
        flash("Geçersiz veya eksik bilgi gönderildi.", "danger")
        return redirect(url_for('admin_dashboard'))

    user = db.session.get(User, int(user_id_str))
    permission = db.session.get(Permission, int(permission_id_str))

    # --- 2. DETAYLI DOĞRULAMA VE HATA MESAJLARI ---
    if not user or not permission:
        flash("Kullanıcı veya yetki bulunamadı.", "danger")
        return redirect(url_for('admin_dashboard'))

    # --- 3. İŞLEM MANTIĞI VE LOGLAMA ---
    if permission not in user.permissions:
        flash(f"'{user.username}' kullanıcısının zaten '{permission.name}' yetkisi bulunmuyor.", "info")
    else:
        try:
            user.permissions.remove(permission)
            db.session.commit()

            # KRİTİK: Yetki kaldırma işlemini logla
            record_log(current_user, f"'{user.username}' kullanıcısından '{permission.name}' yetkisini aldı.")
            flash(f"'{user.username}' kullanıcısından '{permission.name}' yetkisi başarıyla kaldırıldı.", "success")

        except Exception as e:
            db.session.rollback() # Hata durumunda işlemi geri al
            app.logger.error(f"Yetki kaldırılırken hata oluştu: {e}")
            flash("Yetki kaldırılırken beklenmedik bir sunucu hatası oluştu.", "danger")

    return redirect(url_for('admin_dashboard'))

# app.py

# ... önceki kodlar ...

@app.route('/unpack', methods=['POST'])
@login_required
@check_action_limit
def unpack_pak_file():
    # === SUNUCU TARAFLI BAKIM KONTROLÜ ===
    if PAK_UNPACK_MAINTENANCE:
        app.logger.warning(f"Kullanıcı {current_user.username} bakımdaki Unpack PAK aracını kullanmaya çalıştı.")
        return jsonify({"error": {"key": "section_under_maintenance"}}), 503
    # === KONTROL SONU ===

    if 'pakFile' not in request.files:
        return jsonify({"error": {"key": "file_not_found"}}), 400

    file = request.files['pakFile']
    if not file.filename.endswith('.pak'):
        return jsonify({"error": {"key": "invalid_pak_file"}}), 400

    user_limits = get_limits_for_user(current_user)

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file_size_mb = file_size / 1024**2
    file.seek(0)

    if file_size > user_limits['pak_max_size']:
        limit_mb = user_limits['pak_max_size'] // (1024 * 1024)
        record_log(current_user, f"Unpack PAK denemesi başarısız: Boyut limiti aşıldı.", 'PAK', file.filename, file_size_mb)
        return jsonify({"error": {"key": "error_pak_size_limit_role", "limit": f"{limit_mb} MB"}}), 413

    request_id = str(uuid.uuid4())
    upload_dir = UPLOAD_FOLDER / request_id
    result_dir = RESULT_FOLDER / request_id
    try:
        upload_dir.mkdir()
        result_dir.mkdir()
        pak_path = upload_dir / secure_filename(file.filename)
        file.save(pak_path)
        pak = pak_parser.TencentPakFile(pak_path)
        pak.dump(result_dir)

        zip_filename = f"{request_id}_unpacked"
        zip_path_no_ext = RESULT_FOLDER / zip_filename
        shutil.make_archive(str(zip_path_no_ext), 'zip', result_dir)

        final_zip_path = Path(app.config['RESULT_FOLDER']).resolve() / f"{zip_filename}.zip"
        temp_file = TemporaryFile(user_id=current_user.id, file_path=str(final_zip_path), request_id=request_id)
        db.session.add(temp_file)
        db.session.commit()

        download_url = f"/download/{zip_filename}.zip"
        record_log(current_user, f"Unpack PAK: '{file.filename}' işlemi başarıyla tamamlandı.", 'PAK', file.filename, file_size_mb)
        return jsonify({"success": True, "downloadUrl": download_url, "summary": "Dosya başarıyla açıldı!"})
    except (struct.error, AssertionError, ValueError, KeyError):
        record_log(current_user, f"Unpack PAK işlemi başarısız: '{file.filename}' dosyası geçersiz veya bozuk.", 'PAK', file.filename, file_size_mb)
        return jsonify({"error": {"key": "pak_decryption_failed"}}), 400
    except Exception as e:
        record_log(current_user, "Unpack PAK işlemi başarısız: Beklenmedik sunucu hatası.")
        app.logger.error(f"Unpack sırasında hata: {e}")
        traceback.print_exc()
        return jsonify({"error": {"key": "server_error_on_unpack"}}), 500
    finally:
        # Temizlik işlemleri - hata olsa da olmasa da çalışır
        shutil.rmtree(upload_dir, ignore_errors=True)
        shutil.rmtree(result_dir, ignore_errors=True)

@app.route('/repack', methods=['POST'])
@login_required
@check_action_limit
def repack_pak_file():
    # === SUNUCU TARAFLI BAKIM KONTROLÜ ===
    if PAK_RPACK_MAINTENANCE:
        app.logger.warning(f"Kullanıcı {current_user.username} bakımdaki Repack PAK aracını kullanmaya çalıştı.")
        return jsonify({"error": {"key": "section_under_maintenance"}}), 503
    # === KONTROL SONU ===

    if 'originalPakFile' not in request.files or 'modifiedFiles' not in request.files:
        return jsonify({"error": {"key": "missing_files"}}), 400

    original_pak = request.files['originalPakFile']
    modified_files = request.files.getlist('modifiedFiles')

    user_limits = get_limits_for_user(current_user)

    original_pak.seek(0, os.SEEK_END)
    file_size = original_pak.tell()
    file_size_mb = file_size / 1024**2
    original_pak.seek(0)

    if file_size > user_limits['pak_max_size']:
        limit_mb = user_limits['pak_max_size'] // (1024 * 1024)
        record_log(current_user, f"Repack PAK denemesi başarısız: Orijinal dosya boyutu limiti aşıldı.", 'PAK', original_pak.filename, file_size_mb)
        return jsonify({"error": {"key": "error_pak_size_limit_role", "limit": f"{limit_mb} MB"}}), 413

    total_modified_size = sum(f.seek(0, os.SEEK_END) or f.tell() for f in modified_files)
    [f.seek(0) for f in modified_files] # Dosya işaretçilerini başa al

    if total_modified_size > user_limits['repack_pak_modified_max_size']:
        limit_mb = user_limits['repack_pak_modified_max_size'] // (1024 * 1024)
        record_log(current_user, f"Repack PAK denemesi başarısız: Değiştirilen dosya boyutu limiti aşıldı.", 'PAK', original_pak.filename, file_size_mb)
        return jsonify({"error": {"key": "error_modified_pak_size_limit_role", "limit": f"{limit_mb} MB"}}), 413

    modified_names = [f.filename for f in modified_files]
    modified_names_json = json.dumps(modified_names)

    request_id = str(uuid.uuid4())
    upload_dir = UPLOAD_FOLDER / request_id
    try:
        upload_dir.mkdir()
        original_pak_path = upload_dir / secure_filename(original_pak.filename)
        original_pak.save(original_pak_path)
        modified_paths = [upload_dir / secure_filename(f.filename) for f in modified_files]
        for file, path in zip(modified_files, modified_paths):
            file.save(path)

        output_pak_filename = f"{request_id}_repacked.pak"
        output_pak_path = RESULT_FOLDER / output_pak_filename
        stats = repacker_engine.repack_pak(original_pak_path, modified_paths, output_pak_path)

        final_pak_path = Path(app.config['RESULT_FOLDER']).resolve() / output_pak_filename
        temp_file = TemporaryFile(user_id=current_user.id, file_path=str(final_pak_path), request_id=request_id)
        db.session.add(temp_file)
        db.session.commit()

        summary = f"Repack tamamlandı! Değiştirilen: {stats['replaced']}"
        download_url = f"/download/{output_pak_filename}"
        record_log(current_user, f"Repack PAK: '{original_pak.filename}' işlemi başarıyla tamamlandı.",
                   'PAK', original_pak.filename, file_size_mb, len(modified_files), modified_names_json)
        return jsonify({"success": True, "downloadUrl": download_url, "summary": summary})
    except (struct.error, AssertionError, ValueError):
        record_log(current_user, f"Repack PAK işlemi başarısız: '{original_pak.filename}' dosyası geçersiz.",
                   'PAK', original_pak.filename, file_size_mb, len(modified_files), modified_names_json)
        return jsonify({"error": {"key": "invalid_pak_or_modified_files", "message": "Orijinal PAK dosyası veya değiştirilen dosyalar geçersiz."}}), 400
    except Exception as e:
        record_log(current_user, "Repack PAK işlemi başarısız: Beklenmedik sunucu hatası.")
        app.logger.error(f"Repack sırasında hata: {e}")
        traceback.print_exc()
        return jsonify({"error": {"key": "server_error_on_repack", "message": "Dosyalar yeniden paketlenirken sunucuda bir hata oluştu."}}), 500
    finally:
        # Temizlik işlemleri - hata olsa da olmasa da çalışır
        shutil.rmtree(upload_dir, ignore_errors=True)

@app.route('/unpack_obb', methods=['POST'])
@login_required
@check_action_limit
def unpack_obb_file():
    if 'obbFile' not in request.files:
        return jsonify({"error": {"key": "file_not_found"}}), 400

    file = request.files['obbFile']

    user_limits = get_limits_for_user(current_user)

    request_id = str(uuid.uuid4())
    upload_dir = UPLOAD_FOLDER / request_id
    try:
        upload_dir.mkdir()
        obb_path = upload_dir / secure_filename(file.filename)
        file.save(obb_path)

        file_size = obb_path.stat().st_size
        file_size_mb = file_size / 1024**2

        if file_size > user_limits['obb_max_size']:
            limit_mb = user_limits['obb_max_size'] // (1024 * 1024)
            record_log(current_user, f"Unpack OBB denemesi başarısız: Boyut limiti aşıldı.", 'OBB', file.filename, file_size_mb)
            return jsonify({"error": {"key": "error_obb_size_limit_role", "limit": f"{limit_mb} MB"}}), 413

        zip_filename = f"{request_id}_{Path(file.filename).stem}_unpacked"
        zip_path_no_ext = RESULT_FOLDER / zip_filename
        obb_unpack.unpack_and_zip(obb_path, zip_path_no_ext)

        final_zip_path = Path(app.config['RESULT_FOLDER']).resolve() / f"{zip_filename}.zip"
        temp_file = TemporaryFile(user_id=current_user.id, file_path=str(final_zip_path), request_id=request_id)
        db.session.add(temp_file)
        db.session.commit()

        download_url = f"/download/{zip_filename}.zip"
        record_log(current_user, f"Unpack OBB: '{file.filename}' işlemi başarıyla tamamlandı.", 'OBB', file.filename, file_size_mb)
        return jsonify({"success": True, "downloadUrl": download_url, "summary": "OBB dosyası başarıyla açıldı!"})
    except Exception as e:
        record_log(current_user, "Unpack OBB işlemi başarısız: Beklenmedik sunucu hatası.")
        app.logger.error(f"Unpack OBB sırasında hata: {e}")
        traceback.print_exc()
        return jsonify({"error": {"key": "server_error_on_obb_unpack", "message": "OBB dosyası işlenirken bir hata oluştu."}}), 500
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)

@app.route('/repack_obb', methods=['POST'])
@login_required
@check_action_limit
def repack_obb_file():
    if 'originalObbFile' not in request.files or 'modifiedFiles' not in request.files:
        return jsonify({"error": {"key": "missing_files"}}), 400

    original_obb = request.files['originalObbFile']
    modified_files = request.files.getlist('modifiedFiles')

    user_limits = get_limits_for_user(current_user)

    request_id = str(uuid.uuid4())
    upload_dir = UPLOAD_FOLDER / request_id
    try:
        upload_dir.mkdir()
        original_obb_path = upload_dir / secure_filename(original_obb.filename)
        original_obb.save(original_obb_path)

        file_size = original_obb_path.stat().st_size
        file_size_mb = file_size / 1024**2

        if file_size > user_limits['obb_max_size']:
            limit_mb = user_limits['obb_max_size'] // (1024 * 1024)
            record_log(current_user, f"Repack OBB denemesi başarısız: Orijinal dosya boyutu limiti aşıldı.", 'OBB', original_obb.filename, file_size_mb)
            return jsonify({"error": {"key": "error_obb_size_limit_role", "limit": f"{limit_mb} MB"}}), 413

        # Değiştirilen dosyaları kaydet ve toplam boyutlarını hesapla
        modified_paths = []
        total_modified_size = 0
        for f in modified_files:
            path = upload_dir / secure_filename(f.filename)
            f.save(path)
            total_modified_size += path.stat().st_size
            modified_paths.append(path)

        if total_modified_size > user_limits['repack_obb_modified_max_size']:
            limit_mb = user_limits['repack_obb_modified_max_size'] // (1024 * 1024)
            # 1 GB ise GB olarak göster
            if limit_mb >= 1024:
                limit_str = f"{limit_mb / 1024:.1f} GB"
            else:
                limit_str = f"{limit_mb} MB"
            record_log(current_user, f"Repack OBB denemesi başarısız: Değiştirilen dosya boyutu limiti aşıldı.", 'OBB', original_obb.filename, file_size_mb)
            return jsonify({"error": {"key": "error_modified_obb_size_limit_role", "limit": limit_str}}), 413

        modified_names = [f.filename for f in modified_files]
        modified_names_json = json.dumps(modified_names)

        output_obb_filename = f"{request_id}_{original_obb.filename}"
        output_obb_path = RESULT_FOLDER / output_obb_filename
        obb_repack.repack_and_process(original_obb_path, modified_paths, output_obb_path)

        final_obb_path = Path(app.config['RESULT_FOLDER']).resolve() / output_obb_filename
        temp_file = TemporaryFile(user_id=current_user.id, file_path=str(final_obb_path), request_id=request_id)
        db.session.add(temp_file)
        db.session.commit()

        summary = f"OBB Repack tamamlandı! {len(modified_files)} dosya başarıyla değiştirildi."
        download_url = f"/download/{output_obb_filename}"
        record_log(current_user, f"Repack OBB: '{original_obb.filename}' işlemi başarıyla tamamlandı.",
                   'OBB', original_obb.filename, file_size_mb, len(modified_files), modified_names_json)
        return jsonify({"success": True, "downloadUrl": download_url, "summary": summary})
    except Exception as e:
        record_log(current_user, "Repack OBB işlemi başarısız: Beklenmedik sunucu hatası.")
        app.logger.error(f"Repack OBB sırasında hata: {e}")
        traceback.print_exc()
        return jsonify({"error": {"key": "server_error_on_obb_repack", "message": "OBB dosyası yeniden paketlenirken bir hata oluştu."}}), 500
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)

def delayed_cleanup(file_id, file_path):
    """
    Belirtilen ID'ye sahip veritabanı kaydını ve belirtilen yoldaki dosyayı siler.
    Bu fonksiyon APScheduler tarafından çağrılmak üzere tasarlanmıştır.
    """
    # Scheduler ayrı bir thread'de çalıştığı için uygulama bağlamına ihtiyacı var.
    with app.app_context():
        app.logger.info(f"Zamanlanmış temizlik görevi başladı: {file_path}")
        try:
            record_to_delete = db.session.get(TemporaryFile, file_id)
            if record_to_delete:
                db.session.delete(record_to_delete)
                db.session.commit()
                app.logger.info(f"Veritabanı kaydı (ID: {file_id}) zamanlayıcı tarafından silindi.")
            else:
                app.logger.warning(f"Zamanlanmış görev çalıştı ama veritabanı kaydı bulunamadı: ID {file_id}")

            # Fiziksel dosyayı sil
            if os.path.exists(file_path):
                os.remove(file_path)
                app.logger.info(f"Fiziksel dosya zamanlayıcı tarafından silindi: {file_path}")
            else:
                app.logger.warning(f"Zamanlanmış görev çalıştı ama fiziksel dosya bulunamadı: {file_path}")

        except Exception as e:
            app.logger.error(f"Zamanlanmış temizlik görevinde KRİTİK HATA: {e}", exc_info=True)


@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    request_id_match = re.match(r'^([a-f0-9\-]+)', filename)
    # Hata durumunda frontend'in anlayacağı bir JSON yanıtı döndür
    if not request_id_match:
        return jsonify({"error": {"key": "download_link_invalid_format", "message": "Geçersiz indirme linki formatı."}}), 400

    request_id = request_id_match.group(1)

    temp_file = TemporaryFile.query.filter_by(request_id=request_id).first()

    # Kullanıcı kontrolü eklenmiş hali
    if not temp_file or temp_file.user_id != current_user.id:
        # Hata durumunda frontend'in anlayacağı bir JSON yanıtı döndür
        return jsonify({"error": {"key": "download_link_expired_or_invalid", "message": "İndirme linki geçersiz veya zaman aşımına uğramış."}}), 404

    # --- GÜVENLİK DÜZELTMESİ BURADA BAŞLIYOR ---

    # 1. Kullanıcının URL'den gönderdiği tehlikeli 'filename' yerine,
    #    veritabanından aldığımız güvenli ve tam dosya yolunu kullanalım.
    file_path_from_db = Path(temp_file.file_path)

    # 2. Bu güvenli yoldan sadece dosyanın adını alalım.
    secure_filename_to_serve = file_path_from_db.name

    # 3. Dosyanın hala sunucuda var olduğunu kontrol edelim.
    if not file_path_from_db.exists():
        # Dosya yoksa, veritabanında kalmış olabilecek "öksüz" kaydı da temizleyelim.
        with app.app_context():
            stale_record = db.session.get(TemporaryFile, temp_file.id)
            if stale_record:
                db.session.delete(stale_record)
                db.session.commit()
        # Hata durumunda frontend'in anlayacağı bir JSON yanıtı döndür (410 "Gone" daha doğru bir koddur)
        return jsonify({"error": {"key": "download_link_expired_file_gone", "message": "İndirme linkinin süresi dolmuş."}}), 410

    # --- AÇIĞI KAPATAN MANTIK ---
    try:
        # Her görev için dosyanın UUID'sini içeren benzersiz bir ID oluştur.
        job_id = f'cleanup_{request_id}'

        run_time = datetime.now() + timedelta(seconds=60)
        scheduler.add_job(
            func=delayed_cleanup,
            trigger='date',
            run_date=run_time,
            args=[temp_file.id, str(file_path_from_db)],
            id=job_id # Benzersiz ID'yi burada kullanıyoruz
        )
        app.logger.info(f"Dosya için 60 saniye sonrasına temizlik görevi kuruldu: {job_id}")

    except ConflictingIdError:
        # Eğer scheduler "bu ID zaten var" hatası verirse, onu yakalayıp görmezden gel.
        app.logger.info(f"Temizlik görevi zaten mevcut. Yeni görev kurulmadı: {job_id}")

    except Exception as e:
        # Diğer olası hataları logla.
        app.logger.error(f"Temizlik görevi ZAMANLANIRKEN hata oluştu: {e}")

    record_log(current_user, f"İndirme: '{secure_filename_to_serve}' dosyasını indirmeye başladı.")

    # 4. send_from_directory fonksiyonuna GÜVENLİ dosya adını verelim.
    #    Kullanıcının gönderdiği orijinal 'filename' değişkenini ASLA kullanmayalım.
    return send_from_directory(
        app.config['RESULT_FOLDER'],
        secure_filename_to_serve,
        as_attachment=True
    )

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'

    nonce = getattr(g, 'csp_nonce', '')

    # YENİ EKLEME: '127.0.0.1:55555' adresini connect-src'ye ekliyoruz.
    # Bu, tarayıcının yerel Bridge uygulamasına bağlanmasına izin verir.
    LOCAL_BRIDGE_URL = f"http://127.0.0.1:{LOCAL_BRIDGE_PORT}" # 55555 portunu kullansın diye

    csp_policy = [
        "default-src 'self'",

        f"script-src 'self' 'nonce-{nonce}' https://cdn.socket.io https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://www.youtube.com",

        # --- GÜNCELLENMİŞ SATIR ---
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://www.gstatic.com",
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",

        # GÜNCELLEME: LOCAL_BRIDGE_URL'yi 'connect-src' içine ekliyoruz
        "img-src 'self' data: blob: https://img.youtube.com https://i.ytimg.com",

        f"connect-src 'self' wss: ws: https://cdn.jsdelivr.net https://cdn.socket.io {LOCAL_BRIDGE_URL}", # <<< BURASI GÜNCELLENDİ

        "frame-src 'self' https://www.youtube.com"
    ]
    response.headers['Content-Security-Policy'] = "; ".join(csp_policy)
    return response

LOCAL_BRIDGE_PORT = 55555

@app.route('/admin/reported_posts', methods=['GET'])
@login_required
@admin_required
def admin_get_reported_posts():
    try:
        active_reports = PostReport.query.options(
            joinedload(PostReport.reporter),
            joinedload(PostReport.post).joinedload(Post.user)
        ).filter(PostReport.status == 'pending').order_by(PostReport.timestamp.desc()).all()

        inactive_reports = PostReport.query.options(
            joinedload(PostReport.reporter),
            joinedload(PostReport.post).joinedload(Post.user),
            joinedload(PostReport.processed_by_admin)
        ).filter(PostReport.decision.isnot(None)).order_by(PostReport.processed_at.desc()).limit(100).all()

        def serialize_report(r):
            media_list = []
            if r.post:
                for media in r.post.media_files:
                    media_url = url_for('serve_user_media', filename=media.file_url)
                    thumbnail_url = (
                        url_for('serve_user_media', filename=media.thumbnail_url)
                        if getattr(media, 'thumbnail_url', None)
                        else None
                    )
                    media_list.append({ 'url': media_url, 'thumbnail_url': thumbnail_url, 'type': media.file_type })

            return {
                'id': r.id,
                'reason': r.reason,
                'reporter': {
                    'id': r.reporter.id,
                    'username': r.reporter.username,
                    'email': r.reporter.email,
                    'profile_pic': r.reporter.profile_pic_url or url_for('static', filename='images/free.png'),
                    'role': r.reporter.role.value
                },
                'reported': {
                    'id': r.post.user.id if r.post else None,
                    'username': r.post.user.username if r.post else '(deleted)',
                    'email': r.post.user.email if r.post else '-',
                    'profile_pic': (r.post.user.profile_pic_url if r.post else None) or url_for('static', filename='images/free.png'),
                    'role': (r.post.user.role.value if r.post else None)
                },
                'post': {
                    'id': r.post.id if r.post else None,
                    'content': (r.post.content if r.post else '(deleted)'),
                    'media': media_list
                },
                'processed_by_text': (f"{('Kurucu' if r.processed_by_admin and r.processed_by_admin.role == UserRole.kurucu else 'Yönetici')}: {r.processed_by_admin.username} {('onayladı' if r.decision=='approved' else 'reddetti')}" if r.decision else None)
            }

        return jsonify({
            'active_reports': [serialize_report(r) for r in active_reports],
            'inactive_reports': [serialize_report(r) for r in inactive_reports]
        })
    except Exception as e:
        current_app.logger.error(f"Admin reported posts fetch error: {e}")
        return jsonify({'error': 'Raporlar alınamadı.'}), 500

@app.route('/admin/reports', methods=['GET'])
@login_required
@admin_required
def admin_get_reported_posts_alias():
    return admin_get_reported_posts()

@app.route('/admin/reported_posts/<int:report_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_report(report_id):
    report = db.session.get(PostReport, report_id)
    if not report:
        return jsonify({'error': 'Report not found.'}), 404
    try:
        post = db.session.get(Post, report.post_id)
        report.status = 'dismissed'
        report.decision = 'approved'
        report.processed_by_admin_id = current_user.id
        report.processed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Approve report error: {e}")
        return jsonify({'error': 'Approval failed.'}), 500

@app.route('/admin/reports/<int:report_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_report_alias(report_id):
    return admin_approve_report(report_id)

@app.route('/admin/reported_posts/<int:report_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_reject_report(report_id):
    report = db.session.get(PostReport, report_id)
    if not report:
        return jsonify({'error': 'Report not found.'}), 404
    try:
        report.status = 'dismissed'
        report.decision = 'rejected'
        report.processed_by_admin_id = current_user.id
        report.processed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reject report error: {e}")
        return jsonify({'error': 'Rejection failed.'}), 500

@app.route('/admin/reports/<int:report_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_reject_report_alias(report_id):
    return admin_reject_report(report_id)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
        # Periyodik dosya temizleme görevi
        if not scheduler.get_job('cleanup_files_task'):
            scheduler.add_job(id='cleanup_files_task', func=cleanup_expired_files, trigger='interval', minutes=5)

        # ### YENİ: Süresi dolan rolleri kontrol eden periyodik görev ###
        if not scheduler.get_job('check_roles_task'):
            scheduler.add_job(id='check_roles_task', func=check_expired_roles, trigger='interval', hours=1)

        # YENİ ZAMANLANMIŞ GÖREV
        if not scheduler.get_job('reset_captcha_fails_task'):
            scheduler.add_job(id='reset_captcha_fails_task', func=reset_daily_captcha_fails, trigger='interval', hours=1)

    app.run(host='0.0.0.0', port=5000, debug=False)