import requests
import pdfplumber
import io
import re

# ==========================================
# CONFIGURATION
# ==========================================
MOODLE_URL = "http://localhost/moodle_fyp" # Ensure this matches your browser URL exactly
TOKEN = "efe2d9ae2eb8592d995d2b26503c97bc"
ASSIGNMENT_ID = 1

# LOGIN CREDENTIALS (REQUIRED)
USERNAME = "admin"      
PASSWORD = "Password1*" 

API_URL = f"{MOODLE_URL}/webservice/rest/server.php"

# ==========================================
# STEP 1: GET SUBMISSIONS
# ==========================================
def get_submissions(assign_id):
    params = {
        'wstoken': TOKEN,
        'wsfunction': 'mod_assign_get_submissions',
        'moodlewsrestformat': 'json',
        'assignmentids[0]': assign_id
    }
    try:
        response = requests.post(API_URL, data=params)
        return response.json()
    except Exception as e:
        print(f"[API Error] {e}")
        return {}

# ==========================================
# STEP 2: DOWNLOAD PDF (Human Method)
# ==========================================
def download_with_session(file_url):
    print(f"  Attempting download via Session...")
    
    session = requests.Session()
    login_url = f"{MOODLE_URL}/login/index.php"
    
    try:
        # 1. Get Login Page to find the 'logintoken'
        login_page = session.get(login_url)
        
        # Find the hidden logintoken using regex (standard Moodle security)
        token_match = re.search(r'<input type="hidden" name="logintoken" value="(\w+)"', login_page.text)
        login_token = token_match.group(1) if token_match else ""

        # 2. Login
        payload = {
            'username': USERNAME,
            'password': PASSWORD,
            'logintoken': login_token  # <--- Crucial for modern Moodle
        }
        session.post(login_url, data=payload)
        
        # 3. FIX THE URL (The Magic Step)
        # Convert ".../webservice/pluginfile.php/..." to ".../pluginfile.php/..."
        # This makes Moodle treat us like a human browser user.
        human_url = file_url.replace("/webservice/pluginfile.php", "/pluginfile.php")
        
        # Remove any ?token= junk
        human_url = human_url.split('?')[0]
        
        print(f"  Downloading from: {human_url}")
        
        # 4. Download
        response = session.get(human_url)
        
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        else:
            print(f"  [Download Failed] Type: {response.headers.get('Content-Type')}")
            # If it failed, print a snippet to see if it's still an error message
            if 'application/json' in response.headers.get('Content-Type', ''):
                print(f"  Moodle Error: {response.text}")
            return ""
            
    except Exception as e:
        print(f"  [Session Error] {e}")
        return ""

# ==========================================
# STEP 3 & 4: ANALYZE & GRADE
# ==========================================
def run_ai_analysis(text):
    if not text: return 0, "Error reading file."
    
    # Simple Logic
    if len(text) < 50:
        return 40.0, "Submission too short. Please expand."
    elif "concept" in text.lower():
        return 85.0, "Great coverage of the core concepts!"
    else:
        return 60.0, "Good effort, but you missed the key 'concept'."

def post_grade(assign_id, user_id, grade, feedback):
    params = {
        'wstoken': TOKEN,
        'wsfunction': 'mod_assign_save_grade',
        'moodlewsrestformat': 'json',
        'assignmentid': assign_id,
        'userid': user_id,
        'grade': float(grade),
        'attemptnumber': -1,
        'addattempt': 0,
        'applytoall': 1,
        'plugindata[assignfeedbackcomments_editor][text]': feedback,
        'plugindata[assignfeedbackcomments_editor][format]': 1
    }
    requests.post(API_URL, data=params)
    print(f"  [Success] Grade {grade} saved for User {user_id}.")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("--- Starting AI Grader ---")
    data = get_submissions(ASSIGNMENT_ID)
    
    if 'assignments' in data:
        for sub in data['assignments'][0]['submissions']:
            if sub['status'] == 'submitted':
                user_id = sub['userid']
                print(f"\nProcessing User {user_id}...")
                
                if 'plugins' in sub:
                    # Find file
                    files = [p['fileareas'][0]['files'][0]['fileurl'] 
                             for p in sub['plugins'] 
                             if p['type'] == 'file' and p['fileareas'][0]['files']]
                    
                    if files:
                        text = download_with_session(files[0])
                        if text:
                            print(f"  Read {len(text)} chars.")
                            grade, fb = run_ai_analysis(text)
                            post_grade(ASSIGNMENT_ID, user_id, grade, fb)
                        else:
                            print("  Could not read PDF.")