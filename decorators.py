# decorators.py

from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import current_user
from models import UserRole

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in [UserRole.caylak_admin, UserRole.usta_admin, UserRole.kurucu]:
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            is_api_request = (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html)
            )
            if is_api_request:
                return jsonify({"error": "Yetkisiz erişim"}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def usta_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in [UserRole.usta_admin, UserRole.kurucu]:
            flash("Bu işlem için yetkiniz yetersiz.", "danger")
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                 return jsonify({"error": "Yetkisiz erişim"}), 403
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def kurucu_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.kurucu:
            flash("Bu işlem sadece Kurucu tarafından yapılabilir.", "danger")
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                 return jsonify({"error": "Yetkisiz erişim"}), 403
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            is_api_request = (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html)
            )
            if not (current_user.is_authenticated and (current_user.role == UserRole.kurucu or current_user.has_permission(permission_name))):
                if is_api_request:
                    return jsonify({"error": f"Bu işlem için gerekli '{permission_name}' yetkisi bulunmamaktadır."}), 403
                
                flash(f"Bu işlem için gerekli '{permission_name}' yetkiniz bulunmamaktadır.", "danger")
                return redirect(url_for('admin_dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator