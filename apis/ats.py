from flask import Blueprint, request, jsonify
import pdfplumber
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
print("Loaded DEEPSEEK_API_KEY:", DEEPSEEK_API_KEY)  # Debug print

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY not set in environment variables")

# Configure DeepSeek API client
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.novita.ai/v3/openai"  # DeepSeek's OpenAI-compatible endpoint
)

ats_bp = Blueprint('ats', __name__)

@ats_bp.route('/analyze-resume', methods=['POST'])
def analyze_resume():
    try:
        # Check if file and job description are in the request
        if 'file' not in request.files or 'job_description' not in request.form:
            return jsonify({"error": "Missing file or job description"}), 400

        file = request.files['file']
        job_description = request.form['job_description']

        # Validate file type
        if file.content_type != "application/pdf":
            return jsonify({"error": "Invalid file type. Please upload a PDF."}), 400

        # Extract text from PDF using pdfplumber
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        if not text.strip():
            return jsonify({"error": "No text could be extracted from the PDF."}), 400

        # Prepare prompt for DeepSeek API with strict JSON enforcement
        prompt = f"""
        Act as an experienced HR Manager with 20 years of experience in tech hiring. 
        Compare the resume provided below with the job description given below. 
        Evaluate the resume for ATS compatibility, focusing on:
        - Matching skills, keywords, and qualifications with the job description.
        - Formatting issues that might affect ATS parsing (e.g., complex layouts, missing standard headings).
        - Relevance of experience and education.
        
        Provide the response as a valid JSON string enclosed in curly braces, e.g., 
        {{"ATS Score":"85%","Missing Keywords":"AWS, Agile","Formatting Suggestions":"Use standard headings","Content Suggestions":"Add React projects"}}.
        Do not include any additional text, markdown, or explanations outside the JSON string.
        
        Here is the Resume text: {text}
        Here is the Job Description: {job_description}
        """

        # Call DeepSeek API
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1-turbo",
            messages=[
                {"role": "system", "content": "You are an expert HR manager evaluating resumes for ATS compatibility."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        # Extract the response text
        response_text = response.choices[0].message.content
        print("Raw DeepSeek API Response:", response_text)  # Debug print

        # Try parsing as JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            print("JSON Parse Error:", str(e))
            # Fallback: Extract JSON from response if it's wrapped in text or markdown
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    return jsonify({"error": "Invalid JSON structure in DeepSeek response", "raw_response": response_text}), 500
            else:
                return jsonify({"error": "No valid JSON found in DeepSeek response", "raw_response": response_text}), 500

        return jsonify(result)

    except Exception as e:
        print("Error in analyze_resume:", str(e))
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500