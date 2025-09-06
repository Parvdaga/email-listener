import os
import json
import gspread
import imaplib
import email
from email.header import decode_header
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials

# ---
# This special block writes the Google credentials from an environment
# variable into a temporary file that gspread can read.
# ---
CREDENTIALS_JSON_CONTENT = os.environ.get("GCP_SA_CREDS_JSON")
if CREDENTIALS_JSON_CONTENT:
    with open("credentials.json", "w") as f:
        f.write(CREDENTIALS_JSON_CONTENT)
# ---

# =========================================
# 🔹 Load Configuration from Environment Variables
# =========================================
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

IMAP_SERVER = "imap.gmail.com"
SUBJECT_FILTER = "God bless you"
SHEET_NAME = "Job Postings"
CREDENTIALS_FILE = "credentials.json"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# (The rest of the script is exactly the same as the PythonAnywhere version)

def parse_with_gemini(email_body):
    # ... same code ...
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    Extract all job postings from the email below into a JSON object.
    The object must have a single key: "jobs".
    The value of "jobs" must be a list of job objects.
    Each job object in the list must have these keys: "Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline".
    If a field is not found, its value should be null.
    If no jobs are found, return an empty list for the "jobs" key.

    Email:
    {email_body}
    """
    response = model.generate_content(prompt)
    cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned_text)

def get_google_sheet():
    # ... same code ...
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open(SHEET_NAME).sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        sheet = client.create(SHEET_NAME).sheet1
        headers = ["S.No", "Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline"]
        sheet.append_row(headers)
        print("📝 Created new Google Sheet and added headers.")
    return sheet

def append_jobs_to_sheet(jobs_list, sheet):
    # ... same code ...
    if not jobs_list:
        print("ℹ️ No jobs found in the email to add.")
        return

    start_s_no = len(sheet.get_all_values())
    rows_to_add = []
    fields = ["Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline"]
    
    for i, job in enumerate(jobs_list):
        start_s_no += 1
        new_row = [start_s_no]
        for field in fields:
            value = job.get(field)
            if isinstance(value, list):
                value = ", ".join(map(str, value))
            elif isinstance(value, dict):
                 value = json.dumps(value)
            new_row.append(str(value or ""))
        rows_to_add.append(new_row)

    if rows_to_add:
        sheet.append_rows(rows_to_add)
        print(f"✅ Successfully added {len(rows_to_add)} job(s) to Google Sheet.")


def run_job():
    # ... same code ...
    print("🚀 Starting email processing job...")
    
    try:
        sheet = get_google_sheet()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        mail.select("inbox")
        
        status, messages = mail.search(None, f'(UNSEEN SUBJECT "{SUBJECT_FILTER}")')
        email_ids = messages[0].split()
        
        if not email_ids:
            print("✅ No new unread emails found. Job finished.")
            mail.logout()
            return

        print(f"📩 Found {len(email_ids)} new email(s) to process.")
        
        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()
            
            if body:
                try:
                    parsed_data = parse_with_gemini(body)
                    append_jobs_to_sheet(parsed_data.get("jobs", []), sheet)
                except Exception as e:
                    print(f"❌ Error processing email ID {e_id.decode()}: {e}")
        
        mail.logout()
        print("🎉 Successfully processed all new emails.")
        
    except Exception as e:
        print(f"🔥 A critical error occurred: {e}")

if __name__ == "__main__":
    run_job()