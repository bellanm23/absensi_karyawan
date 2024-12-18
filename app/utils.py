import logging
from flask import current_app, request, jsonify
from datetime import datetime, timedelta
from flask_mail import Message
from flask_login import current_user
from app.models import Attendance, User, Employee  # Pastikan untuk mengimpor model EmailConfig
from app import mail
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from app import db
from functools import wraps
from logging.handlers import RotatingFileHandler
from app.models import User  # Pastikan model User diimpor

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),
                        RotatingFileHandler('app.log', maxBytes=1000000, backupCount=5)  # Rotate log
                    ])


def generate_jwt_token(user_id):
    """Menghasilkan token JWT untuk pengguna tanpa kadaluarsa."""
    logging.info(f"Generating JWT token for user ID: {user_id} (no expiration)")
    token = jwt.encode({
        'sub': user_id,
        # Tidak ada 'exp', sehingga token tidak memiliki waktu kadaluarsa
    }, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
    return token


def verify_jwt_token(token):
    """Memverifikasi token JWT dan mengembalikan user_id jika valid."""
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        logging.info(f"Token verified for user ID: {payload['sub']}")
        return payload['sub']
    except jwt.ExpiredSignatureError:
        logging.error("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logging.error("Invalid token")
        return None

def get_user_from_token(token):
    """Mengambil user dari token JWT."""
    user_id = verify_jwt_token(token)
    if user_id:
        user = User.query.get(user_id)
        if user:
            return user
    return None


def get_attendance_for_today(employee_id):
    today = datetime.now().date()  # Get today's date
    attendance_records = Attendance.query.filter_by(employee_id=employee_id, date=today).all()
    logging.info(f"Attendance records for employee {employee_id} on {today}: {attendance_records}")
    return attendance_records


def get_all_employees():
    logging.info("Fetching all employees")  # Log saat mengambil data semua karyawan
    employees = Employee.query.all()
    logging.info(f"Found {len(employees)} employees")  # Log jumlah karyawan yang ditemukan
    return employees

def get_employee_by_id(employee_id):
    logging.info(f"Fetching employee with ID: {employee_id}")  # Log saat mengambil data karyawan berdasarkan ID
    employee = Employee.query.get(employee_id)
    logging.info(f"Employee details: {employee}")  # Log data karyawan
    return employee

def delete_employee_and_related_data(user_id):
    logging.info(f"Deleting employee and related data for user ID: {user_id}")
    try:
        employee = Employee.query.filter_by(user_id=user_id).first()
        if employee:
            deleted_attendance_count = Attendance.query.filter_by(employee_id=employee.id).delete()
            logging.info(f"Deleted {deleted_attendance_count} attendance records for employee {employee.id}")
            db.session.delete(employee)
            logging.info(f"Deleted employee with ID: {employee.id}")

        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            logging.info(f"Deleted user with ID: {user.id}")

        db.session.commit()
        logging.info(f"Changes committed to the database for user ID: {user_id}")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error while deleting data for user ID {user_id}: {e}")

    
    # Menghapus data user
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        logging.info(f"Deleted user with ID: {user.id}")  # Log saat data user dihapus

    # Commit perubahan ke database
    db.session.commit()
    logging.info(f"Changes committed to the database for user ID: {user_id}")  # Log setelah commit perubahan


def generate_reset_token(user_id, expires_in=None):
    """Menghasilkan token reset password untuk pengguna dengan kadaluarsa."""
    expires_in = expires_in or 3600  # Gunakan 1 jam jika tidak ada nilai yang diberikan
    logging.info(f"Generating reset token for user ID: {user_id} with expiration {expires_in} seconds")
    return jwt.encode({
        'reset_password': user_id, 
        'exp': datetime.utcnow() + timedelta(seconds=expires_in)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')


def verify_reset_token(token):
    """Memverifikasi token reset password dan mengembalikan user_id jika valid."""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['reset_password']
        logging.info(f"Token verified for user ID: {user_id}")
        return user_id
    except jwt.ExpiredSignatureError:
        logging.error("Token has expired.")
        return None
    except jwt.InvalidTokenError:
        logging.error("Invalid token.")
        return None
    except Exception as e:
        logging.error(f"Token verification failed: {str(e)}")
        return None
