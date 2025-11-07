from flask import render_template
from flask import Flask, request, jsonify, make_response, session, redirect, url_for
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime
from io import StringIO
from difflib import SequenceMatcher
import re
from functools import wraps

app = Flask(__name__)
app.secret_key = 'keeplearning_hub_secret_2025'  # Secret key for session management

# Get the application directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'docx', 'txt'}
RESULTS_FILE = os.path.join(APP_DIR, 'exam_results.json')

# Library folder and metadata
LIBRARY_FOLDER = os.path.join(APP_DIR, 'library_docs')
LIBRARY_META_FOLDER = os.path.join(LIBRARY_FOLDER, 'meta')
if not os.path.exists(LIBRARY_FOLDER):
    os.makedirs(LIBRARY_FOLDER)
if not os.path.exists(LIBRARY_META_FOLDER):
    os.makedirs(LIBRARY_META_FOLDER)

# Store current exam session in memory
exam_session = {}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        data = request.json
        username = data.get('username', '')
        password = data.get('password', '')
        
        # Check credentials
        if username == 'keeplearninghub' and password == 'keepsleeping':
            session['logged_in'] = True
            session['username'] = username
            return jsonify({'success': True, 'message': 'Login successful'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# Serve the about page
@app.route('/about')
@login_required
def about_page():
    return render_template('about.html')

# Serve the results page (loads saved results)
@app.route('/results')
@login_required
def results_page():
    results = []
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, 'r') as f:
                results = json.load(f)
        except Exception as e:
            print(f"Error reading results file: {e}")
    return render_template('results.html', results=results)

# Redirect root URL to /exams
@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login_page'))
    return render_template('exams.html')

# Serve the exams page (after app is defined)
@app.route('/exams')
@login_required
def exams_page():
    return render_template('exams.html')

# Serve the dedicated exam page 
@app.route('/exam')
@login_required
def exam_page():
    return render_template('exam.html')

    # Serve the library page
@app.route('/library')
@login_required
def library_page():
    return render_template('library.html')

# Get exam data (questions extracted from uploaded document)
@app.route('/exam/data', methods=['GET'])
def get_exam_data():
    global exam_session
    if not exam_session or 'questions' not in exam_session:
        return jsonify({'error': 'No exam data available'}), 400
    return jsonify(exam_session), 200

# Function to check similarity between answers
def calculate_similarity(user_answer, correct_answer):
    """
    Calculate similarity between user answer and correct answer.
    Uses SequenceMatcher for fuzzy matching.
    Returns a score between 0 and 1.
    """
    if not user_answer or not correct_answer:
        return 1.0 if user_answer == correct_answer else 0.0
    
    # Normalize both strings
    user_ans = user_answer.strip().lower()
    correct_ans = correct_answer.strip().lower()
    
    # Exact match gets 1.0
    if user_ans == correct_ans:
        return 1.0
    
    # Extract key words (remove common stop words)
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                  'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
                  'by', 'from', 'it', 'as', 'that', 'this', 'which', 'who'}
    
    user_words = set(re.findall(r'\w+', user_ans)) - stop_words
    correct_words = set(re.findall(r'\w+', correct_ans)) - stop_words
    
    # If both have words, check keyword overlap
    if user_words and correct_words:
        # Calculate Jaccard similarity for keywords
        intersection = len(user_words & correct_words)
        union = len(user_words | correct_words)
        keyword_similarity = intersection / union if union > 0 else 0
    else:
        keyword_similarity = 0
    
    # Use SequenceMatcher for string similarity
    sequence_similarity = SequenceMatcher(None, user_ans, correct_ans).ratio()
    
    # Weighted average: 60% keyword match, 40% sequence match
    final_similarity = (keyword_similarity * 0.6) + (sequence_similarity * 0.4)
    
    return final_similarity

# Submit exam and score answers
@app.route('/exam/submit', methods=['POST'])
def submit_exam():
    data = request.json
    print(f"Submit received: {data}")  # DEBUG
    if not data or 'questions' not in data:
        return jsonify({'error': 'Invalid exam data'}), 400
    
    questions = data['questions']
    answers = data.get('answers', {})
    
    score = 0
    total = len(questions)
    
    for q in questions:
        q_id = f"q{q['id']}"
        user_answer = answers.get(q_id, '').strip()
        correct_answer = (q.get('correct_answer', '') or '').strip()

        # Enforce 5000 character limit for descriptive/fill_blank
        q_type = q.get('type', 'mcq')
        if q_type in ['descriptive', 'fill_blank'] and len(user_answer) > 5000:
            user_answer = user_answer[:5000]

        if q_type == 'mcq' or q_type == 'true_false':
            threshold = 0.95
        elif q_type == 'fill_blank':
            threshold = 0.85
        else:
            threshold = 0.70  # descriptive

        if not user_answer:
            # Empty answer gets 0 points
            continue

        # Score answer
        similarity = calculate_similarity(user_answer, correct_answer)
        if similarity >= threshold:
            score += 1
    
    result = {
        'score': score,
        'total': total,
        'percentage': round((score / total) * 100, 2) if total > 0 else 0,
        'timestamp': datetime.now().isoformat(),
        'student_name': data.get('student_name', 'Unknown'),
        'started_at': data.get('started_at'),
        'submitted_at': data.get('submitted_at'),
        'questions': questions,
        'answers': answers
    }
    print(f"Result created: {result}")  # DEBUG
    
    # Save result to results file
    try:
        print(f"Saving to {RESULTS_FILE}")  # DEBUG
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r') as f:
                all_results = json.load(f)
        else:
            all_results = []
        all_results.append(result)
        with open(RESULTS_FILE, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"Saved successfully. Total results: {len(all_results)}")  # DEBUG
    except Exception as e:
        print(f"Error saving results: {e}")
    
    return jsonify(result), 200

# Download results as JSON file
@app.route('/download/results', methods=['GET'])
def download_results():
    format_type = request.args.get('format', 'json').lower()
    
    if not os.path.exists(RESULTS_FILE):
        return jsonify({'error': 'No results file found'}), 404
    
    try:
        with open(RESULTS_FILE, 'r') as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error reading results file: {e}")
        return jsonify({'error': 'Error reading results'}), 500
    
    if not results:
        return jsonify({'error': 'No results available'}), 404
    
    if format_type == 'csv':
        # Generate CSV
        output = StringIO()
        output.write("Student Name,Score,Total,Percentage,Started,Submitted,Duration\n")
        
        for r in results:
            try:
                started = datetime.fromisoformat(r.get('started_at', '')).strftime('%b %d, %Y, %H:%M:%S %p')
                submitted = datetime.fromisoformat(r.get('submitted_at', r.get('timestamp', ''))).strftime('%b %d, %Y, %H:%M:%S %p')
                
                # Calculate duration
                if r.get('started_at') and r.get('submitted_at'):
                    start = datetime.fromisoformat(r['started_at'])
                    end = datetime.fromisoformat(r['submitted_at'])
                    duration = end - start
                    minutes = duration.total_seconds() // 60
                    seconds = int(duration.total_seconds() % 60)
                    duration_str = f"{int(minutes)}m {seconds}s"
                else:
                    duration_str = "N/A"
                
                output.write(f'"{r.get("student_name", "Unknown")}",{r.get("score", 0)},{r.get("total", 0)},{r.get("percentage", 0)}%,"{started}","{submitted}","{duration_str}"\n')
            except Exception as e:
                print(f"Error processing result: {e}")
        
        csv_data = output.getvalue()
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = f'attachment; filename=exam_results_{datetime.now().strftime("%Y-%m-%d")}.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    
    else:  # JSON format (default)
        response = make_response(json.dumps(results, indent=2))
        response.headers['Content-Disposition'] = f'attachment; filename=exam_results_{datetime.now().strftime("%Y-%m-%d")}.json'
        response.headers['Content-Type'] = 'application/json'
        return response

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Library Upload Endpoint ---
@app.route('/library/upload', methods=['POST'])
@login_required
def library_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(LIBRARY_FOLDER, filename)
        file.save(filepath)
        # Extract questions
        try:
            questions = extract_questions(filepath)
            # Save metadata
            meta_path = os.path.join(LIBRARY_META_FOLDER, filename + '.json')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({'filename': filename, 'questions': questions, 'uploaded_at': datetime.now().isoformat()}, f, indent=2)
            return jsonify({'message': 'Library file uploaded', 'filename': filename, 'questions': questions}), 200
        except Exception as e:
            return jsonify({'error': f'Extraction failed: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type'}), 400

# --- List Library Documents Endpoint ---
@app.route('/library/list', methods=['GET'])
@login_required
def library_list():
    docs = []
    for meta_file in os.listdir(LIBRARY_META_FOLDER):
        if meta_file.endswith('.json'):
            meta_path = os.path.join(LIBRARY_META_FOLDER, meta_file)
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                docs.append(meta)
            except Exception as e:
                continue
    return jsonify({'library': docs}), 200

# --- Set Exam from Library ---
@app.route('/library/set-exam', methods=['POST'])
@login_required
def library_set_exam():
    global exam_session
    data = request.json
    if not data or 'questions' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    exam_session = {'questions': data['questions'], 'answers': {}}
    return jsonify({'message': 'Exam loaded from library'}), 200

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    global exam_session
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Extraction logic
        try:
            extracted_data = extract_questions(filepath)
            print(f"Successfully extracted {len(extracted_data)} questions")
            # Store in session for exam page
            exam_session = {'questions': extracted_data, 'answers': {}}
            return jsonify({'message': 'File uploaded successfully', 'filename': filename, 'questions': extracted_data}), 200
        except Exception as e:
            print(f"ERROR during extraction: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Extraction failed: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type'}), 400

def extract_questions(filepath):
    import re
    
    # Read file
    if filepath.endswith('.docx'):
        from docx import Document
        doc = Document(filepath)
        text = '\n'.join([para.text for para in doc.paragraphs])
    elif filepath.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        return []
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    
    # Find all Answer: positions
    answer_matches = list(re.finditer(r'Answer\s*[\:\-]\s*', text, re.IGNORECASE))
    
    if not answer_matches:
        return []
    
    processed = []
    
    for idx, ans_match in enumerate(answer_matches):
        # Extract the answer text
        answer_start_pos = ans_match.end()
        
        # Answer ends at the next newline or start of next answer
        next_answer_start = answer_matches[idx + 1].start() if idx + 1 < len(answer_matches) else len(text)
        answer_text = text[answer_start_pos:next_answer_start].split('\n')[0].strip()
        
        # Now find the question text
        # Question starts after the PREVIOUS answer ends
        if idx > 0:
            q_start_pos = answer_matches[idx - 1].end()
            # Skip to after first newline to avoid picking up previous answer
            q_start_pos = text.find('\n', q_start_pos) + 1
        else:
            q_start_pos = 0
        
        q_end_pos = ans_match.start()
        q_block = text[q_start_pos:q_end_pos].strip()
        
        if not q_block or len(q_block) < 3:
            continue
        
        q_id = idx + 1
        print(f"Q{q_id}: {q_block[:70].replace(chr(10), ' ')}...")
        
        # ===== MCQ DETECTION =====
        mcq_pattern = r'^([A-D][\.\)]\s+.+?)$'
        mcq_lines = re.findall(mcq_pattern, q_block, re.MULTILINE)
        
        if len(mcq_lines) >= 2:
            print(f"  Type: MCQ ({len(mcq_lines)} options)")
            
            # Extract options text
            options_text = []
            for line in mcq_lines:
                opt_text = re.sub(r'^[A-D][\.\)]\s+', '', line).strip()
                options_text.append(opt_text)
            
            # Find answer letter
            ans_match_letter = re.search(r'^([A-D])', answer_text, re.I)
            answer_letter = ans_match_letter.group(1).upper() if ans_match_letter else None
            
            # Map letter to option text
            correct_answer = answer_letter
            if answer_letter:
                idx_letter = ord(answer_letter) - ord('A')
                if 0 <= idx_letter < len(options_text):
                    correct_answer = options_text[idx_letter]
            
            processed.append({
                'id': q_id,
                'question': q_block,
                'type': 'mcq',
                'options': options_text,
                'correct_answer': correct_answer
            })
        
        # ===== TRUE/FALSE DETECTION =====
        elif re.search(r'True or False', q_block, re.I):
            print(f"  Type: True/False")
            
            correct_answer = answer_text if answer_text in ['True', 'False'] else 'True'
            
            processed.append({
                'id': q_id,
                'question': q_block,
                'type': 'true_false',
                'correct_answer': correct_answer
            })
        
        # ===== FILL-IN-THE-BLANK DETECTION =====
        elif '__' in q_block or '_____' in q_block or '________' in q_block or re.search(r'_+', q_block):
            print(f"  Type: Fill-blank")
            
            processed.append({
                'id': q_id,
                'question': q_block,
                'type': 'fill_blank',
                'correct_answer': answer_text
            })
        
        # ===== DESCRIPTIVE/SHORT ANSWER =====
        else:
            print(f"  Type: Descriptive/SQL")
            
            processed.append({
                'id': q_id,
                'question': q_block,
                'type': 'descriptive',
                'correct_answer': answer_text
            })
    
    print(f"\n✓ Total extracted: {len(processed)} questions\n")
    return processed

@app.route('/clear_results', methods=['POST'])
def clear_results():
    import os
    results_path = os.path.join(os.path.dirname(__file__), 'exam_results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        f.write('[]')
    return redirect(url_for('results_page'))

if __name__ == '__main__':
    app.run(debug=True)
