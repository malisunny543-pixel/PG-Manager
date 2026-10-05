from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.services import authenticate_user, register_tenant

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user' in session:
        role = session['user'].get('role')
        if role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
        elif role == 'MANAGER':
            return redirect(url_for('manager.dashboard'))
        elif role == 'TENANT':
            return redirect(url_for('tenant.dashboard'))
    return render_template('public/index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')

        user = authenticate_user(email, password)
        if user:
            session.clear()
            session['user'] = user
            flash(f"Welcome back, {user['first_name']}!", "success")
            
            # Redirect by role
            role = user['role']
            if role == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
            elif role == 'MANAGER':
                return redirect(url_for('manager.dashboard'))
            elif role == 'TENANT':
                return redirect(url_for('tenant.dashboard'))
            return redirect(url_for('auth.index'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        phone = request.form.get('phone', '')
        emergency_name = request.form.get('emergency_name', '')
        emergency_phone = request.form.get('emergency_phone', '')
        id_proof_type = request.form.get('id_proof_type', 'Aadhaar')
        id_proof_number = request.form.get('id_proof_number', '')
        permanent_address = request.form.get('permanent_address', '')

        try:
            register_tenant(
                email=email, password=password, first_name=first_name, last_name=last_name,
                phone=phone, emergency_name=emergency_name, emergency_phone=emergency_phone,
                id_proof_type=id_proof_type, id_proof_number=id_proof_number,
                permanent_address=permanent_address
            )
            flash("Registration successful! You may now sign in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(str(e), "danger")

    return render_template('auth/register.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for('auth.login'))
