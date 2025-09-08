import email
import imaplib
import json
import logging
import traceback
from email.header import decode_header

import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from .config import config

logger = logging.getLogger(__name__)

# --- Gemini Service ---
def configure_gemini():
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        logger.info("✅ Gemini API configured.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to configure Gemini API: {e}")
        return False

def parse_email_with_gemini(body):
    """Parses email content using Gemini to extract job data."""
    if not body:
        return {"jobs": []}
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        # --- THIS PROMPT HAS BEEN UPDATED ---
        prompt = f"""
        You are an expert job posting extractor. Your task is to meticulously scan an email and extract all job postings into a clean JSON object.

        Follow these rules strictly:
        1.  The final output must be a single JSON object with one key: "jobs".
        2.  The value of "jobs" must be a list of individual job objects.
        3.  Each job object must have these exact keys: "Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline".
        4.  Scan the entire email. Treat any distinct block of text that describes a job role as a separate job posting, even if it's just a few lines. Pay special attention to the very beginning of the email.
        5.  If you cannot find a value for a specific field, use null.
        6.  If the email contains no job postings at all, return an empty list for the "jobs" key.
        7.  Return ONLY the valid JSON object and nothing else. Do not include markdown formatting like ```json.

        Email content to parse:
        {body[:8000]}
        """
        response = model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        logger.info(f"🤖 Gemini response received.")
        return json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"❌ Error parsing with Gemini: {e}")
        return {"jobs": []}

# --- Google Sheets Service ---
def get_google_sheet():
    """Initializes and returns the Google Sheet object."""
    try:
        scope = ["[https://spreadsheets.google.com/feeds](https://spreadsheets.google.com/feeds)", "[https://www.googleapis.com/auth/drive](https://www.googleapis.com/auth/drive)"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID).sheet1
        logger.info("✅ Google Sheets access successful.")
        
        # Ensure headers exist in an empty sheet without clearing existing data
        if not sheet.row_values(1):
            expected_headers = ["S.No", "Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline"]
            sheet.insert_row(expected_headers, 1)
            logger.info("📝 Added headers to empty sheet.")
        return sheet
    except Exception as e:
        logger.error(f"❌ Google Sheets access failed: {e}")
        return None

def append_jobs_to_sheet(sheet, jobs):
    """Appends a list of jobs to the specified Google Sheet."""
    if not jobs:
        logger.info("ℹ️ No jobs to add to the sheet.")
        return 0
    
    try:
        start_s_no = len(sheet.get_all_values())
        rows_to_add = []
        fields = ["Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline"]
        
        for job in jobs:
            start_s_no += 1
            row = [start_s_no] + [str(job.get(field, "") or "") for field in fields]
            rows_to_add.append(row)
        
        if rows_to_add:
            sheet.append_rows(rows_to_add)
            logger.info(f"✅ Successfully added {len(rows_to_add)} job(s) to Google Sheet.")
        return len(rows_to_add)
    except Exception as e:
        logger.error(f"❌ Error appending jobs to sheet: {e}\n{traceback.format_exc()}")
        return 0

# --- Gmail Service ---

def fetch_unread_emails():
    """Connects to Gmail and fetches unread emails matching the subject filter."""
    try:
        mail = imaplib.IMAP4_SSL(config.IMAP_SERVER)
        mail.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        mail.select("inbox")
        
        search_query = f'(UNSEEN SUBJECT "{config.SUBJECT_FILTER}")'
        status, messages = mail.search(None, search_query)
        
        if status != "OK" or not messages[0]:
            mail.logout()
            return [], None

        email_ids = messages[0].split()
        return email_ids, mail
        
    except Exception as e:
        logger.error(f"❌ Gmail connection or search failed: {e}")
        return [], None

def get_email_body(msg):
    """Extracts the plain text body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode()
                    break
                except (UnicodeDecodeError, AttributeError):
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode()
        except (UnicodeDecodeError, AttributeError):
            pass
    return body
