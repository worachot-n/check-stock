from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

from config import Config
from models import db
from models.user import User
from models.log import ActivityLog
from sqlalchemy import text


def _fix_sequence():
    """Reset supply_requisitions PK sequence to max existing value."""
    db.session.execute(text("""
        SELECT setval(
            pg_get_serial_sequence('supply_requisitions', 'sequence_no'),
            COALESCE(MAX(sequence_no), 0)
        )
        FROM supply_requisitions
    """))
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'กรุณาเข้าสู่ระบบก่อน'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.scanner import scanner_bp
    from routes.dashboard import dashboard_bp
    from routes.labels import labels_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(labels_bp)

    with app.app_context():
        db.create_all()
        _fix_sequence()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
