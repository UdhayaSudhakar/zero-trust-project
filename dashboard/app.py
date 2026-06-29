from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, User, SessionLog
import pickle
import numpy as np
import requests
from user_agents import parse
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'zerotrust2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zerotrust.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with open('../models/model.pkl', 'rb') as f:
    model = pickle.load(f)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_location(ip):
    try:
        response = requests.get(f'http://ipapi.co/{ip}/json/', timeout=3)
        data = response.json()
        return {
            'city': data.get('city', 'Unknown'),
            'region': data.get('region', 'Unknown'),
            'country': data.get('country_name', 'Unknown'),
        }
    except:
        return {'city': 'Unknown', 'region': 'Unknown', 'country': 'Unknown'}

def get_device(ua_string):
    ua = parse(ua_string)
    return {
        'browser': ua.browser.family,
        'os': ua.os.family,
        'device': 'Mobile' if ua.is_mobile else 'Tablet' if ua.is_tablet else 'Desktop'
    }

def calculate_risk(ip_changes, failed_attempts, new_device, odd_hours, data_mb, login_freq):
    features = np.array([[login_freq, 30, ip_changes, 10, failed_attempts, new_device, odd_hours, data_mb]])
    prediction = model.predict(features)[0]
    if prediction == 'High':
        return 'High', 20, 'TERMINATE SESSION', 'red'
    elif prediction == 'Medium':
        return 'Medium', 50, 'MONITOR CLOSELY', 'orange'
    else:
        return 'Low', 85, 'ACCESS GRANTED', 'green'

@app.route('/')
@login_required
def home():
    sessions = SessionLog.query.filter_by(
        user_id=current_user.id
    ).order_by(SessionLog.login_time.desc()).limit(10).all()
    return render_template('index.html', user=current_user, sessions=sessions)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username already exists!')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            ip = request.remote_addr
            ua_string = request.headers.get('User-Agent')
            location = get_location(ip)
            device = get_device(ua_string)
            hour = datetime.now().hour
            odd_hours = 1 if hour < 6 or hour > 22 else 0
            risk, trust, action, color = calculate_risk(0, 0, 0, odd_hours, 50, 1)
            session_log = SessionLog(
                user_id=user.id,
                username=user.username,
                ip_address=ip,
                device=device['device'],
                browser=device['browser'],
                os=device['os'],
                city=location['city'],
                country=location['country'],
                risk_level=risk,
                trust_score=trust,
                action=action
            )
            db.session.add(session_log)
            db.session.commit()
            return redirect(url_for('home'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    SessionLog.query.filter_by(
        user_id=current_user.id, is_active=True
    ).update({'is_active': False})
    db.session.commit()
    logout_user()
    return redirect(url_for('login'))

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    data = request.json
    features = np.array([[
        data['login_frequency'],
        data['session_duration'],
        data['ip_changes'],
        data['pages_visited'],
        data['failed_attempts'],
        data['new_device'],
        data['odd_hours'],
        data['data_accessed_mb']
    ]])
    prediction = model.predict(features)[0]
    if prediction == 'High':
        trust_score = 20
        action = 'TERMINATE SESSION'
        color = 'red'
    elif prediction == 'Medium':
        trust_score = 50
        action = 'MONITOR CLOSELY'
        color = 'orange'
    else:
        trust_score = 85
        action = 'ACCESS GRANTED'
        color = 'green'
    return jsonify({
        'risk_level': prediction,
        'trust_score': trust_score,
        'action': action,
        'color': color
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)