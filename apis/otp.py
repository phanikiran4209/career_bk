import smtplib
from flask import Blueprint, request, jsonify
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from random import randint
from database import db
from datetime import datetime, timedelta
from config import Config

otp_bp = Blueprint('otp', __name__)

# Email Configuration (Use environment variables for security)
EMAIL = "careervisionvvit@gmail.com"
APP_PASSWORD = "ojdm oxfu lzjh saoj"

def generate_otp(email):
    """Generates and stores an OTP in the database, then sends it via email."""
    try:
        otp = randint(100000, 999999)
        expiry_time = datetime.utcnow() + timedelta(minutes=5)  # OTP expires in 5 minutes
        
        # Store OTP in MongoDB
        db.get_collection("otp_collection").update_one(
            {"email": email},
            {"$set": {"otp": otp, "expires_at": expiry_time}},
            upsert=True
        )

        # Email Content
        subject = "CareerVision Authorization - OTP Verification"
        body = f"""
        Dear User,

        Your OTP for CareerVision authorization is: {otp}

        Please enter this OTP to complete your verification.

        Regards,  
        CareerVision Team
        """

        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Send Email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, APP_PASSWORD)
        server.sendmail(EMAIL, email, msg.as_string())
        server.quit()

        return True

    except Exception as e:
        print(f"Error sending OTP email: {str(e)}")
        return False


@otp_bp.route('/send_otp', methods=['POST'])
def send_otp():
    """API endpoint to send OTP to the user's email."""
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    if generate_otp(email):
        return jsonify({'message': 'OTP sent successfully'}), 200
    else:
        return jsonify({'error': 'Failed to send OTP'}), 500


@otp_bp.route('/verify_otp', methods=['POST'])
def verify_otp():
    """API endpoint to verify OTP."""
    data = request.get_json()
    email = data.get('email')
    entered_otp = data.get('otp')

    if not email or not entered_otp:
        return jsonify({'error': 'Email and OTP are required'}), 400

    user_otp_data = db.get_collection("otp_collection").find_one({"email": email})

    if not user_otp_data:
        return jsonify({'error': 'OTP not found'}), 400

    stored_otp = user_otp_data.get("otp")
    expiry_time = user_otp_data.get("expires_at")

    if datetime.utcnow() > expiry_time:
        return jsonify({'error': 'OTP expired'}), 400

    if int(entered_otp) == stored_otp:
        return jsonify({'message': 'OTP verified successfully'}), 200
    else:
        return jsonify({'error': 'Invalid OTP'}), 400