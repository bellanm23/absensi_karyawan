import os
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Attendance, AttendanceStatus, Employee
from werkzeug.utils import secure_filename
from datetime import datetime
import pytz

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,  # Atur level log yang diinginkan (INFO, ERROR, DEBUG, dsb)
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),  # Output log ke konsol
                        logging.FileHandler('app.log')  # Simpan log ke file app.log
                    ])

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/user_dashboard')
@login_required
def user_dashboard():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    attendances = Attendance.query.filter_by(employee_id=current_user.id).all()
    
    logging.info(f"User {current_user.id} accessed their dashboard.")  # Logging saat pengguna mengakses dashboard
    
    # Debugging
    print(f"Employee: {employee}")  # Cek apakah employee tidak None
    print(f"Attendances: {attendances}")  # Cek apakah attendances tidak kosong
    
    return render_template('employee/user_dashboard.html', attendances=attendances, employee=employee)

@user_bp.route('/clock_in', methods=['GET', 'POST'])
@login_required
def clock_in():
    if request.method == 'POST':
        photo = request.files.get('photo')  # Ambil file foto dari form
        lat = request.form.get('lat')
        long = request.form.get('long')

        if not photo:
            flash('Foto tidak ditemukan. Silakan coba lagi.', 'danger')
            logging.warning(f"User {current_user.id} failed clock-in: Photo not provided.")  # Logging jika foto tidak ada
            return redirect(url_for('user_bp.clock_in'))

        # Validasi latitude dan longitude
        if not lat or not long:
            flash('Latitude dan Longitude harus diisi!', 'danger')
            logging.warning(f"User {current_user.id} failed clock-in: Latitude or Longitude missing.")  # Logging jika lat/long tidak ada
            return redirect(url_for('user_bp.clock_in'))

        # Simpan foto ke folder static/uploads
        photo_filename = secure_filename(photo.filename)
        photo_path = os.path.join(current_app.root_path, 'static', 'uploads', photo_filename)
        photo.save(photo_path)

        # Simpan data absensi ke database
        attendance = Attendance(
            employee_id=current_user.id,  # Menggunakan ID karyawan yang sedang login
            status=AttendanceStatus.CLOCK_IN,
            date=datetime.today().date(),
            time=datetime.now(),
            photo=photo_filename,  # Simpan nama file foto
            latitude=float(lat),  # Konversi lat dan long ke float
            longitude=float(long)
        )
        db.session.add(attendance)
        db.session.commit()
        flash('Clock In berhasil!', 'success')
        logging.info(f"User {current_user.id} successfully clocked in at {lat}, {long} with photo {photo_filename}.")  # Logging jika clock-in berhasil
        return redirect(url_for('user_bp.user_dashboard'))

    return render_template('employee/clock_in.html')

@user_bp.route('/clock_out', methods=['GET', 'POST'])
@login_required
def clock_out():
    if request.method == 'POST':
        # Cari data clock-in terakhir
        attendance = Attendance.query.filter_by(
            employee_id=current_user.id,
            status=AttendanceStatus.CLOCK_IN
        ).order_by(Attendance.id.desc()).first()

        if not attendance:
            flash('Tidak ada data Clock In sebelumnya untuk Clock Out!', 'danger')
            logging.warning(f"User {current_user.id} attempted to clock out without clocking in.")  # Logging jika tidak ada clock-in sebelumnya
            return redirect(url_for('user_bp.user_dashboard'))

        # Update data clock-out
        attendance.time_out = datetime.now()  # Simpan waktu clock out
        attendance.status = AttendanceStatus.CLOCK_OUT
        db.session.commit()
        flash('Clock Out berhasil!', 'success')
        logging.info(f"User {current_user.id} successfully clocked out.")  # Logging jika clock-out berhasil
        return redirect(url_for('user_bp.user_dashboard'))

    return render_template('employee/clock_out.html')

@user_bp.route('/recap', methods=['GET'])
@login_required
def recap():
    # Ambil semua catatan absensi untuk karyawan yang sedang login
    attendance_records = Attendance.query.filter_by(employee_id=current_user.id).all()
    logging.info(f"User {current_user.id} accessed their attendance recap. Found {len(attendance_records)} records.")  # Logging saat mengakses recap
    return render_template('employee/recap.html', attendance_records=attendance_records, AttendanceStatus=AttendanceStatus)

@user_bp.route('/leave', methods=['GET', 'POST'])
@login_required
def leave():
    if request.method == 'POST':
        reason = request.form.get('reason')
        photo = request.files.get('photo')  # Ambil file foto dari form
        date = request.form.get('date')

        if not reason or not date:
            flash('Alasan dan tanggal harus diisi!', 'danger')
            logging.warning(f"User {current_user.id} failed leave request: Reason or date not provided.")  # Logging jika alasan atau tanggal tidak diisi
            return redirect(url_for('user_bp.leave'))

        # Simpan foto jika ada
        photo_filename = None
        if photo:
            photo_filename = secure_filename(photo.filename)
            photo.save(os.path.join(current_app.root_path, 'static', 'uploads', photo_filename))
            logging.info(f"User {current_user.id} uploaded a leave photo: {photo_filename}")  # Logging saat foto diunggah

        # Simpan pengajuan izin ke database
        attendance = Attendance(
            employee_id=current_user.id,
            status=AttendanceStatus.IJIN,
            date=datetime.strptime(date, '%Y-%m-%d'),  # Mengonversi string ke objek datetime
            time=datetime.now(),
            reason=reason,
            photo=photo_filename  # Simpan nama file foto
        )
        db.session.add(attendance)
        db.session.commit()
        flash('Pengajuan izin berhasil!', 'success')
        logging.info(f"User {current_user.id} successfully submitted a leave request for {date}.")  # Logging pengajuan izin berhasil
        return redirect(url_for('user_bp.user_dashboard'))

    return render_template('employee/leave.html')
