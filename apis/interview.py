from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db
from config import Config
from openai import OpenAI
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

interview_bp = Blueprint('interview', __name__)

base_url = "https://api.novita.ai/v3/openai"
api_key = "sk_iTKUcyR1a6wno7ZIKrIu_i6Sn51WFHVhdWpGTMduC4k"  # Replace with your actual API key
model = "deepseek/deepseek-r1-turbo"

client = OpenAI(base_url=base_url, api_key=api_key)

@interview_bp.route('/generate-questions', methods=['POST'])
@jwt_required()
def generate_interview_questions():
    user_id = get_jwt_identity()
    logger.debug(f"User ID from JWT: {user_id}")

    data = request.get_json()
    job_role = data.get('job_role')
    job_description = data.get('job_description')
    years_of_experience = data.get('years_of_experience')
    hardness = data.get('hardness')

    if not all([job_role, job_description, years_of_experience, hardness]):
        logger.error("Missing required fields in request")
        return jsonify({"error": "Missing required fields"}), 400

    if hardness not in ["easy", "medium", "hard", "expert"]:
        return jsonify({"error": "Hardness must be easy, medium, hard, or expert"}), 400

    prompt = f"""
    Generate 5 interview questions and their answers for a {job_role} role.
    The candidate has {years_of_experience} years of experience, and the interview difficulty should be {hardness}.
    The job description is: {job_description}.
    Return the response as a valid JSON array containing dictionaries with 'question' and 'answer' keys.
    Example: [{{"question": "What is a REST API?", "answer": "A REST API is an architectural style for designing networked applications."}}]
    """

    try:
        logger.debug(f"Sending request to DeepSeek API with prompt: {prompt}")
        chat_completion_res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert in generating interview questions and answers."},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=500,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        generated_text = chat_completion_res.choices[0].message.content
        logger.debug(f"DeepSeek API raw response: {generated_text}")

        try:
            # Attempt to parse the response as JSON
            questions_and_answers = json.loads(generated_text)
            if not isinstance(questions_and_answers, list) or not all(isinstance(qa, dict) and 'question' in qa and 'answer' in qa for qa in questions_and_answers):
                raise ValueError("Invalid JSON format")
        except json.JSONDecodeError:
            logger.warning("Response is not JSON, attempting to parse as plain text")
            questions_and_answers = parse_plain_text_to_json(generated_text)
            if not questions_and_answers:
                return jsonify({"error": "Failed to parse DeepSeek API response"}), 500

        interview_data = {
            "user_id": user_id,
            "job_role": job_role,
            "job_description": job_description,
            "years_of_experience": years_of_experience,
            "hardness": hardness,
            "questions": questions_and_answers,
            "created_at": datetime.utcnow(),
            "status": "pending"
        }
        result = db.interviews.insert_one(interview_data)
        logger.debug(f"Inserted interview into MongoDB with ID: {result.inserted_id}")

        return jsonify({
            "message": "Interview questions generated successfully",
            "interview_id": str(result.inserted_id),
            "questions": questions_and_answers
        }), 200

    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        return jsonify({"error": f"Error generating questions: {str(e)}"}), 500

@interview_bp.route('/evaluate-response', methods=['POST'])
@jwt_required()
def evaluate_response():
    user_id = get_jwt_identity()
    logger.debug(f"User ID from JWT: {user_id}")

    data = request.get_json()
    logger.debug(f"Received data: {data}")

    question = data.get('question')
    response = data.get('response')
    job_role = data.get('job_role')
    years_of_experience = data.get('years_of_experience')
    hardness = data.get('hardness')

    if not all([question, response, job_role, years_of_experience, hardness]):
        logger.error("Missing required fields in request")
        return jsonify({"error": "Missing required fields"}), 400

    prompt = f"""
    Evaluate the following response to the interview question for a {job_role} role.
    The candidate has {years_of_experience} years of experience, and the interview difficulty is {hardness}.
    Question: {question}
    Response: {response}
    Provide detailed feedback on the response, including relevance, depth, and clarity. Also, provide a rating out of 10.
    Return the response as a valid JSON object with 'feedback' and 'rating' keys.
    Example: {{"feedback": "The response is relevant but lacks depth. Consider providing more specific examples.", "rating": 6}}
    """

    try:
        logger.debug(f"Sending request to DeepSeek API with prompt: {prompt}")
        chat_completion_res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert in evaluating interview responses."},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=500,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        generated_text = chat_completion_res.choices[0].message.content
        logger.debug(f"DeepSeek API raw response: {generated_text}")

        try:
            evaluation = json.loads(generated_text)
            if not isinstance(evaluation, dict) or 'feedback' not in evaluation or 'rating' not in evaluation:
                raise ValueError("Invalid JSON format")
        except json.JSONDecodeError:
            logger.warning("Response is not JSON, attempting to parse as plain text")
            evaluation = parse_plain_text_to_json(generated_text)
            if not evaluation:
                return jsonify({"error": "Failed to parse DeepSeek API response"}), 500

        return jsonify({
            "message": "Response evaluated successfully",
            "evaluation": evaluation
        }), 200

    except Exception as e:
        logger.error(f"Error evaluating response: {str(e)}")
        return jsonify({"error": f"Error evaluating response: {str(e)}"}), 500

def parse_plain_text_to_json(text):
    try:
        lines = text.strip().split('\n')
        questions_and_answers = []
        current_question = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.endswith('?'):
                if current_question is not None and current_question["answer"]:
                    questions_and_answers.append(current_question)
                current_question = {"question": line, "answer": ""}
            elif current_question is not None:
                current_question["answer"] += line + " "
        if current_question is not None and current_question["answer"]:
            questions_and_answers.append(current_question)
        logger.debug(f"Parsed questions and answers: {questions_and_answers}")
        return questions_and_answers
    except Exception as e:
        logger.error(f"Failed to parse plain text to JSON: {str(e)}")
        return None