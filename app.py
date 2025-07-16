from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pypdf as PyPDF2
from langdetect import detect
from googletrans import Translator
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import time
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

SUPPORTED_LANGUAGES = {
    'de': 'German', 'fi': 'Finnish', 'es': 'Spanish',
    'hi': 'Hindi', 'fr': 'French', 'it': 'Italian'
}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    chats = db.relationship('Chat', backref='author', lazy=True)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_language = db.Column(db.String(20), nullable=False)
    translated_filename = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"Error extracting text: {e}")
    return text

def detect_language(text):
    try:
        lang = detect(text[:1000]) if text else None
        return lang if lang in SUPPORTED_LANGUAGES else None
    except:
        return None

def translate_text(text, src_lang):
    translator = Translator()
    try:
        if len(text) > 5000:
            chunks = [text[i:i+5000] for i in range(0, len(text), 5000)]
            return " ".join([translator.translate(chunk, src=src_lang, dest='en').text for chunk in chunks])
        return translator.translate(text, src=src_lang, dest='en').text
    except Exception as e:
        print(f"Translation error: {e}")
        return None

def create_translated_pdf(text, filename):
    timestamp = str(int(time.time()))
    output_filename = f"translated_{timestamp}_{filename}"
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], output_filename)
    
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    y_position = height - 40
    
    for line in text.split('\n'):
        if y_position < 40:
            c.showPage()
            y_position = height - 40
        c.drawString(40, y_position, line)
        y_position -= 15
    c.save()
    return output_filename

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('chat'))
        flash('Login unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            text = extract_text_from_pdf(filepath)
            if not text:
                return jsonify({'error': 'Could not extract text'}), 400
            
            lang = detect_language(text)
            if not lang or lang not in SUPPORTED_LANGUAGES:
                return jsonify({'error': 'Unsupported language'}), 400
            
            translated_text = translate_text(text, lang)
            if not translated_text:
                return jsonify({'error': 'Translation failed'}), 500
            
            translated_filename = create_translated_pdf(translated_text, filename)
            
            chat = Chat(
                original_language=SUPPORTED_LANGUAGES[lang],
                translated_filename=translated_filename,
                user_id=current_user.id
            )
            db.session.add(chat)
            db.session.commit()
            
            return jsonify({
                'message': 'File processed',
                'original_language': SUPPORTED_LANGUAGES[lang],
                'translated_text': translated_text[:500] + '...' if len(translated_text) > 500 else translated_text,
                'translated_filename': translated_filename
            })
    
    return render_template('chat.html')

@app.route('/batch_upload', methods=['POST'])
@login_required
def batch_upload():
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No selected files'}), 400
    
    results = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            text = extract_text_from_pdf(filepath)
            if not text:
                results.append({'filename': filename, 'status': 'failed', 'error': 'Text extraction failed'})
                continue
            
            lang = detect_language(text)
            if not lang or lang not in SUPPORTED_LANGUAGES:
                results.append({'filename': filename, 'status': 'failed', 'error': 'Unsupported language'})
                continue
            
            translated_text = translate_text(text, lang)
            if not translated_text:
                results.append({'filename': filename, 'status': 'failed', 'error': 'Translation failed'})
                continue
            
            translated_filename = create_translated_pdf(translated_text, filename)
            
            chat = Chat(
                original_language=SUPPORTED_LANGUAGES[lang],
                translated_filename=translated_filename,
                user_id=current_user.id
            )
            db.session.add(chat)
            
            results.append({
                'filename': filename,
                'status': 'success',
                'original_language': SUPPORTED_LANGUAGES[lang],
                'translated_filename': translated_filename
            })
    
    db.session.commit()
    return jsonify({'results': results})

@app.route('/history')
@login_required
def history():
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.date_posted.desc()).all()
    return render_template('history.html', chats=chats)

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)