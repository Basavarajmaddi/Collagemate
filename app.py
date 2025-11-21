from flask import Flask, request, jsonify, render_template, send_file, redirect, make_response, url_for, session, flash
from flask_cors import CORS
import openai
import sqlite3
from datetime import datetime, timedelta
import os
import tempfile
import re
import asyncio
import edge_tts
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import json
import random
from functools import wraps
import hashlib
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Voice Configuration
VOICE = "en-IN-NeerjaNeural"  # An Indian female voice

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your-email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your-app-password")
COLLEGE_EMAIL = os.getenv("COLLEGE_EMAIL", "bmit@example.com")

# College information
COLLEGE_INFO = {
    'name': 'Brahmdevdada Mane Institute of Technology',
    'short_name': 'BMIT',
    'address': 'Solapur - Mangalwedha National Highway',
    'city': 'Belati, Solapur',
    'state': 'Maharashtra',
    'pincode': '413002',
    'phone': '+91 217 239 2303',
    'email': 'info@bmit.ac.in',
    'courses': [
        {
            'name': 'B.E. Computer Science & Engineering',
            'duration': 4,
            'seats': 60,
            'fees': '95,000',
            'degree': 'B.E.',
            'department': 'CSE',
            'description': 'Learn the fundamentals of computer science, programming, and software development. This program prepares you for a career in technology and innovation.',
            'image': 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97'
        },
        {
            'name': 'B.E. Civil Engineering',
            'duration': 4,
            'seats': 60,
            'fees': '90,000',
            'degree': 'B.E.',
            'department': 'Civil',
            'description': 'Study structural engineering, construction management, and sustainable development. Build the infrastructure of tomorrow.',
            'image': 'https://images.unsplash.com/photo-1581092160607-ee22621dd758'
        },
        {
            'name': 'B.E. Mechanical Engineering',
            'duration': 4,
            'seats': 60,
            'fees': '90,000',
            'degree': 'B.E.',
            'department': 'Mechanical',
            'description': 'Master the principles of mechanics, thermodynamics, and manufacturing processes. Design and build mechanical systems.',
            'image': 'https://images.unsplash.com/photo-1537462715879-360eeb61a0ad'
        }
    ],
    'departments': [
        'Computer Science & Engineering',
        'Civil Engineering',
        'Mechanical Engineering'
    ],
    'facilities': [
        {
            'name': 'Computer Labs',
            'icon': 'fas fa-desktop',
            'description': 'State-of-the-art computer laboratories equipped with the latest hardware and software for hands-on learning and practical experience.',
            'image': 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97',
            'features': [
                'High-performance computers',
                'Latest software tools',
                'Internet connectivity',
                'Technical support'
            ]
        },
        {
            'name': 'Library',
            'icon': 'fas fa-book',
            'description': 'A comprehensive library with extensive collection of books, journals, and digital resources to support academic research and learning.',
            'image': 'https://images.unsplash.com/photo-1521587760476-6c12a4b040da',
            'features': [
                'Digital catalog',
                'Study rooms',
                'Online journals',
                'Reference section'
            ]
        },
        {
            'name': 'Sports Complex',
            'icon': 'fas fa-futbol',
            'description': 'Modern sports facilities including indoor and outdoor courts, gymnasium, and equipment for various sports activities.',
            'image': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48',
            'features': [
                'Indoor courts',
                'Outdoor fields',
                'Fitness center',
                'Sports equipment'
            ]
        },
        {
            'name': 'Hostel',
            'icon': 'fas fa-home',
            'description': 'Comfortable and secure accommodation for students with modern amenities and a conducive environment for studies.',
            'image': 'https://images.unsplash.com/photo-1555854877-bab0e564b8d5',
            'features': [
                'Furnished rooms',
                'Mess facility',
                'Wi-Fi connectivity',
                '24/7 security'
            ]
        }
    ]
}

# Database Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'college.db')

# Admin Authentication
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin@123"  # Production password

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('username') != ADMIN_USERNAME:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/logout')
def admin_logout():
    # Clear all session variables
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

# Admin API Routes
@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get visitor count (unique phone numbers)
    cur.execute('''
        SELECT COUNT(DISTINCT phone_number) 
        FROM conversations 
        WHERE date(timestamp) = ?
    ''', (today,))
    visitors = cur.fetchone()[0]
    
    # Get active conversations (last 24 hours)
    cur.execute('''
        SELECT COUNT(DISTINCT phone_number) 
        FROM conversations 
        WHERE timestamp > datetime('now', '-1 day')
    ''')
    active_conversations = cur.fetchone()[0]
    
    # Get admission requests
    cur.execute('SELECT COUNT(*) FROM admissions WHERE date(application_date) = ?', (today,))
    admissions = cur.fetchone()[0]
    
    # Calculate response rate
    cur.execute('''
        SELECT COUNT(*) 
        FROM conversations 
        WHERE message_type = 'assistant' 
        AND date(timestamp) = ?
    ''', (today,))
    ai_responses = cur.fetchone()[0]
    
    cur.execute('''
        SELECT COUNT(*) 
        FROM conversations 
        WHERE message_type = 'user' 
        AND date(timestamp) = ?
    ''', (today,))
    user_messages = cur.fetchone()[0]
    
    response_rate = round((ai_responses / user_messages * 100) if user_messages > 0 else 0, 1)
    
    cur.close()
    conn.close()
    
    return jsonify({
        'visitors': visitors,
        'conversations': active_conversations,
        'admissions': admissions,
        'response_rate': response_rate
    })

@app.route('/api/admin/conversations')
@admin_required
def admin_conversations():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get recent conversations with context
    cur.execute('''
        SELECT c.*, s.student_name 
        FROM conversations c
        LEFT JOIN student_details s ON c.phone_number = s.phone_number
        ORDER BY c.timestamp DESC 
        LIMIT 50
    ''')
    
    conversations = []
    current_conversation = None
    
    for row in cur.fetchall():
        row = dict(row)
        if current_conversation is None or current_conversation['phone_number'] != row['phone_number']:
            if current_conversation:
                conversations.append(current_conversation)
            current_conversation = {
                'student_name': row['student_name'],
                'phone_number': row['phone_number'],
                'timestamp': row['timestamp'],
                'messages': []
            }
        
        current_conversation['messages'].append({
            'type': row['message_type'],
            'content': row['message_content']
        })
    
    if current_conversation:
        conversations.append(current_conversation)
    
    cur.close()
    conn.close()
    
    return jsonify(conversations)

@app.route('/api/admin/admissions')
@admin_required
def admin_admissions():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT a.*, s.email 
        FROM admissions a
        LEFT JOIN student_details s ON a.phone_number = s.phone_number
        ORDER BY a.application_date DESC
    ''')
    
    admissions = [dict(row) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return jsonify(admissions)

@app.route('/api/admin/admissions/<int:admission_id>', methods=['DELETE'])
@admin_required
def delete_admission(admission_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('DELETE FROM admissions WHERE id = ?', (admission_id,))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error deleting admission: {str(e)}")
        conn.rollback()
        success = False
    
    cur.close()
    conn.close()
    
    return jsonify({'success': success})

@app.route('/api/admin/analytics')
@admin_required
def admin_analytics():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get visitor traffic for the last 7 days
    cur.execute('''
        SELECT date(timestamp) as date, COUNT(DISTINCT phone_number) as visitors
        FROM conversations
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY date(timestamp)
        ORDER BY date
    ''')
    traffic_data = [dict(row) for row in cur.fetchall()]
    
    # Get popular topics based on conversation content
    cur.execute('''
        SELECT 
            CASE 
                WHEN lower(message_content) LIKE '%admission%' THEN 'Admissions'
                WHEN lower(message_content) LIKE '%course%' THEN 'Courses'
                WHEN lower(message_content) LIKE '%fee%' THEN 'Fees'
                WHEN lower(message_content) LIKE '%facility%' OR message_content LIKE '%hostel%' THEN 'Facilities'
                ELSE 'Others'
            END as topic,
            COUNT(*) as count
        FROM conversations
        WHERE message_type = 'user'
        GROUP BY topic
        ORDER BY count DESC
    ''')
    topics_data = [dict(row) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return jsonify({
        'traffic': traffic_data,
        'topics': topics_data
    })

def get_db_connection():
    """Create a database connection"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This allows accessing columns by name
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None

def init_db():
    """Initialize SQLite database with required tables"""
    conn = get_db_connection()
    if not conn:
        return
        
    cur = conn.cursor()
    
    # Create tables
    cur.execute('''
        CREATE TABLE IF NOT EXISTS student_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            phone_number TEXT NOT NULL UNIQUE,
            email TEXT,
            preferred_contact TEXT,
            notes TEXT,
            first_interaction TEXT NOT NULL,
            last_interaction TEXT NOT NULL
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            course_name TEXT NOT NULL,
            batch_year TEXT NOT NULL,
            total_amount REAL NOT NULL,
            admission_status TEXT DEFAULT 'applied',
            application_date TEXT NOT NULL,
            FOREIGN KEY (phone_number) REFERENCES student_details(phone_number)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT,
            message_type TEXT NOT NULL,
            message_content TEXT NOT NULL,
            context_data TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            subject TEXT,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT NOT NULL,
            time_str TEXT NOT NULL,
            is_available INTEGER NOT NULL DEFAULT 1,
            UNIQUE(date_str, time_str)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            email TEXT,
            purpose TEXT NOT NULL,
            date_str TEXT NOT NULL,
            time_str TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            FOREIGN KEY (phone_number) REFERENCES student_details(phone_number)
        )
    ''')
    
    # Create users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            user_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create college_info table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS college_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL,
            content TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY (updated_by) REFERENCES users (id)
        )
    ''')
    
    # Create documents table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            category TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY (uploaded_by) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

def get_client_history(phone_number):
    """Retrieve client's complete history including bookings and conversations"""
    conn = get_db_connection()
    if not conn:
        return None
        
    cur = conn.cursor()
    
    # Get client details
    cur.execute('''
        SELECT * FROM student_details 
        WHERE phone_number = ?
    ''', (phone_number,))
    client_info = cur.fetchone()
    
    if not client_info:
        cur.close()
        conn.close()
        return None
    
    # Get booking history
    cur.execute('''
        SELECT * FROM admissions 
        WHERE phone_number = ? 
        ORDER BY application_date DESC
    ''', (phone_number,))
    admissions = cur.fetchall()
    
    # Get recent conversations
    cur.execute('''
        SELECT * FROM conversations 
        WHERE phone_number = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''', (phone_number,))
    conversations = cur.fetchall()
    
    result = {
        'client_info': dict(client_info),
        'admissions': [dict(row) for row in admissions],
        'conversations': [dict(row) for row in conversations]
    }
    
    cur.close()
    conn.close()
    return result

def save_conversation(phone_number, message_type, content, context_data=None):
    """Save conversation to database"""
    conn = get_db_connection()
    if not conn:
        return
        
    cur = conn.cursor()
    
    try:
        cur.execute('''
            INSERT INTO conversations 
            (phone_number, message_type, message_content, timestamp, context_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            phone_number,
            message_type,
            content,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            json.dumps(context_data) if context_data else None
        ))
        
        conn.commit()
    except Exception as e:
        print(f"Error saving conversation: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def send_confirmation_email(booking_data):
    try:
        msg = MIMEMultipart()
        msg['From'] = COLLEGE_EMAIL
        msg['To'] = booking_data['email']
        msg['Subject'] = f"Booking Confirmation - {COLLEGE_INFO['name']}"

        # Create the email body
        body = f"""
        Dear {booking_data['student_name']},

        Thank you for choosing {COLLEGE_INFO['name']}! Your booking has been confirmed.

        Booking Details:
        - Room Type: {booking_data['course_name']}
        - Check-in Date: {booking_data['date_str']}
        - Check-out Date: {booking_data['time_str']}
        - Booking Reference: {booking_data['id']}

        College Address: {COLLEGE_INFO['address']}
        Contact Phone: {COLLEGE_INFO['phone']}

        If you have any questions or need to modify your booking, please don't hesitate to contact us.

        We look forward to welcoming you!

        Best regards,
        {COLLEGE_INFO['assistant']}
        {COLLEGE_INFO['name']}
        """

        msg.attach(MIMEText(body, 'plain'))

        # Connect to SMTP server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def export_bookings_to_excel():
    try:
        conn = sqlite3.connect(DB_PATH)
        # Read all bookings into a pandas DataFrame
        df = pd.read_sql_query("SELECT * FROM admissions", conn)
        
        # Create Excel file
        excel_path = os.path.join(tempfile.gettempdir(), 'admissions.xlsx')
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        conn.close()
        return excel_path
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")
        return None

def clean_text_for_speech(text):
    """Clean and format text to make it more natural for speech synthesis"""
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s.,!?:;()\'"/-]', '', text)
    
    # Replace contractions with full forms for better pronunciation
    text = re.sub(r"I'd\b", "I would", text)
    text = re.sub(r"You'd\b", "You would", text)
    text = re.sub(r"He'd\b", "He would", text)
    text = re.sub(r"She'd\b", "She would", text)
    text = re.sub(r"We'd\b", "We would", text)
    text = re.sub(r"They'd\b", "They would", text)
    text = re.sub(r"That'd\b", "That would", text)
    text = re.sub(r"It'd\b", "It would", text)
    text = re.sub(r"Who'd\b", "Who would", text)
    
    text = re.sub(r"I'll\b", "I will", text)
    text = re.sub(r"You'll\b", "You will", text)
    text = re.sub(r"He'll\b", "He will", text)
    text = re.sub(r"She'll\b", "She will", text)
    text = re.sub(r"We'll\b", "We will", text)
    text = re.sub(r"They'll\b", "They will", text)
    text = re.sub(r"That'll\b", "That will", text)
    text = re.sub(r"It'll\b", "It will", text)
    text = re.sub(r"Who'll\b", "Who will", text)
    
    # Replace abbreviations with full forms for better pronunciation
    text = text.replace('B.E.', 'Bachelor of Engineering')
    text = text.replace('B.Tech.', 'Bachelor of Technology')
    text = text.replace('M.Tech.', 'Master of Technology')
    text = text.replace('MBA', 'Master of Business Administration')
    text = text.replace('CSE', 'Computer Science and Engineering')
    
    # Make the speech more conversational by preserving sentence structure
    text = text.replace('\n', ' ')
    
    # Clean up any remaining multiple spaces or punctuation
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[,\s]*,[,\s]*', ', ', text)
    text = re.sub(r'[.\s]*\.[.\s]*', '. ', text)
    
    return text.strip()

async def generate_speech(text):
    """Generate speech with proper pauses"""
    communicate = edge_tts.Communicate(text, VOICE)
    
    # Add SSML tags for better pacing
    text_with_breaks = text.replace(', ', '<break time="500ms"/> ')
    text_with_breaks = text_with_breaks.replace('. ', '<break time="800ms"/> ')
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        await communicate.save(fp.name)
        return fp.name

def generate_speech_sync(text):
    try:
        if isinstance(text, dict):
            text = text.get('response', 'I apologize, but I encountered an error generating the response.')
        elif not isinstance(text, str):
            text = str(text)
            
        text = clean_text_for_speech(text)
        print(f"Generating speech for text (first 50 chars): {text[:50]}...")
        return asyncio.run(generate_speech(text))
    except Exception as e:
        print(f"Error generating speech: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
        # Create an empty audio file as fallback
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            return fp.name

def initialize_time_slots():
    """Initialize available time slots for the next 30 days"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get current date
    current_date = datetime.now()
    
    # Generate slots for next 30 days
    for day in range(30):
        date = current_date + timedelta(days=day)
        date_str = date.strftime('%Y-%m-%d')
        
        # Generate slots from 9 AM to 5 PM, hourly
        for hour in range(9, 17):
            time_str = f"{hour:02d}:00"
            
            # Try to insert slot if it doesn't exist
            try:
                cur.execute('''
                    INSERT INTO time_slots (date_str, time_str, is_available)
                    VALUES (?, ?, ?)
                ''', (date_str, time_str, 1))
            except sqlite3.IntegrityError:
                pass
    
    conn.commit()
    cur.close()
    conn.close()

def check_available_slots(date_str=None):
    """Check available slots for a given date or next 7 days if no date provided"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if date_str:
        cur.execute('''
            SELECT date_str, time_str 
            FROM time_slots 
            WHERE date_str = ? AND is_available = 1
            ORDER BY time_str
        ''', (date_str,))
    else:
        # Get slots for next 7 days
        current_date = datetime.now().strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        cur.execute('''
            SELECT date_str, time_str 
            FROM time_slots 
            WHERE date_str BETWEEN ? AND ? AND is_available = 1
            ORDER BY date_str, time_str
        ''', (current_date, future_date))
    
    slots = cur.fetchall()
    cur.close()
    conn.close()
    return slots

def book_slot(date_str, time_str):
    """Book a specific time slot"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Update slot availability
        cur.execute('''
            UPDATE time_slots 
            SET is_available = 0
            WHERE date_str = ? AND time_str = ? AND is_available = 1
            RETURNING id
        ''', (date_str, time_str))
        
        result = cur.fetchone()
        if result:
            conn.commit()
            cur.close()
            conn.close()
            return result[0]
        else:
            conn.rollback()
            cur.close()
            conn.close()
            return None
    except Exception as e:
        print(f"Error booking slot: {str(e)}")
        conn.rollback()
        cur.close()
        conn.close()
        return None

def complete_meeting(meeting_id):
    """Mark a meeting as completed and free up the slot"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get slot_id for the meeting
        cur.execute('SELECT id FROM meetings WHERE id = ?', (meeting_id,))
        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            return False
            
        slot_id = result[0]
        
        # Update meeting status
        cur.execute('''
            UPDATE meetings 
            SET status = 'completed'
            WHERE id = ?
        ''', (meeting_id,))
        
        # Free up the slot
        cur.execute('''
            UPDATE time_slots 
            SET is_available = 1
            WHERE id = ?
        ''', (slot_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error completing meeting: {str(e)}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

def save_client_details(client_data):
    """Save or update client details"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if client exists
        cur.execute('SELECT id FROM student_details WHERE phone_number = ?', (client_data['phone_number'],))
        result = cur.fetchone()
        
        if result:
            # Update existing client
            cur.execute('''
                UPDATE student_details 
                SET student_name = ?, email = ?, 
                    preferred_contact = ?, notes = ?,
                    last_interaction = ?
                WHERE phone_number = ?
            ''', (
                client_data['student_name'],
                client_data.get('email'),
                client_data.get('preferred_contact'),
                client_data.get('notes'),
                current_time,
                client_data['phone_number']
            ))
            client_id = result[0]
        else:
            # Insert new client
            cur.execute('''
                INSERT INTO student_details 
                (student_name, phone_number, email, preferred_contact, notes, first_interaction, last_interaction)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_data['student_name'],
                client_data['phone_number'],
                client_data.get('email'),
                client_data.get('preferred_contact'),
                client_data.get('notes'),
                current_time,
                current_time
            ))
            client_id = cur.lastrowid
        
        conn.commit()
        cur.close()
        conn.close()
        return client_id
    except Exception as e:
        print(f"Error saving client details: {str(e)}")
        conn.rollback()
        cur.close()
        conn.close()
        return None

def get_farewell_message():
    """Generate a context-aware farewell message"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"
    
    farewells = [
        f"Have a wonderful {time_of_day}! Feel free to come back if you need anything else.",
        f"Thank you for visiting {COLLEGE_INFO['name']}. Wishing you a pleasant {time_of_day}!",
        f"Good {time_of_day}! Don't hesitate to ask if you need further assistance.",
        f"Enjoy your {time_of_day}! I'll be here if you need any help later."
    ]
    
    return random.choice(farewells)

def get_ai_response(message, conversation_history):
    try:
        print("Received chat request with message:", message)
        print("Conversation history length:", len(conversation_history))
        
        # Get course info in a more readable format
        courses_info = "\n".join([
            f"- {course['name']}: {course['seats']} seats, ₹{course['fees']} per year, {course['duration']} years"
            for course in COLLEGE_INFO['courses']
        ])

        # System message with college information
        system_message = f"""You are Mia, a friendly AI assistant for {COLLEGE_INFO['name']} ({COLLEGE_INFO['short_name']}). 
You help prospective students and visitors with information about our college.

Key College Information:
- Address: {COLLEGE_INFO['address']}, {COLLEGE_INFO['city']}, {COLLEGE_INFO['state']} {COLLEGE_INFO['pincode']}
- Contact: {COLLEGE_INFO['phone']}, {COLLEGE_INFO['email']}

Available Courses:
{courses_info}

Departments:
{', '.join(COLLEGE_INFO['departments'])}

Your role is to:
1. Provide accurate information about courses, admissions, and facilities
2. Be friendly and professional
3. Guide users through the admission process
4. Schedule campus visits when requested
5. Collect visitor information naturally through conversation

Remember:
- Keep responses concise (max 2-3 sentences)
- If asked about fees, always mention they are per year
- Direct technical/detailed queries to {COLLEGE_INFO['email']}
- Maintain a friendly, professional tone"""

        # Format conversation history
        messages = [{"role": "system", "content": system_message}]
        for msg in conversation_history:
            messages.append({"role": "user" if msg["type"] == "user" else "assistant", "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        print("Phone number provided:", bool(conversation_history and conversation_history[0].get("phone_number")))
        
        # Call OpenAI API
        print("Calling OpenAI API for response...")
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.9,  # Higher temperature for more natural, varied responses
                max_tokens=500
            )
            ai_response = response.choices[0].message.content.strip()
        except Exception as api_error:
            print(f"OpenAI API error: {str(api_error)}")
            ai_response = "I apologize, but I'm having trouble connecting to my knowledge base right now. Please try again in a moment."
        
        print(f"Received AI response (length: {len(ai_response)})")
        
        # Save conversation to database
        if conversation_history and conversation_history[0].get("phone_number"):
            try:
                save_conversation(
                    conversation_history[0]["phone_number"],
                    "user",
                    message
                )
                save_conversation(
                    conversation_history[0]["phone_number"],
                    "assistant",
                    ai_response
                )
                print("Conversation saved to database")
            except Exception as db_error:
                print(f"Error saving conversation: {str(db_error)}")
            
            # Extract information from the conversation
            try:
                print("Extracting information from message...")
                extracted_info = extract_info_from_message(message, ai_response)
                if extracted_info:
                    print("Information extracted:", extracted_info)
                    update_client_details(conversation_history[0]["phone_number"], extracted_info)
                    print("Client details updated")
            except Exception as extract_error:
                print(f"Error extracting information: {str(extract_error)}")
        
        # Generate speech for the response
        try:
            print("Generating speech...")
            audio_file = generate_speech_sync(ai_response)
        except Exception as speech_error:
            print(f"Error generating speech: {str(speech_error)}")
            audio_file = None
        
        print(f"Sending response back to client (length: {len(ai_response)})")
        return {
            "response": ai_response,
            "audio": audio_file
        }
        
    except Exception as e:
        print(f"Error getting AI response: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {getattr(e, '__dict__', {})}")
        return {
            "response": "I apologize, but I encountered an error processing your request. Please try again or contact our support team.",
            "audio": None
        }

def save_interaction(user_message, ai_response, extracted_info=None, interaction_type=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO user_interactions 
        (interaction_time, user_message, ai_response, extracted_info, interaction_type)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        user_message,
        ai_response,
        extracted_info,
        interaction_type
    ))
    conn.commit()
    cur.close()
    conn.close()

def schedule_meeting(meeting_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO meetings 
        (student_name, phone_number, date_str, time_str, purpose, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        meeting_data['student_name'],
        meeting_data.get('phone_number'),
        meeting_data['date_str'],
        meeting_data['time_str'],
        meeting_data.get('purpose'),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    meeting_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return meeting_id

def export_to_excel():
    conn = sqlite3.connect(DB_PATH)
    
    # Get all bookings
    bookings_df = pd.read_sql_query("SELECT * FROM admissions", conn)
    
    # Get all meetings
    meetings_df = pd.read_sql_query("SELECT * FROM meetings", conn)
    
    # Get all interactions
    interactions_df = pd.read_sql_query("SELECT * FROM user_interactions", conn)
    
    # Create Excel writer object
    excel_path = os.path.join(tempfile.gettempdir(), 'college_data.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        bookings_df.to_excel(writer, sheet_name='Admissions', index=False)
        meetings_df.to_excel(writer, sheet_name='Meetings', index=False)
        interactions_df.to_excel(writer, sheet_name='Interactions', index=False)
    
    conn.close()
    return excel_path

def extract_info_from_message(message, ai_response):
    # Extract potential information from user message using GPT
    try:
        system_prompt = """Extract key information from the conversation in a structured way. Include:
        1. Names (student_name)
        2. Phone numbers (phone_number)
        3. Course of interest (course)
        4. Batch year (batch_year)
        5. Email address (email)
        
        Format as valid JSON with these exact field names. Include only fields where information is found.
        Example: {"student_name": "John Doe", "phone_number": "1234567890", "course": "BBA"}
        If no information is found, return empty JSON: {}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User message: {message}\nAI response: {ai_response}"}
        ]
        
        print(f"Sending request to OpenAI for information extraction...")
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            
            # Ensure the response is valid JSON
            extracted_info = response.choices[0].message.content.strip()
            try:
                extracted_info = json.loads(extracted_info)
            except json.JSONDecodeError:
                print("Error decoding JSON response")
                extracted_info = {}
                
            return extracted_info
        except Exception as api_error:
            print(f"OpenAI API error during information extraction: {str(api_error)}")
            return {}
            
    except Exception as e:
        print(f"Error extracting information: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {getattr(e, '__dict__', {})}")
        return {}

def save_to_excel_immediately(data_type, data):
    try:
        excel_file = 'college_data.xlsx'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare the data as a DataFrame
        if data_type == 'interaction':
            new_data = pd.DataFrame([{
                'Timestamp': timestamp,
                'User Message': data.get('user_message', ''),
                'AI Response': data.get('ai_response', ''),
                'Extracted Info': data.get('extracted_info', ''),
                'Type': data.get('interaction_type', 'general')
            }])
            sheet_name = 'Interactions'
        
        elif data_type == 'admission':
            new_data = pd.DataFrame([{
                'Admission ID': data.get('admission_id', ''),
                'Timestamp': timestamp,
                'Student Name': data.get('student_name', ''),
                'Phone Number': data.get('phone_number', ''),
                'Email': data.get('email', ''),
                'Course': data.get('course', ''),
                'Batch Year': data.get('batch_year', ''),
                'Total Amount': data.get('total_amount', 0)
            }])
            sheet_name = 'Admissions'
        
        elif data_type == 'meeting':
            new_data = pd.DataFrame([{
                'Meeting ID': data.get('meeting_id', ''),
                'Timestamp': timestamp,
                'Student Name': data.get('student_name', ''),
                'Phone Number': data.get('phone_number', ''),
                'Meeting Date': data.get('date_str', ''),
                'Meeting Time': data.get('time_str', ''),
                'Purpose': data.get('purpose', '')
            }])
            sheet_name = 'Meetings'
        
        # Try to read existing Excel file or create new
        try:
            with pd.ExcelWriter(excel_file, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                if os.path.exists(excel_file):
                    # Read existing data
                    existing_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    # Combine with new data
                    updated_df = pd.concat([existing_df, new_data], ignore_index=True)
                else:
                    updated_df = new_data
                
                # Write to Excel
                updated_df.to_excel(writer, sheet_name=sheet_name, index=False)
        except FileNotFoundError:
            # If file doesn't exist, create new
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                new_data.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return True
    except Exception as e:
        print(f"Error saving to Excel: {str(e)}")
        return False

@app.route('/')
def home():
    return render_template('index.html', college_info=COLLEGE_INFO)

@app.route('/about')
def about():
    return render_template('about.html', college_info=COLLEGE_INFO)

@app.route('/courses')
def courses():
    return render_template('courses.html', college_info=COLLEGE_INFO)

@app.route('/facilities')
def facilities():
    return render_template('facilities.html', college_info=COLLEGE_INFO)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Here you would typically save this to a database
        # For now, we'll just print it
        print(f"Contact form submission: {name}, {email}, {phone}, {subject}, {message}")
        
        # You could also send an email notification here
        
        # Redirect to the same page with a success message
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html', college_info=COLLEGE_INFO)

@app.route('/chat')
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    try:
        data = request.json
        if not data:
            print("Error: No JSON data received in request")
            return jsonify({
                'text': "I'm sorry, I'm having trouble processing your request. No data was received.",
                'error': "No JSON data in request"
            }), 400
            
        user_message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        phone_number = data.get('phone_number')
        
        print(f"Received chat request with message: {user_message}")
        print(f"Conversation history length: {len(conversation_history)}")
        print(f"Phone number provided: {bool(phone_number)}")
        
        # Ensure conversation_history is a list
        if not isinstance(conversation_history, list):
            print(f"Warning: conversation_history is not a list, it's a {type(conversation_history)}")
            conversation_history = []
        
        # Limit conversation history to last 5 messages to avoid token limits
        if len(conversation_history) > 5:
            conversation_history = conversation_history[-5:]
        
        # Get client history if phone number is provided
        client_history = None
        if phone_number:
            try:
                client_history = get_client_history(phone_number)
                
                # Add context about previous interactions to the AI
                if client_history and client_history.get('client_info'):
                    system_context = f"""
                    Previous client information:
                    - Name: {client_history['client_info']['student_name']}
                    - Last interaction: {client_history['client_info']['last_interaction']}
                    - Previous admissions: {len(client_history['admissions'])}
                    """
                    conversation_history.insert(0, {"role": "system", "content": system_context})
            except Exception as e:
                print(f"Error retrieving client history: {str(e)}")
                # Continue without client history
        
        # Get AI response
        print("Calling OpenAI API for response...")
        response = get_ai_response(user_message, conversation_history)
        if not isinstance(response, dict):
            response = {'response': str(response), 'audio': None}
        ai_response = response.get('response', '')
        print(f"Received AI response (length: {len(ai_response)})")
        
        # Save conversation if phone number is provided
        if phone_number:
            try:
                save_conversation(phone_number, 'user', user_message)
                save_conversation(phone_number, 'assistant', ai_response)
                print("Conversation saved to database")
            except Exception as e:
                print(f"Error saving conversation: {str(e)}")
                # Continue without saving conversation
        
        # Extract and process information
        try:
            print("Extracting information from message...")
            extracted_info = extract_info_from_message(user_message, ai_response)
            
            # Process extracted information
            if extracted_info and phone_number:
                try:
                    # Update client details
                    if 'student_name' in extracted_info:
                        update_client_details(phone_number, extracted_info)
                        print(f"Updated client details for {extracted_info['student_name']}")
                    
                    # Process admission
                    if 'course' in extracted_info:
                        result = process_admission(extracted_info, phone_number)
                        print(f"Processed admission: {result['success']}")
                
                except Exception as e:
                    print(f"Error processing information: {str(e)}")
        except Exception as e:
            print(f"Error extracting or processing information: {str(e)}")
            # Continue without extracted information
        
        # Generate speech response
        try:
            print("Generating speech...")
            speech_text = clean_text_for_speech(ai_response)
            audio_path = generate_speech_sync(speech_text)
            audio_url = f'/api/audio/{os.path.basename(audio_path)}'
            print(f"Speech generated: {audio_url}")
        except Exception as e:
            print(f"Error generating speech: {str(e)}")
            audio_url = None
        
        print(f"Sending response back to client (length: {len(ai_response)})")
        return jsonify({
            'text': ai_response,
            'audio_url': audio_url,
            'client_history': client_history
        })
    except Exception as e:
        print(f"Error in chat_api: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'text': "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment.",
            'error': str(e)
        }), 500

@app.route('/api/audio/<filename>')
def serve_audio(filename):
    # Serve from temp directory
    filepath = os.path.join(tempfile.gettempdir(), filename)
    return send_file(filepath, mimetype='audio/mp3')

def calculate_total_amount(course_name, date_str, time_str):
    # Get course details
    course = COLLEGE_INFO['courses'][course_name]
    
    # Calculate total fees
    total_amount = course['fee']
    
    return {
        'total_amount': total_amount,
        'course': course_name.upper(),
        'date_str': date_str,
        'time_str': time_str
    }

def generate_bill(booking_data, booking_id):
    # Calculate amounts
    amounts = calculate_total_amount(
        booking_data['course'],
        booking_data['date_str'],
        booking_data['time_str']
    )
    
    # Generate bill content
    bill = f"""
    {COLLEGE_INFO['name']}
    {COLLEGE_INFO['address']}
    Phone: {COLLEGE_INFO['phone']}
    ----------------------------------------
    BOOKING CONFIRMATION & BILL
    ----------------------------------------
    Booking ID: {booking_id}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Guest Details:
    Name: {booking_data['student_name']}
    Phone: {booking_data['phone_number']}
    
    Booking Details:
    Course: {booking_data['course']}
    Check-in: {booking_data['date_str']}
    Check-out: {booking_data['time_str']}
    
    Charges:
    Course Fee: ₹{amounts['total_amount']:,.2f}
    ----------------------------------------
    Total Amount: ₹{amounts['total_amount']:,.2f}
    
    Thank you for choosing {COLLEGE_INFO['name']}!
    We look forward to welcoming you.
    """
    
    # Save bill to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(bill)
        return f.name

def update_excel_sheet(booking_data, booking_id, amounts):
    excel_file = 'admissions.xlsx'
    
    # Create DataFrame for new booking
    new_booking = pd.DataFrame([{
        'Admission ID': booking_id,
        'Student Name': booking_data['student_name'],
        'Phone Number': booking_data['phone_number'],
        'Course': booking_data['course'],
        'Batch Year': booking_data['batch_year'],
        'Total Amount': amounts['total_amount'],
        'Admission Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }])
    
    try:
        # Try to read existing Excel file
        if os.path.exists(excel_file):
            existing_df = pd.read_excel(excel_file)
            updated_df = pd.concat([existing_df, new_booking], ignore_index=True)
        else:
            updated_df = new_booking
        
        # Save to Excel
        updated_df.to_excel(excel_file, index=False)
        return True
    except Exception as e:
        print(f"Error updating Excel sheet: {str(e)}")
        return False

@app.route('/api/book', methods=['POST'])
def book_room():
    data = request.json
    
    # Connect to database
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('''
            INSERT INTO admissions 
            (student_name, phone_number, course_name, batch_year, total_amount, admission_status, application_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['student_name'],
            data['phone_number'],
            data['course'],
            data['batch_year'],
            data['total_amount'],
            'applied',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        
        # Get the booking ID
        booking_id = cur.lastrowid
        
        # Update Excel sheet
        excel_updated = update_excel_sheet(data, booking_id, data)
        
        return jsonify({
            "success": True,
            "message": "Admission application submitted successfully",
            "admission_id": booking_id,
            "total_amount": data['total_amount']
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    
    finally:
        cur.close()
        conn.close()

@app.route('/api/bill/<filename>')
def serve_bill(filename):
    # Serve from temp directory
    filepath = os.path.join(tempfile.gettempdir(), filename)
    return send_file(
        filepath,
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'bill_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    )

@app.route('/api/export', methods=['GET'])
def export_data():
    try:
        excel_path = export_to_excel()
        if excel_path:
            return send_file(excel_path, 
                           mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           as_attachment=True,
                           download_name='college_data.xlsx')
        else:
            return jsonify({'error': 'Failed to generate Excel file'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add route to initialize time slots
@app.route('/api/initialize-slots', methods=['POST'])
def init_slots():
    try:
        initialize_time_slots()
        return jsonify({'message': 'Time slots initialized successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add route to complete meetings
@app.route('/api/complete-meeting/<int:meeting_id>', methods=['POST'])
def mark_meeting_complete(meeting_id):
    try:
        if complete_meeting(meeting_id):
            return jsonify({'message': f'Meeting #{meeting_id} marked as completed'})
        else:
            return jsonify({'error': 'Meeting not found or already completed'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add route to check available slots
@app.route('/api/available-slots', methods=['GET'])
def get_available_slots():
    date = request.args.get('date')
    try:
        slots = check_available_slots(date)
        return jsonify({'slots': slots})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add missing function for updating client details
def update_client_details(phone_number, info_dict):
    """Update client details in the database"""
    conn = get_db_connection()
    if not conn:
        return None
        
    cur = conn.cursor()
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if client exists
        cur.execute('SELECT id FROM student_details WHERE phone_number = ?', (phone_number,))
        result = cur.fetchone()
        
        if result:
            # Update existing client
            cur.execute('''
                UPDATE student_details 
                SET student_name = ?,
                    email = ?,
                    preferred_contact = ?,
                    notes = ?,
                    last_interaction = ?
                WHERE phone_number = ?
            ''', (
                info_dict.get('student_name'),
                info_dict.get('email'),
                info_dict.get('preferred_contact'),
                info_dict.get('notes'),
                current_time,
                phone_number
            ))
            client_id = result[0]
        else:
            # Insert new client
            cur.execute('''
                INSERT INTO student_details 
                (student_name, phone_number, email, preferred_contact, notes, first_interaction, last_interaction)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                info_dict.get('student_name'),
                phone_number,
                info_dict.get('email'),
                info_dict.get('preferred_contact'),
                info_dict.get('notes'),
                current_time,
                current_time
            ))
            client_id = cur.lastrowid
        
        conn.commit()
        return client_id
    except Exception as e:
        print(f"Error updating client details: {str(e)}")
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

# Add missing function for processing admissions
def process_admission(info_dict, phone_number):
    """Process admission information and save to database"""
    try:
        # Get course details
        course_name = info_dict.get('course', '').lower()
        
        if course_name not in COLLEGE_INFO['courses']:
            return {
                "success": False, 
                "message": f"We don't offer a course named {course_name}. Available courses are: {', '.join(COLLEGE_INFO['courses'].keys()).upper()}"
            }
            
        # Get batch year (current or next year)
        current_year = datetime.now().year
        batch_year = info_dict.get('batch_year', str(current_year))
            
        # Calculate total fees
        course_fee = COLLEGE_INFO['courses'][course_name]['fee']
        
        # Create admission record
        conn = get_db_connection()
        if not conn:
            return {"success": False, "message": "Database connection failed"}
            
        cur = conn.cursor()
        
        # Check if student already has an application for this course and batch
        cur.execute("""
            SELECT id FROM admissions 
            WHERE phone_number = ? AND course_name = ? AND batch_year = ?
        """, (phone_number, course_name, batch_year))
        
        existing = cur.fetchone()
        if existing:
            conn.close()
            return {
                "success": False, 
                "message": f"You already have an application for {course_name.upper()} for batch {batch_year}. Your application ID is {existing['id']}."
            }
        
        # Get student name
        cur.execute("SELECT student_name FROM student_details WHERE phone_number = ?", (phone_number,))
        student = cur.fetchone()
        if not student:
            conn.close()
            return {"success": False, "message": "Student details not found"}
            
        student_name = student['student_name']
        
        # Insert admission record
        cur.execute("""
            INSERT INTO admissions 
            (student_name, phone_number, course_name, batch_year, total_amount, admission_status, application_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            student_name, 
            phone_number, 
            course_name, 
            batch_year, 
            course_fee, 
            'applied', 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        admission_id = cur.lastrowid
        conn.close()
        
        return {
            "success": True,
            "message": f"Application for {course_name.upper()} has been submitted successfully. Your application ID is {admission_id}.",
            "admission_id": admission_id,
            "course": course_name.upper(),
            "fee": course_fee,
            "batch_year": batch_year
        }
        
    except Exception as e:
        print(f"Error processing admission: {str(e)}")
        return {"success": False, "message": "An error occurred while processing your admission application."}

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        user_type = request.form['user_type']
        
        # Don't allow registering as admin
        if username == ADMIN_USERNAME:
            return render_template('register.html', error="This username is reserved. Please choose another one.")
        
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            password_hash = generate_password_hash(password)
            
            cur.execute('''
                INSERT INTO users (username, password_hash, fullname, email, phone, user_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, fullname, email, phone, user_type))
            
            conn.commit()
            
            # Log the user in
            cur.execute('SELECT id FROM users WHERE username = ?', (username,))
            user = cur.fetchone()
            session['user_id'] = user['id']
            session['username'] = username
            session['fullname'] = fullname
            session['email'] = email
            session['phone'] = phone
            session['user_type'] = user_type
            
            return redirect(url_for('chat_page'))
            
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username or email already exists")
        finally:
            cur.close()
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if this is an admin login
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Create a session for the admin
            session['user_id'] = 0  # Special ID for admin
            session['username'] = username
            session['fullname'] = 'Administrator'
            session['email'] = ''
            session['phone'] = ''
            session['user_type'] = 'admin'
            
            return redirect(url_for('admin_dashboard'))
        
        # Regular user login
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cur.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['fullname'] = user['fullname']
            session['email'] = user['email']
            session['phone'] = user['phone']
            session['user_type'] = user['user_type']
            
            return redirect(url_for('chat_page'))
        
        return render_template('login.html', error="Invalid username or password")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear all session variables
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin/update_info', methods=['POST'])
def update_college_info():
    section = request.form['section']
    content = request.form['content']
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('''
            INSERT OR REPLACE INTO college_info (section, content, updated_by)
            VALUES (?, ?, ?)
        ''', (section, content, session['user_id']))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        cur.close()
        conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/upload_document', methods=['POST'])
def upload_document():
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['document']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        title = request.form.get('title', filename)
        category = request.form.get('category', 'general')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute('''
                INSERT INTO documents (title, filename, category, uploaded_by)
                VALUES (?, ?, ?, ?)
            ''', (title, filename, category, session['user_id']))
            
            conn.commit()
            
            # Process document content and update AI knowledge base
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Here you would add code to process the document content
                # and update the AI's knowledge base
            
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        finally:
            cur.close()
            conn.close()
    
    return jsonify({'success': False, 'error': 'Invalid file type'})

@app.route('/admin/documents')
def list_documents():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT d.*, u.username as uploaded_by_user
        FROM documents d
        JOIN users u ON d.uploaded_by = u.id
        ORDER BY d.uploaded_at DESC
    ''')
    
    documents = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify({'documents': [dict(doc) for doc in documents]})

@app.route('/database-view')
@admin_required
def database_view():
    users = get_all_users()
    conversations = get_all_conversations()
    admissions = get_all_admissions()
    queries = get_all_queries() or []  # Use empty list if None is returned
    return render_template('database_view.html', 
                         users=users,
                         conversations=conversations,
                         admissions=admissions,
                         queries=queries)

@app.route('/api/refresh/<table_type>')
@admin_required
def refresh_table(table_type):
    if table_type == 'users':
        data = get_all_users()
    elif table_type == 'conversations':
        data = get_all_conversations()
    elif table_type == 'admissions':
        data = get_all_admissions()
    elif table_type == 'queries':
        data = get_all_queries()
    else:
        return jsonify([])
    return jsonify(data)

def get_all_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(row) for row in users]

def get_all_conversations():
    conn = get_db_connection()
    conversations = conn.execute('''
        SELECT c.*, s.student_name 
        FROM conversations c
        LEFT JOIN student_details s ON c.phone_number = s.phone_number
        ORDER BY c.timestamp DESC
    ''').fetchall()
    conn.close()
    return [dict(row) for row in conversations]

def get_all_admissions():
    conn = get_db_connection()
    admissions = conn.execute('''
        SELECT * FROM admissions 
        ORDER BY application_date DESC
    ''').fetchall()
    conn.close()
    return [dict(row) for row in admissions]

def get_all_queries():
    """Get all queries from the database"""
    conn = get_db_connection()
    try:
        queries = conn.execute('''
            SELECT * FROM queries 
            ORDER BY created_at DESC
        ''').fetchall()
        return [dict(row) for row in queries]
    except sqlite3.OperationalError:
        # Return empty list if table doesn't exist
        return []
    finally:
        conn.close()

def scrape_website(url):
    """
    Scrape website content and return structured data
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {"error": "Invalid URL format"}

        # Send request with headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'lxml')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract main content
        content = {
            "title": soup.title.string if soup.title else "",
            "headings": [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])],
            "paragraphs": [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)],
            "links": [{"text": a.get_text(strip=True), "href": urljoin(url, a.get('href', ''))} 
                     for a in soup.find_all('a') if a.get_text(strip=True)],
            "tables": []
        }

        # Extract tables
        for table in soup.find_all('table'):
            table_data = []
            for row in table.find_all('tr'):
                cols = row.find_all(['td', 'th'])
                if cols:
                    table_data.append([col.get_text(strip=True) for col in cols])
            if table_data:
                content["tables"].append(table_data)

        return content

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch website: {str(e)}"}
    except Exception as e:
        return {"error": f"Error processing website content: {str(e)}"}

def generate_questions(website_data):
    """
    Generate relevant questions based on website content
    """
    try:
        # Prepare content for GPT
        content_text = f"Title: {website_data['title']}\n\n"
        content_text += "Headings:\n" + "\n".join(website_data['headings']) + "\n\n"
        content_text += "Content:\n" + "\n".join(website_data['paragraphs'])

        # Call GPT to generate questions
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are an expert at analyzing educational institution websites and generating questions. Create a comprehensive list of questions covering these categories:
                1. Academic Programs and Courses
                2. Admission Process and Requirements
                3. Infrastructure and Facilities
                4. Faculty and Staff
                5. Campus Life and Activities
                6. Placement and Career Services
                7. Research and Development
                8. Contact Information and Location
                
                Generate 2-3 specific questions for each relevant category based on the available content."""},
                {"role": "user", "content": content_text}
            ],
            temperature=0.7,
            max_tokens=500
        )

        questions = response.choices[0].message.content.strip().split('\n')
        return [q.strip('1234567890. -•*') for q in questions if q.strip()]

    except Exception as e:
        return ["Error generating questions: " + str(e)]

def answer_question(question, website_data):
    """
    Generate answer based on website content and question
    """
    try:
        # Prepare content for GPT
        content_text = f"Website Title: {website_data['title']}\n\n"
        content_text += "Content:\n" + "\n".join(website_data['paragraphs'])
        if website_data['tables']:
            content_text += "\n\nTables:\n"
            for table in website_data['tables']:
                content_text += "\n".join([" | ".join(row) for row in table]) + "\n\n"

        # Call GPT to answer the question
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are an expert at answering questions about educational institutions based on their website content. 
                Provide accurate, concise answers based only on the provided content. If the information is not available in the content, say so."""},
                {"role": "user", "content": f"Based on this website content:\n\n{content_text}\n\nAnswer this question: {question}"}
            ],
            temperature=0.7,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating answer: {str(e)}"

class BMITOfflineBot:
    def __init__(self):
        self.qa_database = {
            # Course Related Questions
            "courses": {
                "keywords": ["course", "program", "branch", "degree", "study", "department"],
                "answer": """BMIT offers the following engineering programs:
                1. B.E. Computer Science & Engineering (60 seats)
                2. B.E. Civil Engineering (60 seats)
                3. B.E. Mechanical Engineering (60 seats)
                All programs are 4-year undergraduate degrees."""
            },
            "fees": {
                "keywords": ["fee", "cost", "price", "payment", "charges", "expense"],
                "answer": """The fee structure for BMIT programs:
                - B.E. Computer Science: ₹95,000 per year
                - B.E. Civil Engineering: ₹90,000 per year
                - B.E. Mechanical Engineering: ₹90,000 per year"""
            },
            "admission": {
                "keywords": ["admission", "apply", "enroll", "join", "register", "entrance", "how to get"],
                "answer": """Admission Process at BMIT:
                1. Complete 12th standard with PCM
                2. Apply through state CET
                3. Submit required documents
                4. Complete admission formalities at college
                For detailed information, contact the admission office."""
            },
            "facilities": {
                "keywords": ["facility", "infrastructure", "lab", "laboratory", "library", "hostel", "canteen"],
                "answer": """BMIT facilities include:
                1. Modern Computer Labs
                2. Well-equipped Library
                3. Sports Complex
                4. Student Hostel
                5. Cafeteria
                6. Workshop and Labs for each department"""
            },
            "location": {
                "keywords": ["location", "address", "where", "place", "reach", "direction"],
                "answer": "BMIT is located at: Solapur - Mangalwedha National Highway, Belati, Solapur, Maharashtra 413002"
            },
            "contact": {
                "keywords": ["contact", "phone", "email", "number", "call", "reach"],
                "answer": "Contact BMIT:\nPhone: +91 217 239 2303\nEmail: info@bmit.ac.in"
            },
            "placement": {
                "keywords": ["placement", "job", "career", "company", "recruit", "package"],
                "answer": "BMIT has a dedicated placement cell that helps students with career opportunities. Many reputed companies visit for campus recruitment."
            },
            "faculty": {
                "keywords": ["faculty", "teacher", "professor", "staff", "teaching"],
                "answer": "BMIT has highly qualified faculty members with extensive experience in their respective fields. Many faculty members hold Ph.D. degrees."
            },
            "general": {
                "keywords": ["hello", "hi", "hey", "about", "tell me"],
                "answer": "Welcome to BMIT! We are a premier engineering institute in Solapur offering quality education in Computer Science, Civil, and Mechanical Engineering."
            }
        }

    def find_best_match(self, user_question):
        user_question = user_question.lower()
        best_match = None
        max_matches = 0

        for category, data in self.qa_database.items():
            matches = sum(1 for keyword in data["keywords"] if keyword in user_question)
            if matches > max_matches:
                max_matches = matches
                best_match = category

        if max_matches == 0:
            return "general"
        return best_match

    def get_answer(self, user_question):
        if not user_question.strip():
            return "Please ask a question about BMIT."

        matched_category = self.find_best_match(user_question)
        return self.qa_database[matched_category]["answer"]

# Initialize the bot
bmit_bot = BMITOfflineBot()

@app.route('/api/offline-chat', methods=['POST'])
def offline_chat():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400

        message = data.get('message', '').strip()
        
        # Get answer from offline bot
        answer = bmit_bot.get_answer(message)
        
        return jsonify({"text": answer})

    except Exception as e:
        print(f"Error in offline chat: {str(e)}")
        return jsonify({"error": "An error occurred processing your request"}), 500

if __name__ == '__main__':
    init_db()
    initialize_time_slots()
    app.run(debug=True) 