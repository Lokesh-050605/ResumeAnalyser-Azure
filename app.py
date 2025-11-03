import os
import json
import tempfile
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename
from models import db, User, Resume
from blob_storage import BlobStorageClient
from parser import ResumeParser
from ai_client import GeminiClient
from utils import login_required
import config

app = Flask(__name__)
app.config.from_object(config)

# Initialize database
db.init_app(app)

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Initialize clients
blob_client = BlobStorageClient(
    connection_string=app.config['AZURE_STORAGE_CONNECTION_STRING'],
    container_name=app.config['AZURE_CONTAINER_NAME']
)
resume_parser = ResumeParser()
gemini_client = GeminiClient(api_key=app.config['GOOGLE_API_KEY'])

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/callback')
def callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            return "Failed to get user info", 400
        
        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Create new user
            user = User(
                email=user_info['email'],
                name=user_info.get('name', ''),
                picture=user_info.get('picture', '')
            )
            db.session.add(user)
            db.session.commit()
        
        # Store user in session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        session['user_picture'] = user.picture
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"OAuth error: {e}")
        return f"Authentication failed: {str(e)}", 400

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).all()
    return render_template('dashboard.html', resumes=resumes)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF and DOCX allowed'}), 400
        
        # Secure filename
        filename = secure_filename(file.filename)
        user_id = session.get('user_id')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        blob_name = f"user_{user_id}/{timestamp}_{filename}"
        
        # Read file content
        file_content = file.read()
        
        # Upload to Azure Blob Storage
        blob_url = blob_client.upload_file(blob_name, file_content)
        
        # Save to database
        resume = Resume(
            user_id=user_id,
            filename=filename,
            blob_path=blob_name,
            blob_url=blob_url
        )
        db.session.add(resume)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'resume_id': resume.id,
            'filename': filename,
            'message': 'File uploaded successfully'
        }), 201
    
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/files', methods=['GET'])
@login_required
def list_files():
    user_id = session.get('user_id')
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).all()
    
    return jsonify({
        'files': [{
            'id': r.id,
            'filename': r.filename,
            'uploaded_at': r.uploaded_at.isoformat(),
            'analyzed': r.analysis is not None
        } for r in resumes]
    })

@app.route('/analyze/<int:resume_id>', methods=['POST'])
@login_required
def analyze(resume_id):
    try:
        user_id = session.get('user_id')
        resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Get job description from request (optional)
        job_description = request.json.get('job_description', '') if request.is_json else ''
        
        # Download file from blob storage
        file_content = blob_client.download_file(resume.blob_path)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(resume.filename)[1]) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Parse resume
            resume_text = resume_parser.parse(tmp_file_path)
            
            # Analyze with Gemini
            analysis = gemini_client.analyze_resume(resume_text, job_description)
            
            # Save analysis to database
            resume.analysis = json.dumps(analysis)
            resume.analyzed_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
        
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    
    except Exception as e:
        print(f"Analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analysis/<int:resume_id>', methods=['GET'])
@login_required
def get_analysis(resume_id):
    user_id = session.get('user_id')
    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    
    if not resume:
        return jsonify({'error': 'Resume not found'}), 404
    
    if not resume.analysis:
        return jsonify({'error': 'Resume not analyzed yet'}), 404
    
    return jsonify({
        'resume_id': resume.id,
        'filename': resume.filename,
        'uploaded_at': resume.uploaded_at.isoformat(),
        'analyzed_at': resume.analyzed_at.isoformat() if resume.analyzed_at else None,
        'analysis': json.loads(resume.analysis)
    })

@app.route('/analysis/view/<int:resume_id>')
@login_required
def view_analysis(resume_id):
    """Render the analysis page for a specific resume ID"""
    return render_template('analysis.html', resume_id=resume_id)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)