# obb_repack.py

import os
import shutil
import zipfile
import tempfile
from pathlib import Path

class ObbRepackError(Exception):
    """OBB yeniden paketleme sırasında oluşacak özel hatalar için temel sınıf."""
    pass

class FileNotInObbError(ObbRepackError):
    """Değiştirilmek istenen dosya OBB içinde bulunamadığında fırlatılır."""
    pass

class InvalidObbFileError(ObbRepackError):
    """Geçersiz veya bozuk OBB dosyası yüklendiğinde fırlatılır."""
    pass

def find_file_in_tree(directory, filename):
    """Bir dizin ağacında belirli bir dosyayı arar ve tam yolunu döndürür."""
    for root, _, files in os.walk(directory):
        if filename in files:
            return Path(root) / filename
    return None

def repack_and_process(original_obb_path: Path, modified_files_paths: list[Path], output_obb_path: Path):
    """
    Ana OBB yeniden paketleme fonksiyonu.
    Açar, dosyaları değiştirir, sıkıştırmasız paketler ve boyutunu eşitler.
    Hata durumunda özel istisnalar (exceptions) fırlatır.
    """
    work_dir = Path(tempfile.mkdtemp())
    unpacked_obb_dir = work_dir / "unpacked"

    try:
        # Adım 1: Orijinal boyutu al ve dosyayı doğrula
        if not original_obb_path.exists():
            raise FileNotFoundError("Orijinal OBB dosyası sunucuda bulunamadı.")
        
        original_size = original_obb_path.stat().st_size

        # Adım 2: OBB dosyasını aç
        unpacked_obb_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(original_obb_path, 'r') as zip_ref:
                zip_ref.extractall(unpacked_obb_dir)
        except zipfile.BadZipFile:
            raise InvalidObbFileError("Yüklenen OBB dosyası bozuk veya geçerli bir zip arşivi değil.")

        # Adım 3: Dosyaları doğrula ve değiştir
        for file_path in modified_files_paths:
            file_name = file_path.name
            target_path = find_file_in_tree(unpacked_obb_dir, file_name)

            if target_path is None:
                raise FileNotInObbError(f"Değiştirmek istediğiniz '{file_name}' dosyası, OBB içinde bulunamadı.")
            
            shutil.copy2(file_path, target_path)

        # Adım 4: Sıkıştırmasız olarak yeniden paketle
        temp_repack_path = work_dir / "repacked.obb"
        with zipfile.ZipFile(temp_repack_path, 'w', zipfile.ZIP_STORED) as zipf:
            for root, _, files in os.walk(unpacked_obb_dir):
                for file in files:
                    full_path = Path(root) / file
                    archive_name = full_path.relative_to(unpacked_obb_dir)
                    zipf.write(full_path, archive_name)
        
        # Adım 5: Dosya boyutunu orijinaliyle eşitle (Kritik Adım)
        current_size = temp_repack_path.stat().st_size
        if current_size != original_size:
            with open(temp_repack_path, 'a+b') as f:
                f.truncate(original_size)
        
        final_size = temp_repack_path.stat().st_size
        if final_size != original_size:
             raise ObbRepackError(f"Kritik Hata: Dosya boyutu eşitlenemedi. Son boyut: {final_size}")
        
        # Adım 6: Sonuç dosyasını hedefe taşı
        output_obb_path.parent.mkdir(exist_ok=True)
        shutil.move(temp_repack_path, output_obb_path)

    finally:
        # Adım 7: Her durumda geçici dosyaları temizle
        shutil.rmtree(work_dir, ignore_errors=True)