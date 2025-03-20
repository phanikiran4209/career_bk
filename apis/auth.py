from flask import Blueprint, request, jsonify
from database import db
from flask_jwt_extended import create_access_token
from bcrypt import hashpw, gensalt, checkpw
from apis.otp import generate_otp  # Import OTP generation function
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password').encode('utf-8')
    mobile = data.get('mobile')

    if not all([username, email, password, mobile]):
        return jsonify({'message': 'Missing required fields'}), 400

    if db.students.find_one({'email': email}):
        return jsonify({'message': 'Email already exists'}), 400

    hashed_password = hashpw(password, gensalt())
    student = {
        'username': username,
        'email': email,
        'password': hashed_password,
        'mobile': mobile
    }
    db.students.insert_one(student)
    return jsonify({'message': 'Student registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password').encode('utf-8')

    student = db.students.find_one({'username': username})
    if not student or not checkpw(password, student['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    # Generate OTP and send to registered email
    email = student['email']
    if not generate_otp(email):
        return jsonify({'message': 'Failed to send OTP'}), 500

    return jsonify({'message': 'OTP sent to registered email', 'email': email}), 200

@auth_bp.route('/verify_login_otp', methods=['POST'])
def verify_login_otp():
    data = request.get_json()
    otp = data.get('otp')

    if not otp:
        return jsonify({'message': 'OTP is required'}), 400

    # Find the OTP data by the provided OTP
    user_otp_data = db.get_collection("otp_collection").find_one({"otp": int(otp)})
    if not user_otp_data:
        return jsonify({'message': 'Invalid OTP or OTP not found'}), 400

    expiry_time = user_otp_data.get("expires_at")
    if datetime.utcnow() > expiry_time:
        return jsonify({'message': 'OTP expired'}), 400

    # Get the email from OTP data and find the corresponding student
    email = user_otp_data.get("email")
    student = db.students.find_one({'email': email})
    if not student:
        return jsonify({'message': 'User not found'}), 400

    # If OTP matches, generate JWT token
    username = student['username']
    access_token = create_access_token(identity=username)
    profile = db.profiles.find_one({'username': username})
    redirect = 'profile' if not profile or not profile.get('profile_completed') else 'dashboard'
    return jsonify({'token': access_token, 'redirect': redirect}), 200