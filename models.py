import enum
from datetime import datetime, timedelta
import uuid

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

# YENİ: Yetkileri tutacak olan ilişki tablosu (Many-to-Many)
user_permissions = db.Table('user_permissions',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)

# YENİ: Yetkilerin kendisini tanımlayan model
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Örn: 'emergency_delete'
    description = db.Column(db.String(255))  # Örn: 'Kullanıcıları acil durumda silme yetkisi'

    def __repr__(self):
        return f'<Permission {self.name}>'

class PostReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False) # Hangi gönderi
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Kim şikayet etti
    reason = db.Column(db.String(255), nullable=False) # Seçilen sebep
    status = db.Column(db.String(20), default='pending') # pending, dismissed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    decision = db.Column(db.String(20), nullable=True) # approved, rejected

    # İlişkiler
    post = db.relationship('Post', backref=db.backref('reports', lazy=True, cascade="all, delete-orphan"))
    reporter = db.relationship('User', foreign_keys=[reporter_id])
    processed_by_admin = db.relationship('User', foreign_keys=[processed_by_admin_id])

    def __repr__(self):
        return f'<PostReport Post:{self.post_id} Reason:{self.reason}>'
        
# GÜNCELLENDİ: Rolleri daha yönetilebilir hale getiren Enum sınıfı
class UserRole(enum.Enum):
    ücretsiz = 'ücretsiz'
    premium = 'premium'
    dev = 'dev'
    caylak_admin = 'caylak_admin'
    usta_admin = 'usta_admin'
    kurucu = 'kurucu'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    last_post_time = db.Column(db.DateTime, nullable=True)
    
    # --- YENİ: KADEMELİ SPAM SAVUNMASI İÇİN ALANLAR ---
    # Kullanıcının spam filtresine kaç kez takıldığını sayar.
    captcha_fail_count = db.Column(db.Integer, default=0, nullable=False)
    # Filtreye en son ne zaman takıldığını saklar (24 saatlik kontrol için).
    last_captcha_fail_time = db.Column(db.DateTime, nullable=True)
    # Eğer mola aldıysa, molanın ne zaman biteceğini saklar.
    post_cooldown_until = db.Column(db.DateTime, nullable=True)
    cooldown_reason = db.Column(db.String(255), nullable=True)
    post_comment_counts = db.Column(db.Text, nullable=True, default='{}')
    # GÜNCELLENDİ: role alanı artık string yerine Enum kullanıyor
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.ücretsiz)
    
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active' veya 'deleted'
    browser_fingerprint = db.Column(db.String(256), nullable=True, index=True)
    
    backup_code = db.Column(db.String(10), nullable=True)
    session_token = db.Column(db.String(36), nullable=True, unique=True, default=lambda: str(uuid.uuid4()))
    role_expiry_date = db.Column(db.DateTime, nullable=True, default=None)
    action_count = db.Column(db.Integer, default=0)
    last_action_time = db.Column(db.DateTime, default=None)
    limit_hit_count = db.Column(db.Integer, default=0)
    profile_pic_url = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, onupdate=datetime.utcnow)
    selected_language = db.Column(db.String(5), default='en')
    pin_count = db.Column(db.Integer, default=0, nullable=False)

    # --- YENİ CİHAZ "SLOT" SİSTEMİ ---
    # Eski "devices" ilişkisi kaldırıldı.
    # Slot 1
    device_1_fingerprint = db.Column(db.String(256), nullable=True, index=True)
    device_1_name = db.Column(db.String(100), nullable=True)
    device_1_last_login = db.Column(db.DateTime, nullable=True)
    # Slot 2
    device_2_fingerprint = db.Column(db.String(256), nullable=True, index=True)
    device_2_name = db.Column(db.String(100), nullable=True)
    device_2_last_login = db.Column(db.DateTime, nullable=True)
    
    # Başarısız dekont deneme sayısını tutar
    receipt_fail_count = db.Column(db.Integer, default=0, nullable=False)
    
    # 3. başarısız denemenin yapıldığı zamanı tutar
    last_receipt_fail_time = db.Column(db.DateTime, nullable=True)

    # İLİŞKİLER (devices ilişkisi hariç aynı)
    logs = db.relationship('ActivityLog', backref='user', lazy=True, cascade="all, delete-orphan")
    page_visits = db.relationship('PageVisitLog', backref='user', lazy=True, cascade="all, delete-orphan")
    
    # DÜZENLEME: Ticket ilişkisinde, kullanıcı silindiğinde biletlerin silinmemesi için cascade kaldırıldı
    tickets = db.relationship('Ticket', foreign_keys='Ticket.user_id', backref='user', lazy=True)

    # YENİ: Kullanıcının özel yetkileriyle olan ilişkisi
    permissions = db.relationship('Permission', secondary=user_permissions, lazy='subquery',
                                  backref=db.backref('users', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # YENİ: Bir kullanıcının belirli bir yetkiye sahip olup olmadığını kontrol eden yardımcı metod
    def has_permission(self, perm_name):
        """Kullanıcının belirtilen isme sahip bir yetkisi olup olmadığını kontrol eder."""
        for perm in self.permissions:
            if perm.name == perm_name:
                return True
        return False

    def can_perform_action(self):
        # GÜNCELLENDİ: Yeni admin rollerini de sınırsız olarak ekledik
        limits = { 
            UserRole.ücretsiz: {'limit': 1, 'cooldown_hours': 3}, 
            UserRole.premium: {'limit': 30, 'cooldown_hours': 1}, 
            UserRole.dev: {'limit': float('inf'), 'cooldown_hours': 0}, 
            UserRole.caylak_admin: {'limit': float('inf'), 'cooldown_hours': 0}, 
            UserRole.usta_admin: {'limit': float('inf'), 'cooldown_hours': 0}, 
            UserRole.kurucu: {'limit': float('inf'), 'cooldown_hours': 0} 
        }
        user_limit_info = limits.get(self.role, limits[UserRole.ücretsiz])
        if user_limit_info['limit'] == float('inf'):
            return True, None
            
        if self.last_action_time:
            cooldown_end_time = self.last_action_time + timedelta(hours=user_limit_info['cooldown_hours'])
            if datetime.utcnow() >= cooldown_end_time:
                self.action_count = 0
                self.last_action_time = None
                db.session.commit()
                
        if self.action_count >= user_limit_info['limit']:
            self.limit_hit_count += 1
            db.session.commit()
            if self.last_action_time:
                cooldown_end_time = self.last_action_time + timedelta(hours=user_limit_info['cooldown_hours'])
                remaining_time = cooldown_end_time - datetime.utcnow()
                if remaining_time.total_seconds() > 0:
                    return False, {"key": "limit_reached_cooldown", "time": str(remaining_time).split('.')[0]}
            return False, {"key": "limit_reached"}
            
        return True, None

    def increment_action_count(self):
        if self.role not in [UserRole.dev, UserRole.caylak_admin, UserRole.usta_admin, UserRole.kurucu]:
            if self.last_action_time is None:
                self.last_action_time = datetime.utcnow()
            self.action_count += 1
            
    def get_remaining_actions(self):
        limits = { 
            UserRole.ücretsiz: {'limit': 1, 'cooldown_hours': 3}, 
            UserRole.premium: {'limit': 30, 'cooldown_hours': 1}, 
            UserRole.dev: {'limit': float('inf'), 'cooldown_hours': 0}, 
            UserRole.caylak_admin: {'limit': float('inf'), 'cooldown_hours': 0},
            UserRole.usta_admin: {'limit': float('inf'), 'cooldown_hours': 0},
            UserRole.kurucu: {'limit': float('inf'), 'cooldown_hours': 0} 
        }
        user_limit_info = limits.get(self.role, limits[UserRole.ücretsiz])
        
        if user_limit_info['limit'] == float('inf'):
            return {
                'remaining': 'Sınırsız', 
                'total': 'Sınırsız', 
                'cooldown_data': {"key": "unlimited"}, 
                'current_actions': 'Yok', 
                'role': self.role.value
            }
            
        current_limit = user_limit_info['limit']
        current_cooldown = user_limit_info['cooldown_hours']
        effective_action_count = self.action_count
        cooldown_data = {"key": "never_used"}
        
        if self.last_action_time:
            cooldown_end_time = self.last_action_time + timedelta(hours=current_cooldown)
            if datetime.utcnow() >= cooldown_end_time:
                effective_action_count = 0
                cooldown_data = {"key": "refreshed"}
            else:
                if self.action_count >= current_limit:
                    remaining_time = cooldown_end_time - datetime.utcnow()
                    cooldown_data = {"key": "cooldown_active", "time": str(remaining_time).split('.')[0]}
                else:
                    cooldown_data = {"key": "refreshed"}
                    
        remaining = max(0, current_limit - effective_action_count)
        return {
            'remaining': remaining, 
            'total': current_limit, 
            'cooldown_data': cooldown_data, 
            'current_actions': effective_action_count, 
            'role': self.role.value
        }

    def __repr__(self):
        return f'<User {self.username} - {self.role.value}>'

# Yeni: Satın Alma Niyetini Takip Etmek İçin Model
class PurchaseIntent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Satın alma niyetini benzersiz olarak tanımlayan UUID
    intent_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    role = db.Column(db.String(50), nullable=False) # Örn: 'premium', 'dev'
    duration = db.Column(db.String(20), nullable=False) # Örn: '1m', 'permanent'
    price = db.Column(db.String(50), nullable=False) # Örn: '$17.32' (Para birimi ile birlikte string olarak saklanır)
    
    # Durum: PENDING (Başladı), WAITING_FOR_ADMIN (Ödeme bildirimi yapıldı), COMPLETED, CANCELLED
    status = db.Column(db.String(50), nullable=False, default='PENDING')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # YENİ EKLENEN KOLONLAR - Kullanıcının girdiği kanıt bilgileri
    customer_name = db.Column(db.String(50), nullable=True)
    customer_phone = db.Column(db.String(25), nullable=True)
    customer_email = db.Column(db.String(50), nullable=True)
    receipt_image_path = db.Column(db.String(255), nullable=True)
    # EKLENEN KOLONLARIN SONU
    
    # Kullanıcı ödemeyi yaptığını bildirirse bu alan dolar
    payment_notified_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref=db.backref('purchase_intents', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<PurchaseIntent {self.intent_id} - User {self.user_id} - {self.role}>'
        
class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    file_type = db.Column(db.String(10), nullable=True)
    original_file_name = db.Column(db.String(255), nullable=True)
    original_file_size_mb = db.Column(db.Float, nullable=True)
    modified_files_count = db.Column(db.Integer, default=0)
    modified_files_names = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Log: {self.user.username} - {self.action} - {self.timestamp}>'

class TemporaryFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False, unique=True)
    request_id = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('temporary_files', lazy=True, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f'<TemporaryFile {self.file_path}>'
        
class ChatAdminLogAction(enum.Enum):
    MESSAGE_SENT = 'Mesaj Gönderdi'
    TICKET_CLAIMED = 'Bileti Üstlendi'
    TICKET_RELEASED = 'Bileti Serbest Bıraktı'
    TICKET_CLOSED = 'Bileti Kapattı'

# YENİ: Yönetici hareketlerini loglamak için model
class ChatAdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.Enum(ChatAdminLogAction), nullable=False)
    details = db.Column(db.Text, nullable=True) # Örneğin, gönderilen mesajın bir kısmı
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    ticket = db.relationship('Ticket', backref=db.backref('admin_logs', lazy=True, cascade="all, delete-orphan"))
    admin = db.relationship('User', backref='chat_admin_logs')

    def __repr__(self):
        return f'<ChatAdminLog Ticket {self.ticket_id} - Admin {self.admin_id} - {self.action.value}>'

class PageVisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    page_id = db.Column(db.String(50), nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PageVisit: {self.user.username} - {self.page_id} - {self.duration_seconds}s>'

class Ticket(db.Model):
    # DÜZENLEME: ChatMessage ilişkisinde, bilet silindiğinde mesajların silinmesi için cascade eklendi
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='open') # 'open', 'claimed', 'closed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    claimed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    claimed_at = db.Column(db.DateTime, nullable=True)
    
    messages = db.relationship('ChatMessage', backref='ticket', lazy='dynamic', cascade="all, delete-orphan")
    claimer = db.relationship('User', foreign_keys=[claimed_by_admin_id])
    
    def __repr__(self):
        return f'<Ticket {self.id} - {self.subject}>'

class VideoLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_key = db.Column(db.String(50), nullable=False) # Örn: 'video_1'
    watch_time_seconds = db.Column(db.Integer, default=0) # Toplam izlenen saniye
    last_watched_timestamp = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Mevcut User modeline olan ilişki
    user = db.relationship('User', backref=db.backref('video_logs', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<VideoLog User {self.user_id} - Video {self.video_key} - {self.watch_time_seconds}s>'

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    attachment_url = db.Column(db.String(255), nullable=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    is_admin_message = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', backref='sent_messages')
    
    def __repr__(self):
        return f'<ChatMessage {self.id} on Ticket {self.ticket_id}>'
        
class FeatureUsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature_key = db.Column(db.String(50), nullable=False) # 'aimbot', 'wallhack' gibi
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('feature_usage_logs', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<FeatureLog User {self.user_id} - Feature {self.feature_key}>'

class MuteLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mute_end_time = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.String(200), nullable=True)

    # İlişkiler
    user = db.relationship('User', foreign_keys=[user_id], backref='mute_logs')
    admin = db.relationship('User', foreign_keys=[admin_id])

    def __repr__(self):
        return f'<MuteLog for User {self.user_id}>'