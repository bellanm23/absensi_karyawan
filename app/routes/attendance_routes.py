import os
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app, jsonify
from app import db
from app.models import Attendance, AttendanceStatus
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,  # Atur level log yang diinginkan (INFO, ERROR, DEBUG, dsb)
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Output log ke konsol
                        logging.FileHandler('app.log')  # Simpan log ke file app.log
                    ])

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/recap', methods=['GET', 'POST'])
@jwt_required()  # Menggunakan @jwt_required untuk memeriksa otentikasi JWT
def recap():
    # Mendapatkan user_id dari token JWT yang sudah diverifikasi
    user_id = get_jwt_identity()
    
    if request.method == 'POST':
        try:
            # Logika untuk menerima data POST, misalnya menyimpan atau memperbarui data absensi
            data = request.get_json()  # Ambil data JSON dari body
            logging.info(f"Data received: {data}")

            # Simulasi proses data atau penyimpanan
            return jsonify({'status': 'success', 'message': 'Data received successfully'}), 200

        except Exception as e:
            logging.error(f"Error during POST request: {e}")
            return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500

    elif request.method == 'GET':
        # Mengambil catatan absensi berdasarkan user_id yang didapat dari JWT
        attendance_records = Attendance.query.filter_by(employee_id=user_id).all()
        logging.info(f"Recap page accessed by user: {user_id}, Found {len(attendance_records)} attendance records")

        # Return halaman recap untuk karyawan atau pengguna
        return render_template('employee/recap.html', attendance_records=attendance_records, AttendanceStatus=AttendanceStatus)

