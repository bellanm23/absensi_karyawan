import logging
from flask import current_app
import jwt
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import Column, Integer, DateTime, Text, Float, Time, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum
from logging.handlers import RotatingFileHandler
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename


Base = declarative_base()

# Impor db di bagian bawah file
from . import db

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),
                        RotatingFileHandler('app.log', maxBytes=1000000, backupCount=5)
                    ])

# Model User
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Integer, default=0)  # 0 = user, 1 = admin

    # Relasi ke Employee
    employees = db.relationship('Employee', back_populates='user', lazy=True, cascade="all, delete-orphan")

    def get_reset_token(self, expires_in=600):
        logging.info(f"Generating reset token for user with ID: {self.id}")  # Log saat token reset dibuat
        return jwt.encode({'reset_password': self.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)},
                           current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_token(token):
        try:
            user_id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
            logging.info(f"Token verified for user with ID: {user_id}")  # Log setelah token diverifikasi
        except Exception as e:
            logging.error(f"Token verification failed: {str(e)}")  # Log error jika token tidak valid
            return None
        return User.query.get(user_id)

# Model Employee
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    gender = db.Column(db.String(6), nullable=False)
    photo_profile = db.Column(db.Text)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone_number = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relasi ke User
    user = db.relationship('User', back_populates='employees')

    # Relasi ke Attendance
    attendances = db.relationship('Attendance', back_populates='employee', lazy=True, cascade="all, delete-orphan")

# Enum untuk status attendance
class AttendanceStatus(Enum):
    ALPHA = "ALPHA"
    IJIN = "IJIN"
    TIDAK_HADIR = "TIDAK HADIR"
    HADIR = "HADIR"

# Model Attendance
class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.user_id'), nullable=False)  # Foreign key ke employees
    status = db.Column(db.Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.ALPHA)
    date = db.Column(db.Date, nullable=False)  # Menyimpan tanggal presensi
    time = db.Column(db.Time, nullable=False)  # Waktu masuk
    time_out = db.Column(db.Time, default=None)  # Waktu keluar
    photo = db.Column(db.Text, default=None)  # Lokasi file foto
    latitude = db.Column(db.Float, default=None)
    longitude = db.Column(db.Float, default=None)
    reason = db.Column(db.Text, default="N/A")  # Alasan jika 'IJIN' atau lainnya

    # Relasi ke Employee
    employee = db.relationship('Employee', back_populates='attendances', lazy=True)

    def save(self):
        """Save or update the attendance record"""
        try:
            if self.id is None:
                logging.info(f"Creating new attendance record for employee ID: {self.employee_id}")
            else:
                logging.info(f"Updating attendance record ID: {self.id} for employee ID: {self.employee_id}")
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error saving attendance: {e}")
            raise e

    @staticmethod
    def validate_time_format(time_str):
        """Validate time format (HH:MM:SS)"""
        try:
            return datetime.strptime(time_str, '%H:%M:%S').time()
        except ValueError:
            raise ValueError("Invalid time format. Use 'HH:MM:SS'.")

    @staticmethod
    def create_attendance(employee_id, status, date, time, time_out=None, photo=None, latitude=None, longitude=None, reason=None):
        """Create a new attendance record"""
        try:
            new_attendance = Attendance(
                employee_id=employee_id,
                status=status or AttendanceStatus.ALPHA,
                date=datetime.strptime(date, '%Y-%m-%d').date(),
                time=Attendance.validate_time_format(time),
                time_out=Attendance.validate_time_format(time_out) if time_out else None,
                photo=secure_filename(photo) if photo else None,
                latitude=latitude,
                longitude=longitude,
                reason=reason or "N/A"
            )
            new_attendance.save()
            return new_attendance
        except Exception as e:
            logging.error(f"Error creating attendance record: {e}")
            raise e

    @classmethod
    def get_attendance_by_date(cls, employee_id, date):
        """Get attendance for a specific date"""
        return cls.query.filter_by(employee_id=employee_id, date=date).first()

    @property
    def formatted_status(self):
        """Get human-readable status"""
        return self.status.value if self.status else "UNKNOWN"

    @property
    def formatted_time_in(self):
        """Format time-in for display"""
        return self.time.strftime("%H:%M:%S") if self.time else "N/A"

    @property
    def formatted_time_out(self):
        """Format time-out for display"""
        return self.time_out.strftime("%H:%M:%S") if self.time_out else "N/A"

    def __repr__(self):
        return f"<Attendance {self.id} - Employee {self.employee_id} - Status {self.status.value}>"


# Model LocationSetting
class LocationSetting(db.Model):
    __tablename__ = 'location_settings'

    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius = db.Column(db.Float, nullable=False)
    clock_in = db.Column(db.Time, nullable=False)
    clock_out = db.Column(db.Time, nullable=False)

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<LocationSetting Latitude {self.latitude}, Longitude {self.longitude}, Radius {self.radius}>"
    
    def save(self):
        """Override save method to log location setting changes"""
        logging.info(f"Saving location setting ID: {self.id} with latitude: {self.latitude}, longitude: {self.longitude}")
        db.session.add(self)
        db.session.commit()

