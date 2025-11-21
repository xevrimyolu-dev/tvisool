# obb_unpack.py

import shutil
import zipfile
import tempfile
from pathlib import Path

class InvalidObbFileError(Exception):
    """Geçersiz veya bozuk OBB dosyası yüklendiğinde fırlatılır."""
    pass

def unpack_and_zip(obb_file_path: Path, output_zip_path: Path):
    """
    Bir OBB dosyasını açar, içeriğini bir klasöre çıkarır ve o klasörü zip'ler.

    Args:
        obb_file_path (Path): Açılacak .obb dosyasının yolu.
        output_zip_path (Path): Sonuç .zip dosyasının kaydedileceği yol (uzantısız).
    """
    work_dir = Path(tempfile.mkdtemp())
    unpacked_dir = work_dir / "unpacked_content"

    try:
        if not obb_file_path.exists():
            raise FileNotFoundError("OBB dosyası sunucuda bulunamadı.")
        
        # OBB dosyasını aç
        unpacked_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(obb_file_path, 'r') as zip_ref:
                zip_ref.extractall(unpacked_dir)
        except zipfile.BadZipFile:
            raise InvalidObbFileError("Yüklenen OBB dosyası bozuk veya geçerli bir zip arşivi değil.")

        # Açılan klasörü zip'le
        shutil.make_archive(str(output_zip_path), 'zip', unpacked_dir)

    finally:
        # Her durumda geçici dosyaları temizle
        shutil.rmtree(work_dir, ignore_errors=True)