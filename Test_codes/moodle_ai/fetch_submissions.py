import os
import re
import requests
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from PyPDF2 import PdfReader

MOODLE_URL = "http://localhost/moodle_fyp"   # no trailing slash is fine
TOKEN = "b21263f9e0ba4e81e046f1da30e16f80"
ASSIGNMENT_ID = 3

OUT_DIR = "submissions"


def call_moodle(function_name: str, params: dict) -> dict:
    """Call Moodle REST API (POST)."""
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

    # Moodle errors often come back as JSON with 'exception'
    if isinstance(data, dict) and data.get("exception"):
        raise RuntimeError(f"Moodle error: {data.get('message')} ({data.get('errorcode')})")

    return data


def add_token_to_fileurl(fileurl: str) -> str:
    """
    Moodle fileurl usually points to pluginfile.php and needs token query param.
    We'll append token safely even if query already exists.
    """
    parts = urlparse(fileurl)
    q = dict(parse_qsl(parts.query))
    q["token"] = TOKEN
    # optional: force download
    # q["forcedownload"] = "1"
    new_query = urlencode(q)
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))


def safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")


def extract_all_files(submissions_json: dict) -> list[dict]:
    """
    Returns a list of file dicts:
      {
        'userid': int,
        'submissionid': int,
        'filename': str,
        'fileurl': str,
        'mimetype': str
      }
    """
    results = []

    for assignment in submissions_json.get("assignments", []):
        for sub in assignment.get("submissions", []):
            userid = sub.get("userid")
            submissionid = sub.get("id")

            for plugin in sub.get("plugins", []):
                for area in plugin.get("fileareas", []):
                    for f in area.get("files", []):
                        results.append({
                            "userid": userid,
                            "submissionid": submissionid,
                            "filename": f.get("filename"),
                            "fileurl": f.get("fileurl"),
                            "mimetype": f.get("mimetype"),
                        })

    return results


def download_file(url: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as fp:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fp.write(chunk)


def preview_pdf_text(pdf_path: str, max_chars: int = 800) -> str:
    """Extract some text from the first page (best-effort)."""
    reader = PdfReader(pdf_path)
    if not reader.pages:
        return "(No pages found)"
    text = reader.pages[0].extract_text() or ""
    text = " ".join(text.split())
    return text[:max_chars] + ("..." if len(text) > max_chars else "")


def main():
    print("1) Fetching submissions...")
    submissions = call_moodle(
        "mod_assign_get_submissions",
        {"assignmentids[0]": ASSIGNMENT_ID}
    )

    print("2) Extracting file list from response...")
    files = extract_all_files(submissions)

    if not files:
        print("No files found in submissions response.")
        return

    print(f"Found {len(files)} file(s). Filtering PDFs and downloading...")

    os.makedirs(OUT_DIR, exist_ok=True)

    for f in files:
        filename = f["filename"] or "file"
        mimetype = f["mimetype"] or ""
        fileurl = f["fileurl"]

        # Filter: accept PDFs by mimetype or filename
        is_pdf = ("pdf" in mimetype.lower()) or filename.lower().endswith(".pdf")
        if not is_pdf:
            continue

        if not fileurl:
            continue

        token_url = add_token_to_fileurl(fileurl)

        user_part = f"user_{f['userid']}" if f["userid"] is not None else "user_unknown"
        sub_part = f"submission_{f['submissionid']}" if f["submissionid"] is not None else "submission_unknown"
        out_name = safe_name(filename)
        out_path = os.path.join(OUT_DIR, user_part, sub_part, out_name)

        print(f"\nDownloading: {filename}")
        print(f"-> {out_path}")

        download_file(token_url, out_path)

        # Preview
        try:
            preview = preview_pdf_text(out_path)
            print("Preview (first page text):")
            print(preview if preview else "(No extractable text - might be scanned/image PDF)")
        except Exception as e:
            print(f"Preview failed: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
