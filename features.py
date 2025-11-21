# features.py
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from models import UserRole, db, FeatureUsageLog  # FeatureUsageLog modelini ekleyeceğiz
from utils import record_log
from collections import Counter

features_bp = Blueprint('features', __name__, template_folder='templates', static_folder='static')

# Toplam 30 özellik, anahtarları, isimleri ve ikonlarıyla birlikte tanımlandı.
# features.py -> GÜNCELLENDİ
FEATURE_DATA = [
    {"key": "antenna", "name": "Antenna", "image": "feature_antenna.png"}, # GÜNCELLENDİ
    {"key": "magic_bullet", "name": "Magic Bullet", "image": "feature_magic.png"},
    {"key": "no_recoil", "name": "No Recoil", "image": "feature_recoil.png"},
    {"key": "wallhack", "name": "Wall Hack", "image": "feature_wallhack.png"},
    {"key": "speed_hack", "name": "Speed Hack", "image": "feature_speed.png"},
    {"key": "no_grass", "name": "No Grass", "image": "feature_grass.png"},
    {"key": "esp_line", "name": "ESP Line", "image": "feature_esp.png"},
    {"key": "item_glow", "name": "Item Glow", "image": "feature_item.png"},
    {"key": "high_jump", "name": "High Jump", "image": "feature_jump.png"},
    {"key": "instant_reload", "name": "Instant Reload", "image": "feature_reload.png"},
    {"key": "fly_car", "name": "Fly Car", "image": "feature_flycar.png"},
    {"key": "fast_parachute", "name": "Fast Parachute", "image": "feature_parachute.png"},
    {"key": "damage_boost", "name": "Damage Boost", "image": "feature_damage.png"},
    {"key": "no_spread", "name": "No Spread", "image": "feature_spread.png"},
    {"key": "small_crosshair", "name": "Small Crosshair", "image": "feature_crosshair.png"},
    {"key": "god_view", "name": "God View", "image": "feature_view.png"},
    {"key": "auto_headshot", "name": "Auto Headshot", "image": "feature_headshot.png"},
    {"key": "night_vision", "name": "Night Vision", "image": "feature_nightvision.png"},
    {"key": "long_slide", "name": "Long Slide", "image": "feature_slide.png"},
    {"key": "telekill", "name": "Telekill", "image": "feature_telekill.png"},
    {"key": "instant_scope", "name": "Instant Scope", "image": "feature_scope.png"},
    {"key": "mass_grab", "name": "Mass Grab", "image": "feature_grab.png"},
    {"key": "hide_player", "name": "Hide Player Model", "image": "feature_hide.png"},
    {"key": "fov_changer", "name": "FOV Changer", "image": "feature_fov.png"},
    {"key": "anti_smoke", "name": "Anti-Smoke", "image": "feature_smoke.png"},
    {"key": "anti_flash", "name": "Anti-Flash", "image": "feature_flash.png"},
    {"key": "fast_revive", "name": "Fast Revive", "image": "feature_revive.png"},
    {"key": "water_walk", "name": "Walk on Water", "image": "feature_water.png"},
    {"key": "unlimited_ammo", "name": "Unlimited Ammo", "image": "feature_ammo.png"},
    {"key": "vehicle_speed", "name": "Vehicle Speed Boost", "image": "feature_vehicle.png"}
] # TÜM 'subtitle' ANAHTARLARI KALDIRILDI

def get_feature_access_level(user_role):
    """Kullanıcının rolüne göre kaç özelliğe erişebileceğini belirler."""
    if user_role in [UserRole.dev, UserRole.caylak_admin, UserRole.usta_admin, UserRole.kurucu]:
        return 30  # Tüm özellikler
    elif user_role == UserRole.premium:
        return 12 # İlk 12 özellik
    else: # Ücretsiz
        return 1   # Sadece ilk özellik

@features_bp.route('/features')
@login_required
def features_page():
    """Özellikler sayfasını, kullanıcının erişim seviyesine göre render eder."""
    access_level = get_feature_access_level(current_user.role)
    processed_features = []
    for i, feature in enumerate(FEATURE_DATA):
        feature_copy = feature.copy()
        # Özellik kilitli mi değil mi diye kontrol et
        feature_copy["is_locked"] = (i + 1) > access_level
        processed_features.append(feature_copy)
        
    # YENİ: Antenna linkini template'e gönder
    antenna_download_link = "https://www.mediafire.com/file/qgitbzwsa13jo79/Antenna+Config+4.1+ToolVision.7z/file"
        
    return render_template('features.html', 
                           user=current_user, 
                           features=processed_features,
                           antenna_link=antenna_download_link) # GÜNCELLENDİ

@features_bp.route('/features/log_usage', methods=['POST'])
@login_required
def log_feature_usage():
    """Kullanıcı 'Başlat' butonuna tıkladığında seçilen özellikleri kaydeder."""
    data = request.json
    selected_keys = data.get('selected_features')

    if not selected_keys or not isinstance(selected_keys, list):
        return jsonify({"error": "Özellik seçilmedi."}), 400

    try:
        # Hangi özelliklerin kullanıldığını veritabanına kaydet
        for key in selected_keys:
            log = FeatureUsageLog(user_id=current_user.id, feature_key=key)
            db.session.add(log)
        
        db.session.commit()
        
        # Ana aktivite loguna da bir özet kayıt düşelim
        feature_names = ', '.join(selected_keys)
        record_log(current_user, f"Config oluşturuldu: [{feature_names}]")
        
        return jsonify({"success": True, "message": "Konfigürasyon başarıyla loglandı."})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Özellik kullanımı loglanırken hata: {e}")
        return jsonify({"error": "Sunucu hatası"}), 500