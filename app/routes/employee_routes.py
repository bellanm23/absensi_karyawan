import os
import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Attendance, AttendanceStatus, Employee, User
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,  # Atur level log yang diinginkan (INFO, ERROR, DEBUG, dsb)
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Output log ke konsol
                        logging.FileHandler('app.log')  # Simpan log ke file app.log
                    ])

home_bp = Blueprint('home_bp', __name__)

# @home_bp.route('/')
# def index():
#     user_status = 1  # Atau logika untuk menentukan status pengguna
#     return render_template('home.html', user_status=user_status)

@home_bp.route('/')
def index():
    # Anda bisa menambahkan logika untuk menentukan status pengguna di sini
    user_status = current_user.status if current_user.is_authenticated else None
    return render_template('home.html', user_status=user_status)

employee_bp = Blueprint('employee', __name__)


@employee_bp.route('/user_dashboard', methods=['GET'])
@jwt_required()
def user_dashboard():
    user_data = get_jwt_identity()  # Mengambil data pengguna dari JWT token
    user_id = user_data.get('id')  # Pastikan 'id' ada dalam identity saat login

    # Ambil data Employee dan Attendance
    employee = Employee.query.filter_by(user_id=user_id).first()
    attendances = Attendance.query.filter_by(employee_id=user_id).all()

    logging.info(f"User {user_id} accessed their dashboard.")
    
    # Debugging
    print(f"Employee: {employee}")  
    print(f"Attendances: {attendances}")  

    return jsonify({
        'status': 'success',
        'employee': {
            'name': employee.name if employee else 'N/A',
            'position': employee.position if employee else 'N/A'
        },
        'attendances': [
            {
                'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else 'N/A',
                'time': attendance.time.strftime('%H:%M:%S') if attendance.time else 'N/A',
                'status': attendance.status
            } for attendance in attendances
        ]
    }), 200

@employee_bp.route('/profile', methods=['GET', 'POST'])
@jwt_required()  # Menggunakan @jwt_required untuk memeriksa otentikasi JWT
def profile():
    user_data = get_jwt_identity()  # Ini akan mengembalikan data dalam format dictionary
    user_id = user_data.get('id')  # Pastikan untuk mendapatkan 'id' jika hasilnya dictionary
    logging.info(f"User data from token: {user_data}")
    logging.info(f"User ID from token: {user_id}")

    # Untuk permintaan GET, tampilkan data profil dalam format JSON
    if request.method == 'GET':
        employee = Employee.query.filter_by(user_id=user_id).first()  # Mencari employee berdasarkan user_id
        if employee:
            # Return data profil dalam format JSON
            employee_data = {
                'id': employee.id,
                'name': employee.name,
                'gender': employee.gender,
                'email': employee.email,
                'phone_number': employee.phone_number,
                'photo_profile': employee.photo_profile
            }
            return jsonify({'status': 'success', 'employee': employee_data}), 200
        else:
            logging.warning(f"Employee not found for user_id {user_id}")
            return jsonify({'status': 'error', 'message': 'Employee not found'}), 404



@employee_bp.route('/recap', methods=['GET'])
@jwt_required()
def attendance_report():
    # Ambil email pengguna dari token JWT
    user_data = get_jwt_identity()  # Ini akan mengembalikan dictionary
    user_email = user_data.get('email')  # Ambil hanya 'email' dari dictionary

    if not user_email:
        logging.warning('User not authenticated.')
        return jsonify({'status': 'error', 'message': 'User not authenticated'}), 401

    # Dapatkan data pengguna berdasarkan email
    user = User.query.filter_by(email=user_email).first()

    if not user:
        logging.warning(f'User with email {user_email} not found.')
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    try:
        # Mengambil semua catatan absensi untuk pengguna yang sedang login
        attendances = Attendance.query.filter_by(employee_id=user.id).all()  # Filter berdasarkan employee_id
        attendance_data = [{
            'employee_id': attendance.employee_id,
            'status': attendance.status.value if hasattr(attendance.status, 'value') else str(attendance.status),
            'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else 'N/A',  # Tanggal tanpa waktu
            'time': attendance.time.strftime('%H:%M:%S') if attendance.time else 'N/A',  # Hanya jam:menit:detik
            'time_out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else 'Belum Clock Out',  # Hanya jam:menit:detik
            'photo': attendance.photo,
            'latitude': attendance.latitude,
            'longitude': attendance.longitude,
            'reason': attendance.reason
        } for attendance in attendances]

        logging.info(f'{len(attendances)} attendance records fetched for user {user.email}.')

        return jsonify({'status': 'success', 'attendance': attendance_data}), 200

    except Exception as e:
        logging.error(f"Error fetching attendance report: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to retrieve attendance report'}), 500

    
@employee_bp.route('/attendance', methods=['POST'])
@jwt_required()
def record_attendance():
    try:
        # Ambil data JSON dari permintaan POST
        data = request.get_json()
        
        date = data.get('date')
        time = data.get('time')  # Waktu masuk
        time_out = data.get('time_out')  # Waktu keluar (opsional)
        photo = data.get('photo')  # Foto absensi (opsional)
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Validasi data yang diperlukan
        if not date or not time:
            return jsonify({'status': 'error', 'message': 'Date and time are required'}), 400
        
        if latitude is None or longitude is None:
            return jsonify({'status': 'error', 'message': 'Latitude and longitude are required'}), 400

        # Konversi data
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        time_obj = datetime.strptime(time, '%H:%M:%S').time()
        time_out_obj = None
        if time_out:
            time_out_obj = datetime.strptime(time_out, '%H:%M:%S').time()

        # Simpan foto jika ada
        photo_filename = None
        if photo:
            photo_filename = secure_filename(photo)
            with open(os.path.join(current_app.root_path, 'static', 'uploads', photo_filename), 'wb') as f:
                f.write(photo.encode('utf-8'))

        # Ambil employee_id dari JWT
        user_identity = get_jwt_identity()
        employee_id = user_identity['id']  # Ambil ID user dari JWT

        # Simpan presensi ke database
        attendance = Attendance(
            employee_id=employee_id,
            status=AttendanceStatus.HADIR,  # Default HADIR
            date=date_obj,
            time=time_obj,
            time_out=time_out_obj,
            reason=None,  # Tidak ada alasan untuk absensi
            photo=photo_filename,
            latitude=latitude,
            longitude=longitude
        )
        db.session.add(attendance)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Attendance recorded successfully'}), 200

    except Exception as e:
        logging.error(f"Error while recording attendance: {e}")
        return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500


@employee_bp.route('/leave', methods=['POST'])
@jwt_required()
def submit_leave():
    try:
        # Ambil data JSON dari permintaan POST
        data = request.get_json()

        date = data.get('date')
        time = data.get('time')  # Waktu permohonan izin
        reason = data.get('reason', 'N/A')  # Alasan izin (default 'N/A' jika kosong)
        photo = data.get('photo')  # Foto pendukung (opsional)
        # latitude = data.get('latitude')
        # longitude = data.get('longitude')

        # Validasi data yang diperlukan
        if not date or not time:
            return jsonify({'status': 'error', 'message': 'Date and time are required'}), 400
        
        if not reason:
            return jsonify({'status': 'error', 'message': 'Reason is required'}), 400

        # if latitude is None or longitude is None:
        #     return jsonify({'status': 'error', 'message': 'Latitude and longitude are required'}), 400

        # Konversi data
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        time_obj = datetime.strptime(time, '%H:%M:%S').time()

        # Simpan foto jika ada
        photo_filename = None
        if photo:
            photo_filename = secure_filename(photo)
            with open(os.path.join(current_app.root_path, 'static', 'uploads', photo_filename), 'wb') as f:
                f.write(photo.encode('utf-8'))

        # Ambil employee_id dari JWT
        user_identity = get_jwt_identity()
        employee_id = user_identity['id']  # Ambil ID user dari JWT

        # Simpan pengajuan izin ke database
        attendance = Attendance(
            employee_id=employee_id,
            status=AttendanceStatus.IJIN,  # Status IJIN
            date=date_obj,
            time=time_obj,
            time_out=None,  # Tidak ada waktu keluar untuk izin
            reason=reason,
            photo=photo_filename,
            latitude=None,
            longitude=None
        )
        db.session.add(attendance)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Leave request submitted successfully'}), 200

    except Exception as e:
        logging.error(f"Error while submitting leave: {e}")
        return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500
    

@employee_bp.route('/attendance_status', methods=['GET'])
@jwt_required()
def check_attendance_status():
    try:
        # Ambil data dari query parameter
        date = request.args.get('date')
        if not date:
            return jsonify({'status': 'error', 'message': 'Date is required'}), 400

        # Konversi tanggal dari string ke datetime
        date_obj = datetime.strptime(date, '%Y-%m-%d')

        # Ambil employee_id dari JWT
        user_identity = get_jwt_identity()
        employee_id = user_identity['id']

        # Cari absensi berdasarkan employee_id dan date
        attendance = Attendance.query.filter_by(employee_id=employee_id, date=date_obj).first()

        if attendance:
            # Jika ditemukan absensi, tampilkan status
            return jsonify({
                'status': 'success',
                'message': f'Attendance status: {attendance.status}',
                'attendance_status': attendance.status
            }), 200
        else:
            # Jika tidak ditemukan absensi, berarti Alpha (tidak hadir)
            return jsonify({
                'status': 'success',
                'message': 'Attendance status: Alpha (Tidak Hadir)',
                'attendance_status': 'Alpha'
            }), 200

    except Exception as e:
        logging.error(f"Error while checking attendance status: {e}")
        return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500
    







