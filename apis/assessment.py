# apis/assessment.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db

assessment_bp = Blueprint('assessment', __name__)

@assessment_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_assessment():
    username = get_jwt_identity()
    data = request.get_json()
    assessment_id = data.get('assessment_id')  # Test name/title
    score = data.get('score')
    date = data.get('date')

    if not all([assessment_id, score, date]):
        return jsonify({'message': 'Missing required fields'}), 400

    assessment_result = {
        'username': username,
        'assessment_id': assessment_id,
        'score': float(score),
        'date': date
    }
    db.assessments.insert_one(assessment_result)

    return jsonify({'message': 'Assessment submitted'}), 201

@assessment_bp.route('/list', methods=['GET'])
@jwt_required()
def list_assessments():
    assessments = list(db.admin_assessments.find({}, {'_id': 0}))
    return jsonify(assessments), 200