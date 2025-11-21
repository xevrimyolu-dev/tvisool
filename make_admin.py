import sys
from pathlib import Path

# Projenizin ana dizinini Python yoluna ekleyin
# Bu, 'app', 'models', 'extensions' modüllerini bulabilmemiz için gereklidir.
project_dir = '/home/ToolVisions'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

try:
    # Gerekli Flask uygulama bileşenlerini içe aktar
    from app import app
    from extensions import db
    from models import User, UserRole
except ImportError as e:
    print(f"HATA: Gerekli modüller import edilemedi: {e}")
    print("LÜTFEN KONTROL EDİN:")
    print("1. Bu betiğin '/home/ToolVisions/' dizininde olduğundan emin olun.")
    print("2. Betiği çalıştırmadan önce 'workon my-virtualenv' komutuyla sanal ortamı aktifleştirin.")
    sys.exit(1)

# --- Değiştirmek istediğiniz kullanıcının bilgileri ---
USER_EMAIL = "retnavisions@gmail.com"
YENI_ROL = UserRole.kurucu
# ----------------------------------------------------

def set_user_role():
    """
    Belirtilen e-postaya sahip kullanıcının rolünü günceller.
    """
    # Veritabanı işlemi yapabilmek için Flask uygulama bağlamına (app context) ihtiyacımız var.
    with app.app_context():
        print(f"Veritabanına bağlanıldı. '{USER_EMAIL}' e-postası aranıyor...")

        # Kullanıcıyı e-posta adresine göre bul
        user = User.query.filter_by(email=USER_EMAIL).first()

        if user:
            print(f"Kullanıcı bulundu: {user.username} (Mevcut Rol: {user.role.value})")

            if user.role == YENI_ROL:
                print(f"Kullanıcı zaten '{YENI_ROL.value}' rolüne sahip. Değişiklik yapılmadı.")
            else:
                # Kullanıcının rolünü güncelle
                user.role = YENI_ROL

                try:
                    # Değişikliği veritabanına kaydet
                    db.session.commit()
                    print(f"\n*** BAŞARILI ***")
                    print(f"Kullanıcı: {user.username}")
                    print(f"Yeni Rol: {user.role.value}")
                except Exception as e:
                    db.session.rollback()
                    print(f"\nHATA: Veritabanına kayıt sırasında bir sorun oluştu: {e}")
        else:
            print(f"\nHATA: '{USER_EMAIL}' e-posta adresine sahip bir kullanıcı bulunamadı.")

# Bu betik doğrudan çalıştırıldığında 'set_user_role' fonksiyonunu çağır
if __name__ == "__main__":
    set_user_role()