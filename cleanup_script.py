import os
from pathlib import Path
from datetime import datetime, timedelta

# DİKKAT: Bu yol, PythonAnywhere'deki ana klasörünüzle tam olarak eşleşmelidir.
BASE_DIR = Path('/home/ToolVision') 
RESULT_FOLDER = BASE_DIR / 'results'
LOG_FILE = BASE_DIR / 'cleanup.log'

def log_message(message):
    """Log mesajlarını tarihle birlikte bir dosyaya yazar."""
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def cleanup_old_files():
    """20 dakikadan eski olan tüm dosyaları 'results' klasöründen siler."""
    now = datetime.now()
    timeout = timedelta(minutes=20) # 20 dakika bekleme süresi

    if not RESULT_FOLDER.exists():
        log_message(f"HATA: Klasör bulunamadı: {RESULT_FOLDER}")
        return

    log_message("Temizlik görevi çalışıyor...")
    for filename in os.listdir(RESULT_FOLDER):
        file_path = RESULT_FOLDER / filename
        try:
            file_creation_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if now - file_creation_time > timeout:
                os.remove(file_path)
                log_message(f"Eski dosya silindi: {filename}")
        except Exception as e:
            log_message(f"HATA: Dosya silinirken hata: {filename} - {e}")

if __name__ == "__main__":
    cleanup_old_files()