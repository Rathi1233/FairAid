import os
import sqlite3
import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
from dotenv import load_dotenv
import requests
import firebase_admin
from firebase_admin import credentials, firestore

from logic import analyze_data

load_dotenv()

# Firebase Init
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
if cred_path and os.path.exists(cred_path):
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        print(f"Firebase Init Error: {e}")
        db = None
else:
    db = None
    print("WARNING: Firebase credentials not found at FIREBASE_CREDENTIALS_PATH. Cloud saving disabled.")

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'fairaid_super_secret_key_12345'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database setup
def get_db_connection():
    conn = sqlite3.connect('fairaid.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ngo_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Auth Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user_id']
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(current_user, *args, **kwargs)
    return decorated


@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('ngo_name'):
        return jsonify({'message': 'Missing data'}), 400
    
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (ngo_name, email, password) VALUES (?, ?, ?)',
                     (data['ngo_name'], data['email'], hashed_password))
        conn.commit()
        return jsonify({'message': 'Registered successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Email already exists'}), 409
    finally:
        conn.close()


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Could not verify'}), 401

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (data['email'],)).fetchone()
    conn.close()

    if not user:
        return jsonify({'message': 'User not found'}), 401

    if check_password_hash(user['password'], data['password']):
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({
            'token': token,
            'ngo_name': user['ngo_name']
        })

    return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file and file.filename.endswith('.csv'):
        # Save file specifically for this user
        filename = f"user_{current_user}_data.csv"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'message': 'File uploaded successfully', 'has_data': True})
    
    return jsonify({'message': 'Invalid file format. Only CSV allowed.'}), 400


@app.route('/api/analyze', methods=['POST'])
@token_required
def analyze(current_user):
    data = request.get_json() or {}
    threshold = float(data.get('threshold', 8.0))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"user_{current_user}_data.csv")
    
    if not os.path.exists(filepath):
        return jsonify({'message': 'No data uploaded yet. Please upload a CSV.'}), 404
        
    try:
        df = pd.read_csv(filepath)
        results = analyze_data(df, threshold)
        
        # Save to Firebase if enabled
        if db:
            user_doc = db.collection('users').document(str(current_user))
            
            # Save results
            user_doc.collection('results').add({
                'satisfaction_rate': results['satisfaction_rate'],
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
            # Save records (ID, NeedScore, ReceivedHelp)
            # logic.py adds NeedScore and HelpNumeric. 
            records_ref = user_doc.collection('uploads').document('records')
            records_data = df[['ID', 'NeedScore', 'ReceivedHelp']].to_dict(orient='records')
            records_ref.set({'data': records_data})
            
            results['firebase_synced'] = True
        else:
            results['firebase_synced'] = False
            
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Error analyzing data: {str(e)}'}), 500


@app.route('/api/status', methods=['GET'])
@token_required
def status(current_user):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"user_{current_user}_data.csv")
    has_data = os.path.exists(filepath)
    return jsonify({'has_data': has_data})

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter_api(prompt):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY not found in environment.")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistralai/mistral-7b-instruct-v0.1",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        raise Exception(f"OpenRouter API Error: {str(e)}")

@app.route('/api/insights', methods=['POST'])
@token_required
def generate_insights(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Missing data'}), 400
        
    prompt = f"""The NGO data shows:
- Need Satisfaction Rate: {data.get('satisfaction')}
- High-Need Individuals: {data.get('high_need_count')}
- Not Served: {data.get('unfair_count')}

Explain what this means in simple terms."""

    try:
        insight = call_openrouter_api(prompt)
        return jsonify({'insight': insight})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/recommendations', methods=['POST'])
@token_required
def generate_recommendations(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Missing data'}), 400
        
    prompt = f"""Based on this NGO data:
- Need Satisfaction Rate: {data.get('satisfaction')}
- High-Need Individuals: {data.get('high_need_count')}
- Not Served: {data.get('unfair_count')}

Give 3 to 5 practical recommendations to improve fairness in aid distribution."""

    try:
        insight = call_openrouter_api(prompt)
        return jsonify({'insight': insight})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
