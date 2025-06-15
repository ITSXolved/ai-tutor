from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from utils.config import Config
from api.routes import api_bp
from services.vector_service import VectorService
from services.session_service import SessionService

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Enable CORS
    CORS(app)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize services
    with app.app_context():
        vector_service = VectorService()
        session_service = SessionService()
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"})
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)