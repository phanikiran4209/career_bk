from flask import Flask
from config import Config
from database import db
from apis.auth import auth_bp
from apis.profile import profile_bp
from apis.dashboard import dashboard_bp
from apis.assessment import assessment_bp
from apis.admin import admin_bp
from apis.prediction import prediction_bp
from apis.interview import interview_bp
from apis.ats import ats_bp  # Import the new ATS blueprint
from flask_jwt_extended import JWTManager
from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
jwt = JWTManager(app)

# Register all blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(profile_bp, url_prefix='/profile')
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(assessment_bp, url_prefix='/assessment')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(prediction_bp, url_prefix='/prediction')
app.register_blueprint(interview_bp, url_prefix='/interview')
app.register_blueprint(ats_bp, url_prefix='/ats')  # Register the ATS blueprint

if __name__ == '__main__':
    app.run(debug=True)