from flask import Blueprint, render_template
from sqlalchemy import func, text
from models import db
from models.supply import SupplyRequisition
from models.user import User
from decorators import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    total = db.session.query(func.count(SupplyRequisition.sequence_no)).scalar()
    verified_count = db.session.query(func.count(SupplyRequisition.sequence_no)).filter(
        SupplyRequisition.verified == True
    ).scalar()
    unverified_count = total - verified_count

    recent_items = (
        db.session.query(SupplyRequisition, User.username)
        .outerjoin(User, SupplyRequisition.last_verified_by == User.id)
        .filter(SupplyRequisition.verified == True)
        .order_by(SupplyRequisition.last_verified_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        'dashboard/index.html',
        total=total,
        verified_count=verified_count,
        unverified_count=unverified_count,
        recent_items=recent_items,
    )
