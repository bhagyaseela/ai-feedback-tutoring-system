import os
import re
import html
import requests
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from PyPDF2 import PdfReader
import pdfplumber

MOODLE_URL = "http://localhost/moodle_fyp"
TOKEN = "b21263f9e0ba4e81e046f1da30e16f80"
ASSIGNMENT_ID = 3
COURSE_ID = 2
ASSIGNMENTS_DIR = "assignments"
SUBMISSIONS_DIR = "submissions"

def call_moodle(function_name: str, params: dict) -> dict:
    endpoint = f"{MOODLE_URL}/webservice/rest/server.php"
    base_params = {
        "wstoken": TOKEN,
        "wsfunction": function_name,
        "moodlewsrestformat": "json",
    }
    merged = {**base_params, **params}
    r = requests.post(endpoint, data=merged, timeout=60)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, dict) and data.get("exception"):
        raise RuntimeError(f"Moodle error: {data.get('message')} ({data.get('errorcode')})")

    return data


def add_token_to_fileurl(fileurl: str) -> str:
    parts = urlparse(fileurl)
    q = dict(parse_qsl(parts.query))
    q["token"] = TOKEN
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, urlencode(q), parts.fragment))


def safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")


def strip_html_to_text(html_string: str) -> str:
    """
    Very lightweight HTML -> text (no external libs).
    Good enough for most online text submissions.
    """
    if not html_string:
        return ""

    # Unescape entities (&nbsp; etc.)
    s = html.unescape(html_string)

    # Replace <br> and </p> with newlines for readability
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>", "\n", s)

    # Remove all remaining tags
    s = re.sub(r"<[^>]+>", "", s)

    # Clean excessive whitespace
    s = re.sub(r"\n\s*\n+", "\n\n", s).strip()
    return s


def extract_submission_files_and_text(submissions_json: dict):
    """
    Returns:
      files: list of file dicts
      texts: list of online-text dicts
    """
    files = []
    texts = []

    for assignment in submissions_json.get("assignments", []):
        for sub in assignment.get("submissions", []):
            userid = sub.get("userid")
            submissionid = sub.get("id")

            for plugin in sub.get("plugins", []):
                # 1) FILES
                for area in plugin.get("fileareas", []):
                    for f in area.get("files", []):
                        files.append({
                            "userid": userid,
                            "submissionid": submissionid,
                            "filename": f.get("filename"),
                            "fileurl": f.get("fileurl"),
                            "mimetype": f.get("mimetype"),
                        })

                # 2) ONLINE TEXT
                for ef in plugin.get("editorfields", []):
                    # Moodle commonly uses ef["text"] for online text (HTML)
                    # Some versions might use ef["content"]
                    name = ef.get("name") or "editorfield"
                    html_text = ef.get("text") or ef.get("content") or ""

                    if html_text and html_text.strip():
                        texts.append({
                            "userid": userid,
                            "submissionid": submissionid,
                            "fieldname": name,
                            "html": html_text,
                            "plain": strip_html_to_text(html_text)
                        })

    return files, texts


def download_file(url: str, out_path: str) -> None:
    dir_name = os.path.dirname(out_path)

    # Only create directory if path includes one
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as fp:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fp.write(chunk)



def preview_pdf_text(pdf_path: str, max_chars: int = 5000) -> str:
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
    text = "\n\n".join(parts).strip()

    if not text:
        return "(No extractable text - may be scanned/image PDF)"

    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text



def save_online_text(out_dir: str, user_id, submission_id, fieldname: str, html_text: str, plain_text: str):
    user_part = f"user_{user_id}" if user_id is not None else "user_unknown"
    sub_part = f"submission_{submission_id}" if submission_id is not None else "submission_unknown"

    base = os.path.join(out_dir, user_part, sub_part)
    os.makedirs(base, exist_ok=True)

    # Save HTML + plain text separately
    field_safe = safe_name(fieldname)

    html_path = os.path.join(base, f"{field_safe}.html")
    txt_path = os.path.join(base, f"{field_safe}.txt")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)
        
        
def save_submission_text(out_dir, student_id, assignment_id, content: str):
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{student_id}_{assignment_id}.txt"
    path = os.path.join(out_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved: {path}")
    
    
def save_student_submission_text(submissions_dir: str, student_id: int, course_id: int, assignment_id: int, content: str):
    os.makedirs(submissions_dir, exist_ok=True)
    filename = f"{student_id}_{course_id}_{assignment_id}.txt"
    path = os.path.join(submissions_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved submission: {path}")



def get_assignment_details(course_id: int, assignment_id: int) -> dict:
    data = call_moodle("mod_assign_get_assignments", {"courseids[0]": course_id})

    # data: {"courses":[{"id":..,"assignments":[...]}]}
    for course in data.get("courses", []):
        for a in course.get("assignments", []):
            if a.get("id") == assignment_id:
                return a

    raise RuntimeError(f"Assignment id {assignment_id} not found in course {course_id}")

def extract_assignment_files(assignment_obj: dict) -> list[dict]:
    files = []
    for key in ("introfiles", "introattachments"):
        for f in assignment_obj.get(key, []) or []:
            files.append({
                "filename": f.get("filename"),
                "fileurl": f.get("fileurl"),
                "mimetype": f.get("mimetype", ""),
                "source": key
            })
    return files


def save_assignment_master(assignments_dir: str, course_id: int, assignment_id: int, content: str) -> str:
    os.makedirs(assignments_dir, exist_ok=True)
    path = os.path.join(assignments_dir, f"{course_id}_{assignment_id}.txt")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved assignment: {path}")
    return path



def main():
    # 1) Get assignment metadata
    assignment = get_assignment_details(COURSE_ID, ASSIGNMENT_ID)

    assign_name = assignment.get("name", "")
    intro_html = assignment.get("intro", "")  # description/instructions often stored here (HTML)
    intro_text = strip_html_to_text(intro_html)

    activity_instructions = assignment.get("activity", "") or assignment.get("instructions", "")
    # Not always present depending on Moodle version; intro usually has the main text.

    # 2) Create assignment folder + prepare master content
    master_sections = []
    master_sections.append(f"COURSE ID: {COURSE_ID}")
    master_sections.append(f"ASSIGNMENT ID: {ASSIGNMENT_ID}")
    master_sections.append(f"ASSIGNMENT NAME: {assign_name}\n")

    master_sections.append("=== DESCRIPTION / INSTRUCTIONS (FROM INTRO) ===")
    master_sections.append(intro_text if intro_text else "(No intro text found)")

    if activity_instructions:
        master_sections.append("\n=== ACTIVITY INSTRUCTIONS ===")
        master_sections.append(strip_html_to_text(activity_instructions))

    # 3) Download + extract text from assignment additional/intro files (PDFs)
    assignment_files = extract_assignment_files(assignment)
    if assignment_files:
        master_sections.append("\n=== ASSIGNMENT ADDITIONAL FILES (EXTRACTED TEXT) ===")

        for af in assignment_files:
            fname = af["filename"] or "file"
            furl = af["fileurl"]
            mm = (af["mimetype"] or "").lower()

            master_sections.append(f"\n--- File: {fname} (from {af['source']}) ---")

            if not furl:
                master_sections.append("(No fileurl)")
                continue

            is_pdf = ("pdf" in mm) or fname.lower().endswith(".pdf")
            if not is_pdf:
                master_sections.append("(Skipped: not a PDF)")
                continue

            tmp = f"tmp_assignment_{safe_name(fname)}"
            token_url = add_token_to_fileurl(furl)
            download_file(token_url, tmp)

            try:
                txt = preview_pdf_text(tmp, max_chars=30000)
                master_sections.append(txt)
            except Exception as e:
                master_sections.append(f"(Failed to extract PDF text: {e})")
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
    else:
        master_sections.append("\n=== ASSIGNMENT ADDITIONAL FILES ===\n(None found)")

    master_text = "\n".join(master_sections)

    # 4) Save assignment master file + get assignment folder path
    save_assignment_master(ASSIGNMENTS_DIR, COURSE_ID, ASSIGNMENT_ID, master_text)


    # 5) Fetch submissions
    submissions = call_moodle("mod_assign_get_submissions", {"assignmentids[0]": ASSIGNMENT_ID})
    files, texts = extract_submission_files_and_text(submissions)

    # 6) Group per (userid, submissionid)
    submission_map = {}

    # Online text
    for t in texts:
        key = (t["userid"], t["submissionid"])
        submission_map.setdefault(key, [])
        submission_map[key].append("=== ONLINE TEXT SUBMISSION ===\n" + t["plain"] + "\n")

    # PDF text from student uploads
    for f in files:
        filename = f["filename"] or ""
        mimetype = (f["mimetype"] or "").lower()
        is_pdf = ("pdf" in mimetype) or filename.lower().endswith(".pdf")
        if not is_pdf or not f["fileurl"]:
            continue

        key = (f["userid"], f["submissionid"])
        submission_map.setdefault(key, [])

        token_url = add_token_to_fileurl(f["fileurl"])
        temp_pdf = f"temp_{f['userid']}_{f['submissionid']}_{safe_name(filename)}"
        download_file(token_url, temp_pdf)

        try:
            pdf_text = preview_pdf_text(temp_pdf, max_chars=30000)
        except Exception:
            pdf_text = "(PDF text extraction failed)"
        finally:
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)

        submission_map[key].append("=== PDF SUBMISSION TEXT ===\n" + pdf_text + "\n")

    # 7) Save one txt per student using <studentid>_<assignmentid>.txt in assignment folder
    for (student_id, submission_id), parts in submission_map.items():
        final_text = (
            f"STUDENT ID: {student_id}\n"
            f"ASSIGNMENT ID: {ASSIGNMENT_ID}\n"
            f"SUBMISSION ID: {submission_id}\n\n"
            + "\n".join(parts)
        )
        save_student_submission_text(
            SUBMISSIONS_DIR,
            student_id,
            COURSE_ID,
            ASSIGNMENT_ID,
            final_text
        )


    print("\nAll processed.")


if __name__ == "__main__":
    main()
