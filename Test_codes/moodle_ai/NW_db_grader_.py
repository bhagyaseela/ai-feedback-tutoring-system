import mysql.connector
import os
import shutil

# --- CONFIGURATION ---
# 1. Database Credentials (from your config.php or Workbench)
DB_CONFIG = {
    'user': 'root',           # Default for XAMPP is 'root'
    'password': 'MysqlBps135790%',           # Default for XAMPP is empty
    'host': 'localhost',
    'database': 'moodle_fyp', # Your database name
}

# 2. Path to your moodledata/filedir folder (CRITICAL STEP)
# IMPORTANT: Use forward slashes '/' even on Windows
MOODLE_DATA_DIR = "C:/xampp/moodledata/filedir" 

ASSIGNMENT_ID = 1
OUTPUT_DIR = "db_downloads"

def get_submission_files():
    """Queries DB for filenames and their content hashes."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    query = """
    SELECT 
        f.contenthash,
        f.filename,
        f.userid,
        u.firstname,
        u.lastname
    FROM mdl_files f
    JOIN mdl_context ctx ON f.contextid = ctx.id
    JOIN mdl_course_modules cm ON ctx.instanceid = cm.id
    JOIN mdl_assign a ON cm.instance = a.id
    JOIN mdl_user u ON f.userid = u.id
    WHERE a.id = %s
      AND f.component = 'mod_assign'
      AND f.filearea = 'submission_files'
      AND f.filename != '.'
    """
    
    cursor.execute(query, (ASSIGNMENT_ID,))
    results = cursor.fetchall()
    conn.close()
    return results

def copy_from_storage(contenthash, dest_filename):
    """
    Locates the file in moodledata based on hash logic and copies it.
    Moodle Logic: Hash 'abcdef...' is stored in moodledata/filedir/ab/cd/abcdef...
    """
    if not contenthash:
        return False
        
    # Moodle storage logic
    dir1 = contenthash[0:2]  # First 2 chars
    dir2 = contenthash[2:4]  # Next 2 chars
    
    # Construct full source path
    source_path = os.path.join(MOODLE_DATA_DIR, dir1, dir2, contenthash)
    
    if os.path.exists(source_path):
        shutil.copy2(source_path, dest_filename)
        return True
    else:
        print(f"ERROR: Physical file missing at {source_path}")
        return False

def main():
    print("--- Direct Database File Fetcher ---")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    files = get_submission_files()
    print(f"Found {len(files)} files in Database for Assignment {ASSIGNMENT_ID}")
    
    for f in files:
        # Construct a nice filename: UserID_Name_Filename.pdf
        safe_name = f"{f['userid']}_{f['firstname']}_{f['filename']}"
        dest_path = os.path.join(OUTPUT_DIR, safe_name)
        
        print(f"Processing: {safe_name}")
        print(f" -> Hash: {f['contenthash']}")
        
        success = copy_from_storage(f['contenthash'], dest_path)
        
        if success:
            print(" -> [OK] Copied successfully.")
        else:
            print(" -> [FAIL] Could not find file in moodledata.")

if __name__ == "__main__":
    main()