# Dosya: forum/models.py

from datetime import datetime
from extensions import db  # Ana projemizdeki 'db' objesini buradan çekiyoruz
from models import User    # 'User' modeline referans vermek için ana models.py'den import ediyoruz

# -----------------------------------------------------------------------------
# DİKKAT: Aşağıdaki modellerin çalışması için ana 'models.py' dosyanızda
# User modelinin 'posts', 'comments', 'likes' gibi backref'leri OLMAMALIDIR.
# Bu ilişkileri burada, bu dosyada tanımlıyoruz.
# -----------------------------------------------------------------------------

class Post(db.Model):
    __tablename__ = 'post'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime, nullable=True)
    pinned = db.Column(db.Boolean, default=False, index=True)
    pinned_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('posts', lazy='dynamic'), foreign_keys=[user_id])
    pinned_by = db.relationship('User', foreign_keys=[pinned_by_user_id])
    # --- YENİ SATIR SONU ---
    media_files = db.relationship('PostMedia', backref='post', lazy='dynamic', cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade="all, delete-orphan")
    reactions = db.relationship('Reaction', backref='post', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Post {self.id}>'

class PostMedia(db.Model):
    """Gönderilere eklenen resim, video veya dosyaları temsil eder."""
    __tablename__ = 'post_media'
    
    id = db.Column(db.Integer, primary_key=True)
    file_url = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # 'image', 'video', 'file' gibi
    original_filename = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(512), nullable=True)
    
    # Bu medya dosyasının hangi posta ait olduğunu belirtir.
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f'<PostMedia {self.original_filename}>'

class Comment(db.Model):
    """Gönderilere yapılan yorumları temsil eder."""
    __tablename__ = 'comment'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # Yorumun hangi posta ve hangi kullanıcıya ait olduğunu belirtir.
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Yorum yazarını User tablosu ile ilişkilendirir.
    author = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))

    def __repr__(self):
        return f'<Comment by User {self.user_id} on Post {self.post_id}>'

class Like(db.Model):
    """Gönderileri kimlerin beğendiğini temsil eder."""
    __tablename__ = 'like'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Beğeninin hangi posta ve hangi kullanıcıya ait olduğunu belirtir.
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Beğeneni User tablosu ile ilişkilendirir.
    author = db.relationship('User', backref=db.backref('likes', lazy='dynamic'))

    # Bir kullanıcının aynı gönderiyi birden fazla kez beğenmesini engeller.
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_like_uc'),)

    def __repr__(self):
        return f'<Like by User {self.user_id} on Post {self.post_id}>'

class Reaction(db.Model):
    __tablename__ = 'reaction'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # like, heart, smile, surprise, sad, angry
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    author = db.relationship('User', backref=db.backref('reactions', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='_user_post_reaction_uc'),)

    def __repr__(self):
        return f'<Reaction {self.type} by User {self.user_id} on Post {self.post_id}>'