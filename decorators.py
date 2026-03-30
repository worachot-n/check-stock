from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_approved:
            flash('บัญชีของคุณยังไม่ได้รับการอนุมัติ', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function
