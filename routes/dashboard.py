from flask import Blueprint, render_template
from sqlalchemy import func, text
from models import db
from models.supply import SupplyRequisition
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

    recent_items = db.session.execute(text("""
        SELECT
            COALESCE(sr.requisition_item, sr.item_name)   AS display_name,
            STRING_AGG(DISTINCT sr.item_number, ', ')      AS item_numbers,
            COUNT(*)                                       AS total_quantity,
            MAX(sr.unit_of_measure)                        AS unit_of_measure,
            MAX(u.username)                                AS verified_by,
            MAX(sr.last_verified_at)                       AS last_verified_at,
            MAX(sr.item_image)                             AS item_image
        FROM supply_requisitions sr
        LEFT JOIN users u ON sr.last_verified_by = u.id
        WHERE sr.verified = TRUE
        GROUP BY COALESCE(sr.requisition_item, sr.item_name)
        ORDER BY MAX(sr.last_verified_at) DESC
        LIMIT 10
    """)).fetchall()

    return render_template(
        'dashboard/index.html',
        total=total,
        verified_count=verified_count,
        unverified_count=unverified_count,
        recent_items=recent_items,
    )
