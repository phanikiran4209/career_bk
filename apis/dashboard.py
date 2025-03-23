from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db
import base64

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

@dashboard_bp.route('/profile/photo', methods=['GET'])
@jwt_required()
def get_profile_photo():
    # Get the username from the JWT token
    username = get_jwt_identity()

    # Find the user's profile in the database
    profile = db.profiles.find_one({'username': username}, {'profile_photo': 1})

    if not profile:
        return jsonify({'message': 'Profile not found'}), 404

    # Check if the profile has a photo
    if 'profile_photo' not in profile or not profile['profile_photo']:
        return jsonify({'message': 'Profile photo not found'}), 404

    # Get the profile photo (assuming it's stored as a base64 string)
    # If it's stored as raw binary data, you can directly use profile['profile_photo']
    try:
        # Decode the base64 string to binary data (remove this if the photo is already binary)
        photo_data = base64.b64decode(profile['profile_photo'])
    except Exception as e:
        return jsonify({'message': f'Error decoding profile photo: {str(e)}'}), 500

    # Create a response with the binary data
    response = make_response(photo_data)
    
    # Set the Content-Type header (assuming the photo is a JPEG; adjust if it's PNG or another format)
    response.headers.set('Content-Type', 'image/jpeg')
    
    return response