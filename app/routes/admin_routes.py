import logging
import datetime
from datetime import datetime, time
from functools import wraps
import re
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.models import User, Attendance, Employee, LocationSetting, AttendanceStatus
from flask_bcrypt import Bcrypt
from app import db
import uuid
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,  # Atur level log yang diinginkan (INFO, ERROR, DEBUG, dsb)
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Output log ke konsol
                        logging.FileHandler('app.log')  # Simpan log ke file app.log
                    ])

admin_bp = Blueprint('admin_bp', __name__)
bcrypt = Bcrypt()


# Endpoint untuk menambah employee
@admin_bp.route('/add_employee', methods=['POST'])
@jwt_required()  # Melindungi endpoint ini dengan token
def add_employee():
    # Mendapatkan ID pengguna dari token yang diterima
    current_user_id = get_jwt_identity()

    # Ambil data dari JSON
    data = request.get_json()
    name = data.get('name')
    gender = data.get('gender')
    email = data.get('email')
    phone_number = data.get('phone_number')
    password = data.get('password')
    photo = data.get('photo')

    # Validasi input
    if not name or not email or not password or not phone_number:
        return jsonify({'status': 'error', 'message': 'All fields are required!'}), 400

    # Cek apakah email sudah ada
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'status': 'error', 'message': 'Email already exists!'}), 400

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        # Simpan data ke database untuk user dan employee
        new_user = User(email=email, password=hashed_password, status=0)
        db.session.add(new_user)
        db.session.commit()

        new_employee = Employee(
            name=name,
            gender=gender,
            email=email,
            phone_number=phone_number,
            password=hashed_password,
            photo_profile=photo,  # Foto yang diambil, pastikan sudah diproses dengan benar
            user_id=new_user.id
        )
        db.session.add(new_employee)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Employee added successfully!'}), 201

    except Exception as e:
        db.session.rollback()  # Membatalkan transaksi jika terjadi kesalahan
        logging.error(f"Error while adding employee: {e}")
        return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500


@admin_bp.route('/edit_employee/<int:id>', methods=['POST'])
@jwt_required()
def edit_employee(id):
    # Ambil data pegawai berdasarkan ID
    employee = Employee.query.get_or_404(id)
    
    # Ambil data JSON yang dikirimkan
    data = request.get_json()

    logging.info(f"Data received for editing employee {id}: {data}")

    # Validasi input
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({'status': 'error', 'message': 'Name and email are required!'}), 422

    # Validasi format email
    email = data['email']
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'status': 'error', 'message': 'Invalid email format!'}), 422

    # Cek apakah email sudah digunakan oleh pegawai lain
    existing_employee = Employee.query.filter_by(email=email).first()
    if existing_employee and existing_employee.id != id:
        return jsonify({'status': 'error', 'message': 'Email already in use by another employee!'}), 400

    try:
        # Update data pegawai
        employee.name = data['name']
        employee.email = email
        db.session.commit()

        logging.info(f'Employee with ID {id} updated successfully.')
        return jsonify({'status': 'success', 'message': 'Employee updated successfully!'}), 200

    except Exception as e:
        logging.error(f"Error updating employee {id}: {str(e)}")
        db.session.rollback()  # Rollback jika terjadi kesalahan saat commit
        return jsonify({'status': 'error', 'message': 'Failed to update employee. Please try again later.'}), 500



# Endpoint untuk menghapus employee
@admin_bp.route('/delete_employee/<int:id>', methods=['POST'])
@jwt_required()
def delete_employee(id):
    # Proses penghapusan data
    employee = Employee.query.filter_by(user_id=id).first()
    if not employee:
        return jsonify({'status': 'error', 'message': 'Employee not found!'}), 404

    try:
        Attendance.query.filter_by(employee_id=employee.id).delete()
        db.session.delete(employee)
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'User and all related records deleted successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        logging.error(f'Error deleting user with ID {id}: {e}')
        return jsonify({'status': 'error', 'message': f'Error deleting user: {e}'}), 500



@admin_bp.route('/list_employees', methods=['GET'])
@jwt_required()
def list_employee():
    # Ambil semua employee dari database
    try:
        employees = Employee.query.all()
        employees_data = [{
            'id': employee.id,
            'name': employee.name,
            'gender': employee.gender,
            'email': employee.email,
            'phone_number': employee.phone_number,
            'photo_profile': employee.photo_profile
        } for employee in employees]

        logging.info(f'{len(employees)} employees listed.')
        return jsonify({'status': 'success', 'employees': employees_data}), 200
    except Exception as e:
        logging.error(f"Error fetching employees: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to retrieve employees'}), 500




# @admin_bp.route('/attendance_report', methods=['GET'])
# @jwt_required()
# def attendance_report():
#     # Ambil email pengguna dari token JWT
#     user_data = get_jwt_identity()  # Ini mengembalikan dictionary
#     user_email = user_data.get('email')  # Ambil hanya email dari dictionary

#     # Validasi admin
#     user = User.query.filter_by(email=user_email).first()
#     if not user:
#         logging.warning(f"User with email {user_email} not found.")
#         return jsonify({'status': 'error', 'message': 'User not found'}), 404

#     if user.status != 1:
#         logging.warning(f"Access denied for user {user_email}. Not an admin.")
#         return jsonify({'status': 'error', 'message': 'Access denied'}), 403

#     try:
#         # Query join Attendance dan Employee
#         attendances = db.session.query(Attendance, Employee.name).join(
#             Employee, Attendance.employee_id == Employee.user_id
#         ).all()

#         # Format hasil query ke JSON
#         attendance_data = [{
#             'employee_id': attendance.employee_id,
#             'employee_name': name,  # Nama karyawan dari tabel Employee
#             'status': attendance.status.value if hasattr(attendance.status, 'value') else str(attendance.status),  # Konversi ke string
#             'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else 'N/A',  # Tanggal tanpa waktu
#             'time': attendance.time.strftime('%H:%M:%S') if attendance.time else 'N/A',  # Hanya jam:menit:detik
#             'time_out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else 'N/A'  # Hanya jam:menit:detik
#         } for attendance, name in attendances]

#         logging.info(f"{len(attendances)} attendance records fetched.")
#         return jsonify({'status': 'success', 'attendance': attendance_data}), 200

#     except Exception as e:
#         logging.error(f"Error fetching attendance report: {str(e)}")
#         return jsonify({'status': 'error', 'message': 'Failed to retrieve attendance report'}), 500

@admin_bp.route('/attendance_report', methods=['GET'])
@jwt_required()
def attendance_report():
    # Ambil email pengguna dari token JWT
    user_data = get_jwt_identity()  # Ini mengembalikan dictionary
    user_email = user_data.get('email')  # Ambil hanya email dari dictionary

    # Validasi admin
    user = User.query.filter_by(email=user_email).first()
    if not user:
        logging.warning(f"User with email {user_email} not found.")
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    if user.status != 1:
        logging.warning(f"Access denied for user {user_email}. Not an admin.")
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403

    try:
        # Query join Attendance dan Employee
        attendances = db.session.query(Attendance, Employee.name).join(
            Employee, Attendance.employee_id == Employee.user_id
        ).all()

        # Format hasil query ke JSON
        attendance_data = []
        for attendance, name in attendances:
            # Tentukan status absensi (Alpha jika tidak ada absensi, Hadir atau Izin sesuai status)
            if attendance.status == AttendanceStatus.HADIR:
                status = 'Hadir'
            elif attendance.status == AttendanceStatus.IJIN:
                status = 'Izin'
            else:
                status = 'Alpha'  # Jika tidak ada absensi, dianggap Alpha

            attendance_data.append({
                'employee_id': attendance.employee_id,
                'employee_name': name,  # Nama karyawan dari tabel Employee
                'status': status,  # Status absensi
                'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else 'N/A',  # Tanggal tanpa waktu
                'time': attendance.time.strftime('%H:%M:%S') if attendance.time else 'N/A',  # Hanya jam:menit:detik
                'time_out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else 'N/A'  # Hanya jam:menit:detik
            })

        logging.info(f"{len(attendance_data)} attendance records fetched.")
        return jsonify({'status': 'success', 'attendance': attendance_data}), 200

    except Exception as e:
        logging.error(f"Error fetching attendance report: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to retrieve attendance report'}), 500



@admin_bp.route('/location_settings', methods=['GET', 'POST'])
@jwt_required()
def location_settings():
    if request.method == 'GET':
        # Mengambil pengaturan lokasi
        settings = LocationSetting.query.first()  # Ambil pengaturan lokasi pertama
        if settings:
            return jsonify({
                'latitude': settings.latitude,
                'longitude': settings.longitude,
                'radius': settings.radius,
                'clock_in': settings.clock_in.strftime('%H:%M:%S'),  # Format hanya jam:menit:detik
                'clock_out': settings.clock_out.strftime('%H:%M:%S')  # Format hanya jam:menit:detik
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'No location settings found.'}), 404

    elif request.method == 'POST':
        # Mengambil data JSON dari permintaan
        data = request.get_json()

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        radius = data.get('radius')
        clock_in_str = data.get('clock_in')
        clock_out_str = data.get('clock_out')

        # Mengonversi string clock_in dan clock_out ke objek waktu (hanya jam, menit, detik)
        clock_in = datetime.strptime(clock_in_str, '%H:%M:%S').time()  # Format HH:MM:SS
        clock_out = datetime.strptime(clock_out_str, '%H:%M:%S').time()  # Format HH:MM:SS

        # Simpan data ke database
        new_setting = LocationSetting(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            clock_in=clock_in,
            clock_out=clock_out
        )
        db.session.add(new_setting)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Location settings saved successfully!'}), 201
