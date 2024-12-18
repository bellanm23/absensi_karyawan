import logging, jwt
from flask import Blueprint, request, jsonify, url_for, render_template, redirect, session
from flask_login import login_user, logout_user, current_user
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User
from app.utils import generate_jwt_token, generate_reset_token, verify_reset_token
from flask_bcrypt import Bcrypt
from app import db

# Inisialisasi Blueprint dan Bcrypt
auth_bp = Blueprint('auth_bp', __name__)
bcrypt = Bcrypt()

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),
                        logging.FileHandler('app.log')
                    ])


@auth_bp.route('/login', methods=['POST'])
def login():
        try:
            if request.is_json:
                email = request.json.get('email')
                password = request.json.get('password')
            else:
                email = request.form.get('email')
                password = request.form.get('password')

            user = User.query.filter_by(email=email).first()
            if user is None:
                return jsonify({'msg': 'Email tidak ditemukan'}), 404

            if not bcrypt.check_password_hash(user.password, password):
                return jsonify({'msg': 'Password salah'}), 401

            # Buat token dan sertakan status serta id dalam identity
            token = create_access_token(identity={'email': user.email, 'status': user.status, 'id': user.id})

            return jsonify({
                'status': 'success',
                'message': 'Login berhasil!',
                'token': token,
                'user_status': user.status  # Menggunakan user_status untuk membedakan dengan 'status'
            }), 200

        except Exception as e:
            logging.error(f"Error during login: {str(e)}")
            return jsonify({'msg': 'Internal server error'}), 500


# Route Logout
@auth_bp.route('/logout', methods=['POST'])  # Hanya izinkan POST
@jwt_required()  # Token wajib untuk POST
def logout():
    try:
        # Log aktivitas logout
        jwt_header = request.headers.get('Authorization')
        if jwt_header:
            logging.info(f"JWT Token Received in Header: {jwt_header}")
        else:
            logging.warning("No JWT Token found in Authorization Header.")

        # Mendapatkan identitas pengguna dari token
        identity = get_jwt_identity()
        logging.info(f"User {identity} attempting to log out.")

        # Respons logout sukses
        return jsonify({'status': 'success', 'message': 'Logout berhasil!'}), 200
    except Exception as e:
        logging.error(f"Error during logout: {str(e)}")
        return jsonify({'msg': 'Internal server error'}), 500


# Route untuk forgot-password
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    
    # Jika POST request, proses email
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'status': 'error', 'message': 'Email harus diisi!'}), 400

    email = data['email']
    user = User.query.filter_by(email=email).first()
    if user:
        token = generate_reset_token(user.id)
        reset_url = url_for('auth_bp.reset_password', token=token, _external=True)
        return jsonify({'status': 'success', 'message': 'Token berhasil dibuat', 'reset_url': reset_url}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Email tidak ditemukan.'}), 404


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'GET':
        # Tampilkan halaman reset password (HTML)
        return render_template('auth/reset_password.html', token=token)

    # Proses jika POST request (perbarui password)
    user_id = verify_reset_token(token)
    if user_id is None:
        return jsonify({'status': 'error', 'message': 'Token tidak valid atau kedaluwarsa.'}), 401

    user = User.query.get(user_id)
    if user:
        data = request.get_json()
        if not data or 'new_password' not in data:
            return jsonify({'status': 'error', 'message': 'Password baru harus diisi!'}), 400

        new_password = data['new_password']

        # Hash password baru
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')  # Menggunakan bcrypt untuk hash

        # Update password user di database
        user.password = hashed_password
        db.session.commit()  # Simpan perubahan ke database

        logging.info(f"Password reset successfully for user {user.email}")
        return jsonify({'status': 'success', 'message': 'Password berhasil diperbarui.'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'User tidak ditemukan.'}), 404