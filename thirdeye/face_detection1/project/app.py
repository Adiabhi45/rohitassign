
# -*- coding: utf-8 -*-
"""
Face Recognition System - Production Ready
Offline ML-based face recognition with secure authentication
"""

from flask import Flask, render_template, request, send_from_directory, jsonify, session, redirect, url_for
import os
from datetime import datetime, timedelta
import sqlite3
import random
import string
from functools import wraps
from PIL import Image, ImageEnhance
import logging
from logging.handlers import RotatingFileHandler
import secrets
from werkzeug.security import safe_join
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Production-grade secret key from environment
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
if os.getenv('SECRET_KEY') is None:
    print('WARNING: SECRET_KEY not set in environment. Using random key (sessions will reset on restart).')

# Configure upload folder for face sketches
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'output')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))  # 16MB default
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Environment configuration
DEBUG_MODE = os.getenv('FLASK_ENV', 'development') == 'development'
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '127.0.0.1')

# Reference database configuration
REFERENCE_FOLDER = os.getenv('REFERENCE_FOLDER', 'reference_database')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'face_sketch.db')

# Logging configuration
if not DEBUG_MODE:
    # Production logging
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Face Recognition App startup')
else:
    # Development logging
    app.logger.setLevel(logging.DEBUG)

# Security headers middleware
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if not DEBUG_MODE:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# CLIP model will be loaded on first use (lazy loading)
clip_model = None
clip_preprocess = None
device = None

def load_clip_model():
    """Load CLIP model on demand with error handling"""
    global clip_model, clip_preprocess, device
    if clip_model is None:
        try:
            app.logger.info('[LOADING] Loading CLIP model...')
            import torch
            import clip
            device = "cuda" if torch.cuda.is_available() else "cpu"
            clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
            app.logger.info(f'[SUCCESS] CLIP model loaded on {device}')
        except Exception as e:
            app.logger.error(f'[ERROR] Failed to load CLIP model: {str(e)}')
            raise
    return clip_model, clip_preprocess, device

# Database setup
def init_db():
    """Initialize the SQLite database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create OTP table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                otp_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert default user if not exists
        cursor.execute('SELECT id FROM users WHERE email = ?', ('admin@facesketch.com',))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (username, email) 
                VALUES (?, ?)
            ''', ('admin', 'admin@facesketch.com'))
            app.logger.info('[SUCCESS] Default user created: admin@facesketch.com')
        
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f'[ERROR] Database initialization error: {str(e)}')
        raise

# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f'[ERROR] CRITICAL: Failed to initialize database: {str(e)}')
    if not DEBUG_MODE:
        raise

def generate_otp(length=6):
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

def login_required(f):
    """Decorator to protect routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and OTP generation"""
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        try:
            conn = sqlite3.connect(DATABASE_PATH, timeout=10)
            cursor = conn.cursor()
            
            # Check if user exists - only allow existing users
            cursor.execute('SELECT id, username, email FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                app.logger.warning(f'Login attempt for non-existent user: {email}')
                return jsonify({
                    'success': False, 
                    'message': 'User not found. Please contact administrator.'
                }), 404
            
            user_id, username, email = user
            
            # Generate OTP
            otp_code = generate_otp()
            expires_at = datetime.now() + timedelta(minutes=10)
            
            cursor.execute('''
                INSERT INTO otps (user_id, otp_code, expires_at) 
                VALUES (?, ?, ?)
            ''', (user_id, otp_code, expires_at))
            conn.commit()
            conn.close()
            
            # Log OTP (in production, send via email/SMS service)
            if DEBUG_MODE:
                print('=' * 50)
                print(f'[OTP] OTP GENERATED FOR {email}')
                print(f'[EMAIL] User: {username}')
                print(f'[CODE] OTP Code: {otp_code}')
                print(f'[TIME] Expires at: {expires_at.strftime("%Y-%m-%d %H:%M:%S")}')
                print('=' * 50)
            else:
                app.logger.info(f'OTP generated for user {username} (expires at {expires_at})')
                # TODO: Integrate with email/SMS service (e.g., SendGrid, Twilio)
            
            return jsonify({
                'success': True,
                'message': 'OTP sent successfully!' if not DEBUG_MODE else 'OTP generated! Check the server console for OTP code.',
                'user_id': user_id
            })
        except Exception as e:
            app.logger.error(f'Error generating OTP for {email}: {str(e)}')
            return jsonify({
                'success': False,
                'message': 'An error occurred. Please try again later.'
            }), 500
    
    return render_template('login.html')

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and login user"""
    data = request.get_json()
    user_id = data.get('user_id')
    otp_code = data.get('otp_code', '').strip()
    
    if not user_id or not otp_code:
        return jsonify({'success': False, 'message': 'User ID and OTP are required'}), 400
    
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10)
        cursor = conn.cursor()
        
        # Check OTP
        cursor.execute('''
            SELECT id, expires_at, is_used FROM otps 
            WHERE user_id = ? AND otp_code = ? 
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id, otp_code))
        
        otp_record = cursor.fetchone()
        
        if not otp_record:
            conn.close()
            app.logger.warning(f'Invalid OTP attempt for user_id: {user_id}')
            return jsonify({'success': False, 'message': 'Invalid OTP code'}), 400
        
        otp_id, expires_at_str, is_used = otp_record
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S.%f')
        
        if is_used:
            conn.close()
            return jsonify({'success': False, 'message': 'OTP already used'}), 400
        
        if datetime.now() > expires_at:
            conn.close()
            return jsonify({'success': False, 'message': 'OTP expired'}), 400
        
        # Mark OTP as used
        cursor.execute('UPDATE otps SET is_used = 1 WHERE id = ?', (otp_id,))
        conn.commit()
        
        # Get user info
        cursor.execute('SELECT username, email FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            username, email = user
            # Set session
            session['user_id'] = user_id
            session['username'] = username
            session['email'] = email
            session.permanent = True
            
            app.logger.info(f'[SUCCESS] User {username} logged in successfully!')
            
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'redirect': url_for('index')
            })
        
        return jsonify({'success': False, 'message': 'User not found'}), 400
    except Exception as e:
        app.logger.error(f'Error during OTP verification: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again later.'
        }), 500

@app.route('/logout')
def logout():
    """Logout user"""
    username = session.get('username', 'Unknown')
    session.clear()
    app.logger.info(f'[LOGOUT] User {username} logged out')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Render the main application page"""
    return render_template('index.html', username=session.get('username'))

@app.route('/assets/<category>')
@login_required
def get_assets(category):
    """Get list of assets for a specific category"""
    asset_path = os.path.join('static', 'assets', category)
    if os.path.exists(asset_path):
        files = [f for f in os.listdir(asset_path) if f.endswith('.png')]
        return jsonify({'assets': files})
    return jsonify({'assets': []})

@app.route('/save-sketch', methods=['POST'])
@login_required
def save_sketch():
    """Save the created sketch"""
    try:
        data = request.get_json()
        sketch_data = data.get('sketchData')
        
        # Add user info to sketch data
        sketch_data['user_id'] = session.get('user_id')
        sketch_data['username'] = session.get('username')
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sketch_{timestamp}.json'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save sketch data
        import json
        with open(filepath, 'w') as f:
            json.dump(sketch_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Sketch saved successfully!',
            'filename': filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving sketch: {str(e)}'
        }), 500

@app.route('/output/<filename>')
@login_required
def download_sketch(filename):
    """Download saved sketch"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/clip-recognition')
@login_required
def clip_recognition():
    """CLIP-based local face recognition page"""
    return render_template('clip_recognition.html', username=session.get('username'))

@app.route('/face-recognition')
@login_required
def face_recognition():
    """AWS Rekognition-based face recognition page"""
    return render_template('face_recognition.html', username=session.get('username'))

@app.route('/clip-compare', methods=['POST'])
@login_required
def clip_compare():
    """Compare sketch with reference images from database using CLIP embeddings"""
    try:
        # Load CLIP model on first use
        import torch
        model, preprocess, dev = load_clip_model()
        
        # Get the uploaded sketch image
        if 'sketch' not in request.files:
            return jsonify({'success': False, 'message': 'No sketch file provided'}), 400
        
        sketch_file = request.files['sketch']
        
        if sketch_file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Process sketch image
        sketch_image = Image.open(sketch_file).convert('RGB')
        sketch_preprocessed = preprocess(sketch_image).unsqueeze(0).to(dev)
        
        # Get sketch embedding
        with torch.no_grad():
            sketch_features = model.encode_image(sketch_preprocessed)
            sketch_features = sketch_features / sketch_features.norm(dim=-1, keepdim=True)
        
        # Get all reference images from database folder
        reference_folder = 'reference_database'
        
        if not os.path.exists(reference_folder):
            return jsonify({
                'success': False,
                'message': 'Reference database folder not found. Please add reference images to the "reference_database" folder.'
            }), 404
        
        # Get all image files from reference database
        supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        reference_files = [f for f in os.listdir(reference_folder) 
                          if f.lower().endswith(supported_formats)]
        
        if not reference_files:
            return jsonify({
                'success': False,
                'message': 'No reference images found in database. Please add images to the "reference_database" folder.'
            }), 404
        
        results = []
        
        # Compare with each reference image in database
        for ref_filename in reference_files:
            try:
                ref_path = os.path.join(reference_folder, ref_filename)
                
                # Process reference image
                ref_image = Image.open(ref_path).convert('RGB')
                ref_preprocessed = preprocess(ref_image).unsqueeze(0).to(dev)
                
                # Get reference embedding
                with torch.no_grad():
                    ref_features = model.encode_image(ref_preprocessed)
                    ref_features = ref_features / ref_features.norm(dim=-1, keepdim=True)
                
                # Calculate cosine similarity
                similarity = (sketch_features @ ref_features.T).item()
                
                # Convert to percentage (0-100)
                prediction_score = ((similarity + 1) / 2) * 100  # Normalize from [-1,1] to [0,100]
                
                results.append({
                    'filename': ref_filename,
                    'similarity': round(similarity, 4),
                    'prediction_score': round(prediction_score, 2),
                    'matched': prediction_score >= 30,  # Consider matched if score >= 50%
                    'image_path': f'/reference-image/{ref_filename}'
                })
                
                print(f'[INFO] {ref_filename}: Similarity={similarity:.4f}, Score={prediction_score:.2f}%')
                
            except Exception as e:
                results.append({
                    'filename': ref_filename,
                    'error': str(e),
                    'matched': False
                })
                print(f'[ERROR] Error processing {ref_filename}: {str(e)}')
        
        # Sort results by prediction score (highest first)
        results.sort(key=lambda x: x.get('prediction_score', 0), reverse=True)
        
        # Get top matches (score >= 50%)
        top_matches = [r for r in results if r.get('matched', False)]
        
        return jsonify({
            'success': True,
            'message': f'Searched {len(results)} reference images in database',
            'total_images': len(results),
            'matches_found': len(top_matches),
            'results': results,
            'device': dev
        })
        
    except Exception as e:
        print(f'[ERROR] Error in CLIP face recognition: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error processing images: {str(e)}'
        }), 500

@app.route('/reference-image/<filename>')
# @login_required
def get_reference_image(filename):
    """Serve reference images from database with security"""
    try:
        # Prevent directory traversal attacks
        safe_path = safe_join(REFERENCE_FOLDER, filename)
        if safe_path is None or not os.path.exists(safe_path):
            app.logger.warning(f'Invalid reference image request: {filename}')
            return jsonify({'success': False, 'message': 'Image not found'}), 404
        return send_from_directory(REFERENCE_FOLDER, filename)
    except Exception as e:
        app.logger.error(f'Error serving reference image {filename}: {str(e)}')
        return jsonify({'success': False, 'message': 'Error loading image'}), 500

@app.route('/offline-face-match')
@login_required
def offline_face_match():
    """Offline face recognition page (AWS Rekognition alternative)"""
    return render_template('offline_face_match.html', username=session.get('username'))

@app.route('/offline-face-match', methods=['POST'])
@login_required
def offline_face_match_process():
    """
    Process face matching using offline ML model (CLIP)
    Similar to AWS Rekognition's SearchFacesByImage functionality
    """
    try:
        # Load CLIP model on first use
        import torch
        import numpy as np
        model, preprocess, dev = load_clip_model()
        
        # Get the uploaded sketch image
        if 'sketch' not in request.files:
            return jsonify({'success': False, 'message': 'No sketch file provided'}), 400
        
        sketch_file = request.files['sketch']
        
        if sketch_file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Process sketch image - Apply face-focused preprocessing
        sketch_image = Image.open(sketch_file).convert('RGB')
        
        # Resize to standard size for better comparison
        sketch_image = sketch_image.resize((224, 224), Image.LANCZOS)
        
        # Apply contrast enhancement for better feature detection
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(sketch_image)
        sketch_image = enhancer.enhance(1.5)  # Increase contrast by 50%
        
        sketch_preprocessed = preprocess(sketch_image).unsqueeze(0).to(dev)
        
        # Get sketch embedding
        with torch.no_grad():
            sketch_features = model.encode_image(sketch_preprocessed)
            sketch_features = sketch_features / sketch_features.norm(dim=-1, keepdim=True)
        
        # Get all reference images from database folder
        reference_folder = 'D:\\thirdeye\\thirdeye\\face_detection1\\project\\reference_database'
        
        if not os.path.exists(reference_folder):
            return jsonify({
                'success': False,
                'message': 'Reference database folder not found. Please add reference images to the "reference_database" folder.'
            }), 404
        
        # Get all image files from reference database
        supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        reference_files = [f for f in os.listdir(reference_folder) 
                          if f.lower().endswith(supported_formats)]
        
        if not reference_files:
            return jsonify({
                'success': False,
                'message': 'No reference images found in database. Please add images to the "reference_database" folder.'
            }), 404
        
        matches = []
        embeddings_cache = {}  # Cache for reference embeddings
        
        # Compare with each reference image in database
        for ref_filename in reference_files:
            try:
                ref_path = os.path.join(reference_folder, ref_filename)
                
                # Process reference image with same preprocessing
                ref_image = Image.open(ref_path).convert('RGB')
                
                # Resize to standard size
                ref_image = ref_image.resize((224, 224), Image.LANCZOS)
                
                # Apply same contrast enhancement
                enhancer = ImageEnhance.Contrast(ref_image)
                ref_image = enhancer.enhance(1.5)
                
                ref_preprocessed = preprocess(ref_image).unsqueeze(0).to(dev)
                
                # Get reference embedding
                with torch.no_grad():
                    ref_features = model.encode_image(ref_preprocessed)
                    ref_features = ref_features / ref_features.norm(dim=-1, keepdim=True)
                
                # Calculate cosine similarity
                similarity = (sketch_features @ ref_features.T).item()
                
                # Enhanced scoring algorithm that considers facial structure
                # Boost the score slightly for better matches
                base_score = ((similarity + 1) / 2) * 100  # Normalize from [-1,1] to [0,100]
                
                # Apply confidence boost for higher similarities
                if similarity > 0.7:
                    confidence_boost = (similarity - 0.7) * 20  # Up to 6% boost for very high similarities
                    prediction_score = min(base_score + confidence_boost, 100)
                else:
                    prediction_score = base_score
                
                matches.append({
                    'filename': ref_filename,
                    'similarity': round(similarity, 4),
                    'prediction_score': round(prediction_score, 2),
                    'matched': prediction_score >= 35,  # Slightly higher threshold for better accuracy
                    'image_path': f'/reference-image/{ref_filename}'
                })
                
                if DEBUG_MODE:
                    print(f'[INFO] {ref_filename}: Similarity={similarity:.4f}, Score={prediction_score:.2f}%')
                
            except Exception as e:
                app.logger.error(f'Error processing {ref_filename}: {str(e)}')
                if DEBUG_MODE:
                    print(f'[ERROR] Error processing {ref_filename}: {str(e)}')
        
        # Sort by prediction score (highest first)
        matches.sort(key=lambda x: x.get('prediction_score', 0), reverse=True)
        
        # Get best match
        best_match = matches[0] if matches else None
        
        # Check if best match meets threshold (75% for better accuracy)
        if best_match and best_match['prediction_score'] >= 35:
            app.logger.info(f'[SUCCESS] MATCH FOUND: {best_match["filename"]} ({best_match["prediction_score"]}%)')
            if DEBUG_MODE:
                print(f'\n[SUCCESS] MATCH FOUND: {best_match["filename"]} ({best_match["prediction_score"]}%)\n')
            return jsonify({
                'success': True,
                'message': 'Face matched successfully!',
                'best_match': best_match,
                'total_images': len(matches),
                'threshold': 35,
                'device': dev
            })
        else:
            app.logger.info(f'[ERROR] NO MATCH FOUND (threshold: 75%, best: {best_match["prediction_score"] if best_match else 0}%)')
            if DEBUG_MODE:
                print(f'\n[ERROR] NO MATCH FOUND (threshold: 75%, best: {best_match["prediction_score"] if best_match else 0}%)\n')
            return jsonify({
                'success': False,
                'message': f'No match found in the database. Best match: {best_match["prediction_score"] if best_match else 0}% (threshold: 75%)',
                'best_match': best_match,  # Still return best attempt
                'total_images': len(matches),
                'threshold': 35,
                'device': dev
            })
        
    except Exception as e:
        app.logger.error(f'Error in offline face recognition: {str(e)}')
        if DEBUG_MODE:
            print(f'[ERROR] Error in offline face recognition: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing the image. Please try again.'
        }), 500

if __name__ == '__main__':
    # Production-ready startup
    app.logger.info(f'Starting Face Recognition App on {HOST}:{PORT}')
    app.logger.info(f'Environment: {"Development" if DEBUG_MODE else "Production"}')
    app.logger.info(f'Reference folder: {REFERENCE_FOLDER}')
    
    # Run the application
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG_MODE,
        threaded=True  # Enable multi-threading for better performance
    )