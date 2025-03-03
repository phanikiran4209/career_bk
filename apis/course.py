# apis/course.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db

course_bp = Blueprint('course', __name__)

@course_bp.route('/complete', methods=['POST'])
@jwt_required()
def complete_course():
    username = get_jwt_identity()
    data = request.get_json()
    course_title = data.get('course_title')

    if not course_title:
        return jsonify({'message': 'Course title is required'}), 400

    result = db.courses.update_one(
        {'course_title': course_title},
        {'$addToSet': {'completed_by': username}}
    )
    if result.modified_count > 0:
        return jsonify({'message': 'Course marked as completed'}), 200
    return jsonify({'message': 'Course already completed or not found'}), 400

# Register this blueprint in app.py
# app.register_blueprint(course_bp, url_prefix='/course')