from flask import Blueprint, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth
import os
import json
import random
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Firebase service account key from the environment variable
firebase_service_account_key = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')

if not firebase_service_account_key:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable is not set")

# Parse the JSON string from the environment variable
cred = credentials.Certificate(json.loads(firebase_service_account_key))

# Initialize Firebase Admin SDK
firebase_admin.initialize_app(cred)

otp_bp = Blueprint('otp', __name__)

# In-memory storage for OTPs (for demo purposes; use a database in production)
otp_store = {}

# Email configuration (replace with your SMTP details or use a service like SendGrid)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-app-password')

def send_otp_email(email: str, otp: str):
    msg = MIMEText(f'Your OTP for careervision-d2e55 is: {otp}. It is valid for 5 minutes.')
    msg['Subject'] = 'Your OTP for Password Reset'
    msg['From'] = SMTP_USER
    msg['To'] = email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

@otp_bp.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))
        # Store OTP with expiration (5 minutes)
        otp_store[email] = {
            'otp': otp,
            'expires_at': datetime.now() + timedelta(minutes=5)
        }

        # Send OTP via email
        send_otp_email(email, otp)

        return jsonify({
            'message': f'OTP sent to {email}. It is valid for 5 minutes.'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@otp_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        provided_otp = data.get('otp')

        if not email or not provided_otp:
            return jsonify({'error': 'Email and OTP are required'}), 400

        # Check if OTP exists and is valid
        if email in otp_store:
            stored_otp_data = otp_store[email]
            if datetime.now() > stored_otp_data['expires_at']:
                del otp_store[email]
                return jsonify({'error': 'OTP has expired'}), 400
            if stored_otp_data['otp'] == provided_otp:
                del otp_store[email]  # Clear OTP after successful verification
                # Optionally, sign in or update user in Firebase
                user = auth.get_user_by_email(email)  # Ensure the user exists
                return jsonify({
                    'message': 'Successfully verified OTP',
                    'user_id': user.uid
                }), 200
            else:
                return jsonify({'error': 'Invalid OTP'}), 400
        else:
            return jsonify({'error': 'No OTP found for this email'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500