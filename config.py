import os
import base64
import logging
from datetime import timedelta

# Menghasilkan SECRET_KEY dari Base64
secret_key = base64.b64encode(os.urandom(24)).decode('utf-8')


class Config:
    # Koneksi ke database SQLite
    SECRET_KEY = secret_key
    SQLALCHEMY_DATABASE_URI = 'sqlite:///attendance_system.db?timeout=60'
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Konfigurasi JWT
    JWT_SECRET_KEY = secret_key  # Kunci rahasia untuk JWT
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Waktu kedaluwarsa token akses


    # Menambahkan batas ukuran upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Tentukan lokasi folder untuk menyimpan foto
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads')

    # Pastikan folder ada
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Konfigurasi SMTP untuk email
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587

    # Konfigurasi Logging
    logging.basicConfig(level=logging.INFO,  # Atur level log yang diinginkan (INFO, ERROR, DEBUG, dsb)
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.StreamHandler(),  # Output log ke konsol
                            logging.FileHandler('app_config.log')  # Simpan log ke file app_config.log
                        ])

    logging.info("Config loaded successfully")  # Log untuk menandakan konfigurasi telah dimuat