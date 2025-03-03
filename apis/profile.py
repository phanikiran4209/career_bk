# apis/profile.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db
import bson.binary  # For storing binary data in MongoDB

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/create', methods=['POST'])
@jwt_required()
def create_profile():
    username = get_jwt_identity()

    if not request.content_type.startswith('multipart/form-data'):
        return jsonify({'message': 'Content-Type must be multipart/form-data'}), 400

    college_name = request.form.get('college_name')
    interests = request.form.getlist('interests[]')
    skills = request.form.getlist('skills[]')
    achievements = request.form.getlist('achievements[]')
    resume_file = request.files.get('resume')
    profile_photo_file = request.files.get('profile_photo')
    certificate_names = request.form.getlist('certificate_names[]')
    certificate_files = request.files.getlist('certificates[]')

    if not college_name or not resume_file:
        return jsonify({'message': 'College name and resume are required'}), 400
    if resume_file and not resume_file.filename.endswith('.pdf'):
        return jsonify({'message': 'Resume must be a PDF file'}), 400
    if profile_photo_file and not profile_photo_file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        return jsonify({'message': 'Profile photo must be JPG or PNG'}), 400
    if certificate_files:
        for cert_file in certificate_files:
            if not cert_file.filename.endswith('.pdf'):
                return jsonify({'message': 'Certificates must be PDF files'}), 400
        if len(certificate_names) != len(certificate_files):
            return jsonify({'message': 'Number of certificate names must match number of certificate files'}), 400

    resume_data = bson.binary.Binary(resume_file.read()) if resume_file else None
    profile_photo_data = bson.binary.Binary(profile_photo_file.read()) if profile_photo_file else None
    certificates_data = [
        {'name': cert_name, 'file': bson.binary.Binary(cert_file.read())}
        for cert_name, cert_file in zip(certificate_names, certificate_files)
    ] if certificate_files else []

    profile = {
        'username': username,
        'college_name': college_name,
        'resume': resume_data,
        'interests': interests,
        'skills': skills,
        'achievements': achievements,
        'profile_photo': profile_photo_data,
        'certificates': certificates_data
    }
    profile = {k: v for k, v in profile.items() if v is not None}

    db.profiles.update_one({'username': username}, {'$set': profile}, upsert=True)
    return jsonify({'message': 'Profile created/updated successfully', 'status': 'success'}), 200

@profile_bp.route('/get', methods=['GET'])
@jwt_required()
def get_profile():
    username = get_jwt_identity()
    profile = db.profiles.find_one({'username': username})
    if not profile:
        return jsonify({'message': 'Profile not found', 'exists': False}), 404

    profile_data = {
        'username': profile['username'],
        'college_name': profile.get('college_name', ''),
        'interests': profile.get('interests', []),
        'skills': profile.get('skills', []),
        'achievements': profile.get('achievements', []),
        'has_resume': 'resume' in profile,
        'has_profile_photo': 'profile_photo' in profile,
        'certificates': [{'name': cert['name']} for cert in profile.get('certificates', [])]
    }
    return jsonify({'profile': profile_data, 'exists': True}), 200