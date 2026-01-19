import requests
import json
import os
from pypdf import PdfReader  # <--- NEW IMPORT

# --- CONFIGURATION ---
MOODLE_URL = "http://localhost/moodle_fyp"
TOKEN = "3a48be7638a93e26ab49bf10b170a9da"
ASSIGNMENT_ID = 1  # Updated to the working ID
DOWNLOAD_DIR = "submissions"

# --- HELPER FUNCTIONS ---

def get_submissions(assign_id):
    endpoint = f"{MOODLE_URL}/webservice/rest/server.php"
    params = {
        "wstoken": TOKEN,
        "wsfunction": "mod_assign_get_submissions",
        "moodlewsrestformat": "json",
        "assignmentids[0]": assign_id
    }
    response = requests.get(endpoint, params=params)
    response.raise_for_status()
    return response.json()

def download_file(file_url, dest_path):
    # 1. FIX THE URL for Web Service Access
    # Change '.../pluginfile.php/...' to '.../webservice/pluginfile.php/...'
    if '/pluginfile.php/' in file_url and '/webservice/pluginfile.php/' not in file_url:
        download_url = file_url.replace('/pluginfile.php/', '/webservice/pluginfile.php/')
    else:
        download_url = file_url

    # 2. Append Token
    if '?' in download_url:
        download_url = f"{download_url}&token={TOKEN}"
    else:
        download_url = f"{download_url}?token={TOKEN}"
    
    print(f"DEBUG: Downloading from: {download_url}")

    # 3. Perform Download
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        first_chunk = next(r.iter_content(chunk_size=1024))
        
        # Validation
        if not first_chunk.startswith(b'%PDF'):
            print(f"\n[!] ERROR: Server rejected token. Response:\n{first_chunk.decode('utf-8')}")
            return False

        with open(dest_path, 'wb') as f:
            f.write(first_chunk)
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                
    return True


def read_pdf_text(filepath):
    """
    Extracts and prints text from the PDF to the terminal.
    """
    print(f"\n{'='*20} CONTENT START {'='*20}")
    try:
        reader = PdfReader(filepath)
        text_found = False
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_found = True
                print(f"\n--- Page {i+1} ---")
                print(text.strip())
        
        if not text_found:
            print("\n[!] WARNING: No text found. This might be a scanned image/photo.")
            
    except Exception as e:
        print(f"[!] Error reading PDF: {e}")
        
    print(f"\n{'='*20} CONTENT END {'='*20}\n")

# --- MAIN WORKFLOW ---

def main():
    print(f"--- Fetching submissions for Assignment ID: {ASSIGNMENT_ID} ---")
    data = get_submissions(ASSIGNMENT_ID)

    if 'exception' in data:
        print(f"API Error: {data['message']}")
        return

    if not data.get('assignments'):
        print("No assignment found.")
        return

    submissions = data['assignments'][0]['submissions']
    active_submissions = [s for s in submissions if s['status'] == 'submitted']
    
    print(f"Found {len(active_submissions)} active submissions.\n")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    grades = []

    for sub in active_submissions:
        user_id = sub['userid']
        print(f"PROCESSING STUDENT ID: {user_id}")
        
        file_plugin = next((p for p in sub['plugins'] if p['type'] == 'file'), None)
        if not file_plugin or not file_plugin.get('fileareas'):
            print("No file submission found.")
            continue
            
        file_info = file_plugin['fileareas'][0]['files'][0]
        file_url = file_info['fileurl']
        filename = f"{user_id}_{file_info['filename']}"
        save_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # 1. Download
        if not os.path.exists(save_path):
            print(f"Downloading {filename}...")
            download_file(file_url, save_path)
        else:
            print(f"File {filename} already exists. Reading local copy...")
        
        # 2. Read Text to Terminal
        read_pdf_text(save_path)
        
        # 3. Grade
        grade = input(f"Enter Grade for Student {user_id} (0-100): ")
        comment = input(f"Enter Feedback: ")
        
        grades.append({
            "userid": user_id,
            "grade": grade,
            "feedback": comment
        })
        print("-" * 50)

    # Save grades locally
    with open("final_grades.json", "w") as f:
        json.dump(grades, f, indent=4)
        
    print("\nGrading complete. Results saved to final_grades.json")

if __name__ == "__main__":
    main()