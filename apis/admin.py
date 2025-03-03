# apis/admin.py
from flask import Blueprint, request, jsonify
from database import db
from bcrypt import hashpw, gensalt, checkpw
from flask_jwt_extended import create_access_token, jwt_required
import fitz
import logging
import datetime

admin_bp = Blueprint('admin', __name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'.encode('utf-8')
hashed_admin_pass = hashpw(ADMIN_PASSWORD, gensalt())

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password').encode('utf-8')

    if username == ADMIN_USERNAME and checkpw(password, hashed_admin_pass):
        access_token = create_access_token(identity=username, additional_claims={'role': 'admin'})
        return jsonify({'message': 'Admin logged in', 'token': access_token}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def admin_dashboard():
    tests_taken = db.assessments.count_documents({})
    total_students = db.students.count_documents({})
    active_students = len(db.assessments.distinct('username'))
    total_assessments = db.admin_assessments.count_documents({})

    test_counts = db.assessments.aggregate([
        {'$group': {'_id': '$assessment_id', 'count': {'$sum': 1}}},
        {'$project': {'test_name': '$_id', 'tests': '$count', '_id': 0}}
    ])
    tests_per_assessment = list(test_counts)

    student_activity = db.assessments.aggregate([
        {'$group': {'_id': '$username', 'count': {'$sum': 1}}},
        {'$project': {'username': '$_id', 'tests': '$count', '_id': 0}}
    ])
    student_activity_data = list(student_activity)

    return jsonify({
        'tests_taken': tests_taken,
        'total_students': total_students,
        'active_students': active_students,
        'total_assessments': total_assessments,
        'tests_per_assessment': tests_per_assessment,
        'student_activity': student_activity_data
    }), 200

@admin_bp.route('/upload-assessment', methods=['POST'])
@jwt_required()
def upload_assessment():
    if not request.content_type.startswith('multipart/form-data'):
        logger.error("Invalid Content-Type: %s", request.content_type)
        return jsonify({'message': 'Content-Type must be multipart/form-data'}), 400

    title = request.form.get('title')
    pdf_file = request.files.get('pdf_file')

    if not title or not pdf_file:
        logger.error("Missing title or PDF file: title=%s, pdf_file=%s", title, pdf_file)
        return jsonify({'message': 'Title and PDF file are required'}), 400

    if not pdf_file.filename.endswith('.pdf'):
        logger.error("Invalid file type: %s", pdf_file.filename)
        return jsonify({'message': 'File must be a PDF'}), 400

    try:
        pdf_stream = pdf_file.read()
        logger.debug("PDF file size: %d bytes", len(pdf_stream))

        pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
        extracted_text = ""
        for page_num, page in enumerate(pdf_document, start=1):
            text = page.get_text("text")
            extracted_text += f"--- Page {page_num} ---\n{text}\n"
            logger.debug("Extracted text from page %d: %s", page_num, text[:100])

        if not extracted_text.strip():
            logger.warning("No text extracted from PDF")
            return jsonify({'message': 'No readable text found in PDF'}), 400

        questions = []
        lines = extracted_text.split('\n')
        current_question = None
        options = []
        correct_answer = None

        for line in lines:
            line = line.strip()
            if line and line.startswith('--- Page'):
                continue
            if line and line[0].isdigit() and '.' in line[:3]:
                if current_question:
                    questions.append({
                        'question': current_question,
                        'options': options,
                        'correct_answer': correct_answer
                    })
                current_question = line
                options = []
                correct_answer = None
            elif line and line[0] in 'abcd':
                if '#' in line:
                    option_text = line.replace('#', '').strip()
                    options.append(option_text)
                    correct_answer = option_text
                else:
                    options.append(line.strip())

        if current_question:
            questions.append({
                'question': current_question,
                'options': options,
                'correct_answer': correct_answer
            })

        if not questions:
            logger.warning("No questions parsed from text: %s", extracted_text[:500])
            return jsonify({'message': 'No questions could be parsed from PDF'}), 400

        assessment = {
            'title': title,
            'questions': questions
        }
        result = db.admin_assessments.insert_one(assessment)
        logger.info("Assessment saved: %s with %d questions", title, len(questions))

        return jsonify({
            'message': 'Assessment uploaded and questions extracted',
            'assessment_id': str(result.inserted_id),
            'title': title,
            'question_count': len(questions)
        }), 201

    except Exception as e:
        logger.error("Error processing PDF: %s", str(e))
        return jsonify({'message': f'Error processing PDF: {str(e)}'}), 500

@admin_bp.route('/assessments', methods=['GET'])
@jwt_required()
def get_assessments():
    assessments = list(db.admin_assessments.find({}, {'_id': 0}))
    return jsonify({'assessments': assessments}), 200

@admin_bp.route('/upload-course', methods=['POST'])
@jwt_required()
def upload_course():
    if not request.content_type.startswith('multipart/form-data'):
        logger.error("Invalid Content-Type: %s", request.content_type)
        return jsonify({'message': 'Content-Type must be multipart/form-data'}), 400

    module_name = request.form.get('module_name')
    course_title = request.form.get('course_title')
    course_link = request.form.get('course_link', None)
    pdf_file = request.files.get('course_material', None)

    if not module_name or not course_title:
        logger.error("Missing module_name or course_title: module_name=%s, course_title=%s", module_name, course_title)
        return jsonify({'message': 'Module Name and Course Title are required'}), 400

    course_content = None
    if pdf_file and pdf_file.filename.endswith('.pdf'):
        try:
            pdf_stream = pdf_file.read()
            logger.debug("Course PDF file size: %d bytes", len(pdf_stream))

            pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
            extracted_text = ""
            for page_num, page in enumerate(pdf_document, start=1):
                text = page.get_text("text")
                extracted_text += f"--- Page {page_num} ---\n{text}\n"
                logger.debug("Extracted text from page %d: %s", page_num, text[:100])

            if extracted_text.strip():
                course_content = extracted_text
            else:
                logger.warning("No text extracted from course PDF")
        except Exception as e:
            logger.error("Error processing course PDF: %s", str(e))
            return jsonify({'message': f'Error processing course PDF: {str(e)}'}), 500

    course = {
        'module_name': module_name,
        'course_title': course_title,
        'course_link': course_link,
        'course_content': course_content,
        'completed_by': []
    }
    result = db.courses.insert_one(course)
    logger.info("Course saved: %s", course_title)

    return jsonify({
        'message': 'Course uploaded successfully',
        'course_id': str(result.inserted_id),
        'course_title': course_title
    }), 201

@admin_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_courses():
    courses = list(db.courses.find({}, {'_id': 0}))
    return jsonify({'courses': courses}), 200

@admin_bp.route('/schedule-session', methods=['POST'])
@jwt_required()
def schedule_session():
    data = request.get_json()
    session_title = data.get('sessionTitle')  # Updated to match frontend
    session_date = data.get('session_date')  # Expected format: "dd-mm-yyyy"
    session_type = data.get('sessionType')    # Updated to match frontend

    if not all([session_title, session_date, session_type]):
        logger.error("Missing required fields: title=%s, date=%s, type=%s", session_title, session_date, session_type)
        return jsonify({'message': 'Session Title, Date, and Type are required'}), 400

    try:
        day, month, year = map(int, session_date.split('-'))
        if not (1 <= day <= 31 and 1 <= month <= 12 and year >= 2023):
            raise ValueError
    except ValueError:
        logger.error("Invalid date format: %s", session_date)
        return jsonify({'message': 'Date must be in dd-mm-yyyy format and valid'}), 400

    session = {
        'session_title': session_title,
        'session_date': session_date,
        'session_type': session_type,
        'created_at': datetime.datetime.now().isoformat()
    }
    result = db.sessions.insert_one(session)
    logger.info("Session scheduled: %s", session_title)

    return jsonify({
        'message': 'Session scheduled successfully',
        'session_id': str(result.inserted_id),
        'session_title': session_title
    }), 201

@admin_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    sessions = list(db.sessions.find({}, {'_id': 0}))
    return jsonify({'sessions': sessions}), 200