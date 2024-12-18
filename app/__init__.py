import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_jwt_extended import JWTManager  # Impor JWTManager
from config import Config

# Inisialisasi objek
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
jwt = JWTManager()  # Inisialisasi JWTManager

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,  # Atur level log yang diinginkan (INFO, ERROR, DEBUG, dsb)
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Output log ke konsol
                        logging.FileHandler('app.log')  # Simpan log ke file app.log
                    ])

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inisialisasi db, migrate, login_manager, bcrypt, mail, jwt
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)  # Inisialisasi JWT

    # Konfigurasi LoginManager
    login_manager.login_view = 'auth_bp.login'  # Ganti dengan nama blueprint dan endpoint login Anda
    login_manager.login_message = "Please log in to access this page."  # Pesan yang ditampilkan saat pengguna tidak terautentikasi
    
    logging.info("Application started.")  # Logging ketika aplikasi mulai dijalankan

    @app.context_processor
    def utility_processor():
        from app.models import AttendanceStatus  # Impor di dalam fungsi
        from app.utils import get_attendance_for_today
        return dict(get_attendance_for_today=get_attendance_for_today, AttendanceStatus=AttendanceStatus)

    # User loader function
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User  # Lazy import untuk menghindari circular import
        logging.info(f"Loading user with ID: {user_id}")  # Logging saat memuat user
        return User.query.get(int(user_id))

    # Daftarkan blueprint
    from .routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    logging.info("Registered 'auth_bp' blueprint.")  # Logging saat blueprint auth didaftarkan

    from .routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    logging.info("Registered 'admin_bp' blueprint.")  # Logging saat blueprint admin didaftarkan

    from .routes.user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')
    logging.info("Registered 'user_bp' blueprint.")  # Logging saat blueprint user didaftarkan

    from .routes.employee_routes import home_bp, employee_bp
    app.register_blueprint(home_bp)
    app.register_blueprint(employee_bp, url_prefix='/employee')
    logging.info("Registered 'employee_bp' blueprint.")  # Logging saat blueprint employee didaftarkan

    from .routes.attendance_routes import attendance_bp
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    logging.info("Registered 'attendance_bp' blueprint.")  # Logging saat blueprint attendance didaftarkan

    return app