from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


# Bu nesneleri burada oluşturuyoruz ama henüz bir uygulamaya bağlamıyoruz.
# Bu, farklı dosyalardan aynı nesnelere erişmemizi sağlar.
csrf = CSRFProtect()
db = SQLAlchemy()