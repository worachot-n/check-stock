from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db
from models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'danger')
            return render_template('auth/login.html')

        if not user.is_approved:
            flash('บัญชีของคุณยังไม่ได้รับการอนุมัติจากผู้ดูแลระบบ', 'warning')
            return render_template('auth/login.html')

        login_user(user)
        flash(f'ยินดีต้อนรับ, {user.username}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard.index'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()

        if not username or not password:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('รหัสผ่านไม่ตรงกัน', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('ชื่อผู้ใช้นี้ถูกใช้งานแล้ว', 'danger')
            return render_template('auth/register.html')

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            phone=phone,
            is_approved=False
        )
        db.session.add(user)
        db.session.commit()

        flash('สมัครสมาชิกสำเร็จ! กรุณารอการอนุมัติจากผู้ดูแลระบบ', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if new_password != confirm_password:
            flash('รหัสผ่านไม่ตรงกัน', 'danger')
            return render_template('auth/reset_password.html')

        user = User.query.filter_by(username=username).first()
        if not user:
            flash('ไม่พบผู้ใช้งานนี้ในระบบ', 'danger')
            return render_template('auth/reset_password.html')

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('รีเซ็ตรหัสผ่านสำเร็จ', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('ออกจากระบบแล้ว', 'info')
    return redirect(url_for('auth.login'))
