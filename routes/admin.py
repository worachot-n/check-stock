from flask import Blueprint, render_template, redirect, url_for, flash, request
from models import db
from models.user import User
from decorators import login_required, admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    pending = User.query.filter_by(is_approved=False).order_by(User.created_at.asc()).all()
    approved = User.query.filter_by(is_approved=True).order_by(User.created_at.desc()).all()
    return render_template('admin/dashboard.html', pending=pending, approved=approved)


@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f'อนุมัติผู้ใช้ {user.username} แล้ว', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/reject/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'ปฏิเสธและลบผู้ใช้ {user.username} แล้ว', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/set-role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def set_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get('role', 'user')
    if role in ('admin', 'user'):
        user.role = role
        db.session.commit()
        flash(f'เปลี่ยนสิทธิ์ {user.username} เป็น {role} แล้ว', 'success')
    return redirect(url_for('admin.users'))
