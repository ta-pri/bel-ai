from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
 
db = SQLAlchemy()
 
def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.secret_key = 'bookstore-secret-key-2024'
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "bookstore.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    db.init_app(app)
    
    from .routes import main
    app.register_blueprint(main)
    
    with app.app_context():
        db.create_all()
        from .models import User
        from werkzeug.security import generate_password_hash
        if not User.query.filter_by(login='admin').first():
            admin = User(login='admin', password=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
    
    return app