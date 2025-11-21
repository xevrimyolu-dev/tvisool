import os
from pathlib import Path # Path nesnesini kullanmak için

# Projenin temel dizin yolunu belirler.
basedir = Path(os.path.abspath(os.path.dirname(__file__)))

class Config:
    # --- KRİTİK GÜVENLİK AYARLARI ---
    SECRET_KEY = os.environ.get('SECRET_KEY')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    # YENİ EKLENEN API ANAHTARI
    OCR_SPACE_API_KEY = os.environ.get('OCR_SPACE_API_KEY') or 'K88159943688957'

    # --- Veritabanı Ayarları ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + str(basedir / 'instance' / 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Flask Oturum (Session) Yapılandırması ---
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True