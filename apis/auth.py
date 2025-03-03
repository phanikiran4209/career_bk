# apis/auth.py
from flask import Blueprint, request, jsonify
from database import db
from flask_jwt_extended import create_access_token
from bcrypt import hashpw, gensalt, checkpw

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
    if student and checkpw(password, student['password']):
        access_token = create_access_token(identity=username)
        return jsonify({'token': access_token}), 200
    return jsonify({'message': 'Invalid credentials'}), 401