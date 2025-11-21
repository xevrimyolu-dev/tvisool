# forum/cut.py
# Versiyon 2.0 (Yeniden Yazım - Daha Sağlam Hata Kontrolü)

import os
from PIL import Image
from flask import current_app
import json

def crop_image(image_stream, crop_data_json, save_path):
    """
    Bir resim dosyasını (stream) ve JSON formatındaki kırpma verilerini alır,
    resmi kırpar, optimize eder ve belirtilen yola kaydeder.
    Bu versiyon, gelen verileri daha dikkatli doğrular.

    Args:
        image_stream: Flask'ten gelen dosya nesnesi.
        crop_data_json (str): Cropper.js'ten gelen kırpma verilerini içeren JSON string'i.
        save_path (str): Kırpılmış resmin kaydedileceği tam yol.

    Returns:
        bool: İşlem başarılıysa True, değilse False.
    """
    try:
        # Gelen JSON verisinin boş veya geçersiz olup olmadığını kontrol et
        if not crop_data_json:
            current_app.logger.warning("Boş kırpma verisi alındı. Orijinal resim kaydedilecek.")
            # Bu durumda, resmi olduğu gibi kaydetmeyi tercih edebiliriz.
            # Şimdilik hata olarak kabul edelim.
            return False

        crop_data = json.loads(crop_data_json)
        
        # Gerekli tüm anahtarların veride mevcut olduğundan emin ol
        required_keys = ['x', 'y', 'width', 'height']
        if not all(key in crop_data for key in required_keys):
            current_app.logger.error(f"Eksik kırpma verisi: {crop_data}")
            return False

        # Gelen verileri güvenli bir şekilde tam sayıya çevir
        x = int(crop_data.get('x', 0))
        y = int(crop_data.get('y', 0))
        width = int(crop_data.get('width', 0))
        height = int(crop_data.get('height', 0))

        # Genişlik veya yükseklik sıfırsa, bu geçersiz bir kırpmadır.
        if width <= 0 or height <= 0:
            current_app.logger.error(f"Geçersiz kırpma boyutları: GxY = {width}x{height}")
            return False

        with Image.open(image_stream) as img:
            # Pillow'un (sol, üst, sağ, alt) koordinat formatına çevir
            crop_box = (x, y, x + width, y + height)

            # Resmi kırp
            cropped_img = img.crop(crop_box)
            
            # Instagram standardı olan 1080x1080 boyutuna optimize et
            TARGET_SIZE = 1080
            cropped_img.thumbnail((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

            # PNG'lerdeki şeffaflık sorunlarını önlemek için RGB'ye çevir
            if cropped_img.mode in ("RGBA", "P"):
                cropped_img = cropped_img.convert("RGB")
                
            # Optimize edilmiş resmi yüksek kalitede JPEG olarak kaydet
            cropped_img.save(save_path, 'JPEG', quality=95, optimize=True)
            
        current_app.logger.info(f"Resim başarıyla kırpıldı ve '{save_path}' yoluna kaydedildi.")
        return True

    except json.JSONDecodeError:
        current_app.logger.error("Geçersiz JSON formatında kırpma verisi alındı.")
        return False
    except Exception as e:
        current_app.logger.error(f"Resim kırpma sırasında kritik bir hata oluştu: {e}", exc_info=True)
        return False