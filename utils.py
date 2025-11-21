# utils.py
from flask import current_app
from extensions import db
from models import ActivityLog

def record_log(user, action_description, file_type=None, original_file_name=None, original_file_size_mb=None, modified_files_count=0, modified_files_names=None):
    """
    Uygulamanın herhangi bir yerinden çağrılabilen, merkezi log kaydetme fonksiyonu.
    """
    try:
        log = ActivityLog(
            user_id=user.id, 
            action=action_description, 
            file_type=file_type,
            original_file_name=original_file_name, 
            original_file_size_mb=original_file_size_mb,
            modified_files_count=modified_files_count, 
            modified_files_names=modified_files_names
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # 'app.logger' yerine 'current_app.logger' kullanmak, döngüsel bağımlılığı önler.
        current_app.logger.error(f"Log kaydı sırasında hata oluştu: {e}")
        db.session.rollback()