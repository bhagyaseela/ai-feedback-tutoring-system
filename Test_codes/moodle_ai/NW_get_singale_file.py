import mysql.connector
import os
import shutil

# ==========================================
# 1. CONFIGURATION (Updated with your details)
# ==========================================
DB_CONFIG = {
    'user': 'moodleuser',
    'password': 'moodlepass', 
    'host': 'localhost',
    'database': 'moodle_fyp',
}

# [!] IMPORTANT: Check your config.php for $CFG->dataroot
# If your dataroot is "D:/moodledata", write "D:/moodledata/filedir" here.
# Don't forget the "/filedir" at the end!
MOODLE_DATA_DIR = r"C:\xampp\moodledata\filedir" 

OUTPUT_DIR = "downloaded_submissions"
# ==========================================

def main():
    print("--- CONNECTING TO DATABASE ---")
    
    # 1. Connect
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        print("Database connection successful.")
    except Exception as e:
        print(f"\n[!] DATABASE ERROR: {e}")
        print("Double check if your WAMP/XAMPP SQL server is running.")
        return

    # 2. Find PDF Submissions
    print("Searching for PDF submissions...")
    query = """
    SELECT 
        f.contenthash,
        f.filename,
        f.userid,
        a.name AS assignment_name
    FROM mdl_files f
    JOIN mdl_context ctx ON f.contextid = ctx.id
    JOIN mdl_course_modules cm ON ctx.instanceid = cm.id
    JOIN mdl_assign a ON cm.instance = a.id
    WHERE f.filearea = 'submission_files'
      AND f.filename != '.'
      AND f.mimetype = 'application/pdf'
    """
    
    cursor.execute(query)
    files = cursor.fetchall()
    conn.close()

    if not files:
        print("No PDFs found in 'submission_files' area.")
        return

    print(f"Found {len(files)} files. Starting extraction...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 3. Copy Files
    count = 0
    for f in files:
        f_hash = f['contenthash']
        
        # Calculate Path: moodledata/filedir/01/b1/01b1...
        dir1 = f_hash[0:2]
        dir2 = f_hash[2:4]
        source_path = os.path.join(MOODLE_DATA_DIR, dir1, dir2, f_hash)
        
        # Create Output Name: AssignmentName_UserID.pdf
        safe_assign = "".join(x for x in f['assignment_name'] if x.isalnum())
        dest_name = f"{safe_assign}_User{f['userid']}_{f['filename']}"
        dest_path = os.path.join(OUTPUT_DIR, dest_name)

        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"[OK] Saved: {dest_name}")
            count += 1
        else:
            print(f"[ERROR] File missing on disk: {source_path}")
            print("       (Check your MOODLE_DATA_DIR path!)")

    print(f"\nDone. {count} files saved to folder: '{OUTPUT_DIR}'")

if __name__ == "__main__":
    main()