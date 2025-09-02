# app.py
from flask import Flask, render_template, request, jsonify, url_for
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import requests
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from datetime import timedelta

load_dotenv()

app = Flask(__name__)
CORS(app)

# Config
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-change-me')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
jwt = JWTManager(app)

INTASEND_SECRET_KEY = os.getenv('INTASEND_SECRET_KEY')  # Set this in .env (use sandbox key first)

# Database connection helper
def create_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'edugenie_db')
        )
        # print("MySQL Database connection successful")
        return connection
    except Error as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate')
def generate():
    return render_template('generate.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"error": "All fields are required"}), 400

    connection = create_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({"error": "Email already registered"}), 400

        hashed = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password, is_premium) VALUES (%s, %s, %s, %s)",
            (name, email, hashed, False)
        )
        connection.commit()
        user_id = cursor.lastrowid
        cursor.close()
        connection.close()

        # create JWT token for convenience (optional)
        access_token = create_access_token(identity=user_id)
        return jsonify({
            "message": "User created successfully",
            "user_id": user_id,
            "access_token": access_token
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    email = data.get('email')
    password = data.get('password')
    if not all([email, password]):
        return jsonify({"error": "All fields are required"}), 400

    connection = create_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, password, name, is_premium FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if not user or not check_password_hash(user['password'], password):
            return jsonify({"error": "Invalid email or password"}), 401

        access_token = create_access_token(identity=user['id'])
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {"id": user['id'], "name": user['name'], "is_premium": bool(user['is_premium'])}
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-flashcards', methods=['POST'])
def generate_flashcards():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    text = data.get('text', '')
    if not text:
        return jsonify({"error": "No text provided"}), 400

    flashcards = generate_questions_from_text(text)
    return jsonify({"flashcards": flashcards})

def generate_questions_from_text(text):
    sentences = text.split('.')
    questions = []
    for i, sentence in enumerate(sentences):
        if len(sentence.strip()) > 10 and i < 5:
            question = f"What is the main idea of: '{sentence.strip()}'?"
            answer = f"This sentence discusses: {sentence.strip()}"
            questions.append({"question": question, "answer": answer})
    if len(questions) < 3:
        questions.extend([
            {"question": "What is the capital of France?", "answer": "Paris"},
            {"question": "What is 2 + 2?", "answer": "4"},
            {"question": "What is the largest planet in our solar system?", "answer": "Jupiter"}
        ])
    return questions

# Save flashcards - protected route
@app.route('/api/save-flashcards', methods=['POST'])
@jwt_required()
def save_flashcards():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    flashcards = data.get('flashcards', [])

    connection = create_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor()
        for card in flashcards:
            cursor.execute(
                "INSERT INTO flashcards (user_id, question, answer) VALUES (%s, %s, %s)",
                (user_id, card['question'], card['answer'])
            )
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Flashcards saved successfully", "saved_count": len(flashcards)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create an IntaSend payment link (checkout / paymentlinks)
@app.route('/api/create-paymentlink', methods=['POST'])
@jwt_required()
def create_paymentlink():
    """
    Request body example:
    {
        "amount": 2000,
        "currency": "KES",
        "title": "Flipwise Pro - 1 month",
        "description": "Monthly subscription"
    }
    """
    data = request.get_json() or {}
    amount = data.get('amount')
    currency = data.get('currency', 'KES')
    title = data.get('title', 'Flipwise Pro')
    description = data.get('description', '')
    user_id = get_jwt_identity()

    if not INTASEND_SECRET_KEY:
        return jsonify({"error": "Payment gateway not configured on server"}), 500
    if not amount:
        return jsonify({"error": "Amount is required"}), 400

    # Build payload for IntaSend paymentlinks (fields can be tuned; check IntaSend docs)
    payload = {
        "title": title,
        "amount": amount,
        "currency": currency,
        "description": description,
        # redirect_url: where IntaSend should send customer after success (optional)
        "redirect_url": url_for('index', _external=True),
        "metadata": {
            "user_id": user_id
        }
    }

    headers = {
        "Authorization": f"Bearer {INTASEND_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post("https://api.intasend.com/api/v1/paymentlinks/", json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        resp = r.json()
        # The response will include a URL to redirect the user to
        # Example fields depend on IntaSend response; adjust to the actual response fields
        return jsonify({"success": True, "intasend_response": resp})
    except requests.RequestException as e:
        return jsonify({"error": "Failed to create payment link", "details": str(e)}), 500

# IntaSend webhook endpoint to be configured in the IntaSend dashboard
@app.route('/webhook/intasend', methods=['POST'])
def intasend_webhook():
    # IMPORTANT: verify the webhook signature as per IntaSend docs in production
    event = request.get_json() or {}
    # Example processing: mark user premium when invoice is paid
    # The actual event structure depends on IntaSend; inspect and adapt.
    try:
        invoice = event.get('data', {})
        status = invoice.get('status') or event.get('status')
        metadata = invoice.get('metadata') or {}
        user_id = metadata.get('user_id')
        invoice_id = invoice.get('id') or invoice.get('invoice_id')

        if status == 'paid' and user_id:
            connection = create_db_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("UPDATE users SET is_premium = %s WHERE id = %s", (True, user_id))
                connection.commit()
                cursor.close()
                connection.close()
        # respond quickly
        return jsonify({"received": True})
    except Exception as e:
        print("Webhook handling error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create DB tables if needed
    connection = create_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                password VARCHAR(255),
                is_premium BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                question TEXT,
                answer TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        cursor.close()
        connection.close()

    app.run(debug=True, port=5000)
