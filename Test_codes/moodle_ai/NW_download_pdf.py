import requests
import os

# --- CONFIGURATION ---
MOODLE_URL = "http://localhost/moodle_fyp" # No trailing slash
TOKEN = "312c5d2bdde9b8a03201ae02867a25f3"
ASSIGNMENT_ID = 1  # The specific assignment ID (mdl_assign.id)
SAVE_FOLDER = "./downloads"

# Ensure download directory exists
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

def get_submissions():
    """Fetch all submissions for the specific assignment."""
    endpoint = f"{MOODLE_URL}/webservice/rest/server.php"
    
    params = {
        "wstoken": TOKEN,
        "wsfunction": "mod_assign_get_submissions",
        "moodlewsrestformat": "json",
        "assignmentids[0]": ASSIGNMENT_ID
    }

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Moodle: {e}")
        return None

def download_file(file_url, file_name):
    """Download the file using the token for authentication."""
    # Moodle file URLs require the token appended to bypass login
    download_url = f"{file_url}?token={TOKEN}"
    
    path = os.path.join(SAVE_FOLDER, file_name)
    
    print(f"Downloading {file_name}...")
    
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    print(f"Saved to {path}")

def main():
    data = get_submissions()
    
    # 1. Basic Validation
    if not data or 'assignments' not in data:
        print("No data returned.")
        return

    # 2. Process Assignments
    for assignment in data['assignments']:
        # FIX 1: Use 'assignmentid' instead of 'id'
        aid = assignment.get('assignmentid') 
        print(f"Processing Assignment ID: {aid}")
        
        # Check if there are submissions
        if 'submissions' not in assignment:
            print(f"  > No submissions found.")
            continue

        for submission in assignment['submissions']:
            user_id = submission['userid']
            status = submission['status']
            
            # Optional: Skip students who haven't submitted anything
            if status == 'new':
                continue

            print(f"  > Checking User {user_id} (Status: {status})")

            # Look inside plugins to find the 'file' area
            for plugin in submission.get('plugins', []):
                if plugin['type'] == 'file':
                    for filearea in plugin.get('fileareas', []):
                        if filearea['area'] == 'submission_files':
                            
                            for file in filearea.get('files', []):
                                # Identify PDF files
                                if file['mimetype'] == 'application/pdf':
                                    # Create a unique filename
                                    filename = f"User_{user_id}_{file['filename']}"
                                    
                                    # Download
                                    download_file(file['fileurl'], filename)