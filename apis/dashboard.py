# apis/dashboard.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/student', methods=['GET'])
@jwt_required()
def student_dashboard():
    username = get_jwt_identity()
    assessments = list(db.assessments.find({'username': username}))

    tests_taken = len(assessments)
    highest_score = max([a['score'] for a in assessments], default=0) if assessments else 0

    test_stats = {}
    for a in assessments:
        test_name = a['assessment_id']
        if test_name not in test_stats:
            test_stats[test_name] = {'count': 0, 'highest_score': 0}
        test_stats[test_name]['count'] += 1
        test_stats[test_name]['highest_score'] = max(test_stats[test_name]['highest_score'], a['score'])

    graph_data = [
        {'test_name': name, 'tests': stats['count'], 'highest_score': stats['highest_score']}
        for name, stats in test_stats.items()
    ]

    courses = list(db.courses.find({}, {'_id': 0}))
    sessions = list(db.sessions.find({}, {'_id': 0}))

    return jsonify({
        'tests_taken': tests_taken,
        'highest_score': highest_score,
        'assessments': [{'title': a['assessment_id'], 'score': a['score'], 'date': a['date']} for a in assessments],
        'graph_data': graph_data,
        'courses': courses,
        'sessions': sessions
    }), 200

@dashboard_bp.route('/course/complete', methods=['POST'])
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