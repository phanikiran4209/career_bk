from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import pickle
import numpy as np
import pandas as pd
from pymongo import MongoClient
import os
from config import Config
from datetime import datetime

# Define Blueprint
prediction_bp = Blueprint('prediction', __name__)

# Load the trained model
model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'best_model.pkl')
with open(model_path, 'rb') as file:
    model = pickle.load(file)

# Load label encoders
encoders_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'label_encoders.pkl')
with open(encoders_path, 'rb') as file:
    encoders = pickle.load(file)

# Define expected feature columns (excluding target variable)
feature_columns = ['Gender', 'Age', 'GPA', 'Major', 'Interested Domain', 
                   'Projects', 'Python', 'SQL', 'Java']

# Helper function to preprocess input data
def preprocess_input(data):
    df = pd.DataFrame([data])

    # Map categorical values to numerical
    gender_map = {'Male': 0, 'Female': 1}
    skill_map = {'Weak': 0, 'Average': 1, 'Strong': 2}

    df['Gender'] = df['Gender'].map(gender_map).fillna(-1)  # Handle unknown gender
    df['Python'] = df['Python'].map(skill_map).fillna(0)  # Default skills to 0
    df['SQL'] = df['SQL'].map(skill_map).fillna(0)
    df['Java'] = df['Java'].map(skill_map).fillna(0)

    # One-hot encode categorical features
    df_encoded = pd.get_dummies(df, columns=['Major', 'Interested Domain', 'Projects'])

    # Ensure all expected columns are present (fill missing with 0)
    expected_columns = model.feature_names_in_ if hasattr(model, 'feature_names_in_') else feature_columns
    for col in expected_columns:
        if col not in df_encoded.columns:
            df_encoded[col] = 0

    # Reorder columns to match model training data
    df_encoded = df_encoded[expected_columns]

    return df_encoded.values.astype(float)  # Convert to float

# MongoDB connection
mongo_client = MongoClient(Config.MONGO_URI)
db = mongo_client[Config.MONGO_DB_NAME]
predictions_collection = db.predictions

@prediction_bp.route('/predict_career', methods=['POST'])
@jwt_required()  # Require JWT token for authentication
def predict_career():
    try:
        # Get the current user's identity from the JWT token
        current_user = get_jwt_identity()

        # Extract user ID safely
        user_id = None
        if isinstance(current_user, dict) and 'id' in current_user:
            user_id = current_user['id']
        elif isinstance(current_user, str):
            user_id = current_user  # If the identity is a string (e.g., user ID)
        else:
            return jsonify({
                'error': 'Invalid user identity in JWT token',
                'status': 'error'
            }), 401

        # Get JSON data from request
        data = request.get_json()

        # Validate required fields
        required_fields = ['Gender', 'Age', 'GPA', 'Major', 'Interested Domain', 
                           'Projects', 'Python', 'SQL', 'Java']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {missing_fields}'}), 400

        # Preprocess the input data
        processed_input = preprocess_input(data)

        # Make prediction
        prediction = model.predict(processed_input)

        # Decode prediction label
        target_column = "Future Career"  # Adjust if needed
        prediction_label = encoders[target_column].inverse_transform([int(prediction[0])])[0]

        # Store prediction in MongoDB
        prediction_data = {
            'user_id': user_id,
            'input_data': data,
            'prediction': prediction_label,
            'timestamp': datetime.utcnow()  # Use datetime for JSON serialization
        }
        prediction_id = predictions_collection.insert_one(prediction_data).inserted_id

        # Return prediction response
        return jsonify({
            'prediction': prediction_label,
            'status': 'success',
            'user_id': user_id
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
