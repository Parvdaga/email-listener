import os
import json
import gspread
import imaplib
import email
from email.header import decode_header
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialize Flask App ---
app = Flask(__name__)

# Load environment variables
CREDENTIALS_JSON_CONTENT = os.environ.get("GCP_SA_CREDS_JSON")
if CREDENTIALS_JSON_CONTENT:
    with open("credentials.json", "w") as f:
        f.write(CREDENTIALS_JSON_CONTENT)

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")  # This was missing!
IMAP_SERVER = "imap.gmail.com"
SUBJECT_FILTER = "God bless you"
CREDENTIALS_FILE = "credentials.json"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

def parse_with_gemini(email_body):
    """Parse email content using Gemini AI to extract job postings."""
    try:
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
        logger.info(f"Gemini response: {cleaned_text}")
        return json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"Error parsing with Gemini: {e}")
        return {"jobs": []}

def get_google_sheet():
    """Get or create Google Sheet for job postings."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        
        # Use the GOOGLE_SHEET_ID to open the sheet
        if GOOGLE_SHEET_ID:
            try:
                sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
                logger.info("✅ Successfully opened existing Google Sheet")
            except gspread.exceptions.SpreadsheetNotFound:
                logger.error("❌ Sheet with provided ID not found")
                return None
        else:
            # Fallback: try to open by name or create new
            try:
                sheet = client.open("Job Postings").sheet1
            except gspread.exceptions.SpreadsheetNotFound:
                sheet = client.create("Job Postings").sheet1
                logger.info("📝 Created new Google Sheet")
        
        # Check if headers exist, if not add them
        try:
            headers = sheet.row_values(1)
            if not headers or len(headers) < 11:
                headers = ["S.No", "Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline"]
                sheet.insert_row(headers, 1)
                logger.info("📝 Added headers to sheet")
        except Exception as e:
            logger.error(f"Error checking/adding headers: {e}")
            
        return sheet
    except Exception as e:
        logger.error(f"Error getting Google Sheet: {e}")
        return None

def append_jobs_to_sheet(jobs_list, sheet):
    """Append job postings to Google Sheet."""
    try:
        if not jobs_list:
            logger.info("ℹ️ No jobs found in the email to add.")
            return

        # Get current row count
        all_values = sheet.get_all_values()
        start_s_no = len(all_values)
        
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
                elif value is None:
                    value = ""
                new_row.append(str(value))
            rows_to_add.append(new_row)

        if rows_to_add:
            sheet.append_rows(rows_to_add)
            logger.info(f"✅ Successfully added {len(rows_to_add)} job(s) to Google Sheet.")
    except Exception as e:
        logger.error(f"Error appending jobs to sheet: {e}")

def run_job():
    """Main job processing function."""
    logger.info("🚀 Starting email processing job...")
    
    try:
        # Get Google Sheet
        sheet = get_google_sheet()
        if not sheet:
            logger.error("❌ Failed to get Google Sheet")
            return
            
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        mail.select("inbox")
        
        # Search for unread emails with specific subject
        status, messages = mail.search(None, f'(UNSEEN SUBJECT "{SUBJECT_FILTER}")')
        email_ids = messages[0].split()
        
        if not email_ids:
            logger.info("✅ No new unread emails found. Job finished.")
            mail.logout()
            return

        logger.info(f"📩 Found {len(email_ids)} new email(s) to process.")
        
        for e_id in email_ids:
            try:
                # Fetch email
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Extract email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                
                logger.info(f"Email body length: {len(body) if body else 0}")
                
                if body:
                    # Parse with Gemini
                    parsed_data = parse_with_gemini(body)
                    append_jobs_to_sheet(parsed_data.get("jobs", []), sheet)
                    
                    # Mark email as read
                    mail.store(e_id, '+FLAGS', '\\Seen')
                else:
                    logger.warning(f"Empty body for email ID {e_id.decode()}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing email ID {e_id.decode()}: {e}")
        
        mail.logout()
        logger.info("🎉 Successfully processed all new emails.")
        
    except Exception as e:
        logger.error(f"🔥 A critical error occurred: {e}")

@app.route('/webhook', methods=['POST'])
def webhook_trigger():
    """Webhook endpoint that triggers the email processing job."""
    logger.info("🔔 Webhook received! Starting job...")
    try:
        run_job()
        return {"status": "success", "message": "Job completed successfully"}, 200
    except Exception as e:
        logger.error(f"Webhook execution failed: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Service is running"}, 200

@app.route('/', methods=['GET'])
def home():
    """Basic status page."""
    return {"status": "running", "message": "Job Scraper Service"}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
