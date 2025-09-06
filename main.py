import os
import json
import gspread
import imaplib
import email
from email.header import decode_header
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialize Flask App ---
app = Flask(__name__)

# Load environment variables with validation
def validate_env_vars():
    required_vars = [
        'GMAIL_ADDRESS', 
        'GMAIL_APP_PASSWORD', 
        'GEMINI_API_KEY', 
        'GCP_SA_CREDS_JSON', 
        'GOOGLE_SHEET_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

# Validate environment variables on startup
env_valid = validate_env_vars()

# Write credentials file
CREDENTIALS_JSON_CONTENT = os.environ.get("GCP_SA_CREDS_JSON")
if CREDENTIALS_JSON_CONTENT:
    try:
        # Validate JSON format
        json.loads(CREDENTIALS_JSON_CONTENT)
        with open("credentials.json", "w") as f:
            f.write(CREDENTIALS_JSON_CONTENT)
        logger.info("✅ Credentials file created successfully")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in GCP_SA_CREDS_JSON: {e}")
        env_valid = False

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
IMAP_SERVER = "imap.gmail.com"
SUBJECT_FILTER = "God bless you"
CREDENTIALS_FILE = "credentials.json"

# Configure Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini API configured")
    except Exception as e:
        logger.error(f"❌ Failed to configure Gemini API: {e}")

def test_gmail_connection():
    """Test Gmail IMAP connection."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        mail.select("inbox")
        logger.info("✅ Gmail connection successful")
        mail.logout()
        return True
    except Exception as e:
        logger.error(f"❌ Gmail connection failed: {e}")
        return False

def test_google_sheets_access():
    """Test Google Sheets access."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        
        if GOOGLE_SHEET_ID:
            sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
            logger.info("✅ Google Sheets access successful")
            return True
        else:
            logger.error("❌ GOOGLE_SHEET_ID not provided")
            return False
    except Exception as e:
        logger.error(f"❌ Google Sheets access failed: {e}")
        return False

def parse_with_gemini(email_body):
    """Parse email content using Gemini AI to extract job postings."""
    try:
        logger.info(f"📝 Parsing email body (length: {len(email_body)})")
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        Extract all job postings from the email below into a JSON object.
        The object must have a single key: "jobs".
        The value of "jobs" must be a list of job objects.
        Each job object in the list must have these keys: "Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline".
        If a field is not found, its value should be null.
        If no jobs are found, return an empty list for the "jobs" key.
        
        Return ONLY valid JSON, no markdown formatting or additional text.

        Email content:
        {email_body[:2000]}  # Limit to first 2000 chars to avoid token limits
        """
        
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip()
        
        # Remove markdown formatting if present
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text.replace("```json", "").replace("```", "").strip()
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.replace("```", "").strip()
        
        logger.info(f"🤖 Gemini response: {cleaned_text[:200]}...")
        
        parsed_data = json.loads(cleaned_text)
        jobs_count = len(parsed_data.get("jobs", []))
        logger.info(f"📊 Parsed {jobs_count} job(s) from email")
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error: {e}")
        logger.error(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
        return {"jobs": []}
    except Exception as e:
        logger.error(f"❌ Error parsing with Gemini: {e}")
        return {"jobs": []}

def get_google_sheet():
    """Get Google Sheet for job postings."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        logger.info("✅ Successfully opened Google Sheet")
        
        # Check if headers exist
        try:
            headers = sheet.row_values(1)
            expected_headers = ["S.No", "Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline"]
            
            if not headers or headers != expected_headers:
                sheet.clear()
                sheet.insert_row(expected_headers, 1)
                logger.info("📝 Added headers to sheet")
        except Exception as e:
            logger.error(f"Error with headers: {e}")
            
        return sheet
        
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error("❌ Sheet with provided ID not found")
        return None
    except Exception as e:
        logger.error(f"❌ Error accessing Google Sheet: {e}")
        return None

def append_jobs_to_sheet(jobs_list, sheet):
    """Append job postings to Google Sheet."""
    try:
        if not jobs_list:
            logger.info("ℹ️ No jobs found in the email to add.")
            return True

        # Get current row count
        all_values = sheet.get_all_values()
        start_s_no = len(all_values)
        
        rows_to_add = []
        fields = ["Date", "Company Name", "Job Position", "Location", "Job Description", "Details", "Role Type", "Link/Email", "CTC", "Deadline"]
        
        for job in jobs_list:
            start_s_no += 1
            new_row = [start_s_no]
            for field in fields:
                value = job.get(field, "")
                if isinstance(value, list):
                    value = ", ".join(map(str, value))
                elif isinstance(value, dict):
                    value = json.dumps(value)
                elif value is None:
                    value = ""
                new_row.append(str(value))
            rows_to_add.append(new_row)
            logger.info(f"📋 Prepared job: {job.get('Company Name', 'Unknown')} - {job.get('Job Position', 'Unknown')}")

        if rows_to_add:
            sheet.append_rows(rows_to_add)
            logger.info(f"✅ Successfully added {len(rows_to_add)} job(s) to Google Sheet.")
            return True
        return False
        
    except Exception as e:
        logger.error(f"❌ Error appending jobs to sheet: {e}")
        logger.error(traceback.format_exc())
        return False

def run_job():
    """Main job processing function."""
    logger.info("🚀 Starting email processing job...")
    
    if not env_valid:
        logger.error("❌ Environment variables not properly configured")
        return {"success": False, "error": "Environment configuration error"}
    
    try:
        # Get Google Sheet
        sheet = get_google_sheet()
        if not sheet:
            return {"success": False, "error": "Failed to access Google Sheet"}
            
        # Connect to Gmail
        logger.info("📧 Connecting to Gmail...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        mail.select("inbox")
        logger.info("✅ Gmail connection successful")
        
        # Search for unread emails with specific subject
        search_query = f'(UNSEEN SUBJECT "{SUBJECT_FILTER}")'
        logger.info(f"🔍 Searching for emails with query: {search_query}")
        
        status, messages = mail.search(None, search_query)
        email_ids = messages[0].split()
        
        if not email_ids:
            logger.info("✅ No new unread emails found.")
            mail.logout()
            return {"success": True, "message": "No new emails to process", "processed": 0}

        logger.info(f"📩 Found {len(email_ids)} new email(s) to process.")
        
        processed_count = 0
        for e_id in email_ids:
            try:
                logger.info(f"📬 Processing email ID: {e_id.decode()}")
                
                # Fetch email
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Get email subject for logging
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                logger.info(f"📧 Email subject: {subject}")
                
                # Extract email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8')
                                break
                            except UnicodeDecodeError:
                                try:
                                    body = part.get_payload(decode=True).decode('latin-1')
                                    break
                                except:
                                    logger.warning("Failed to decode email part")
                                    continue
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            body = msg.get_payload(decode=True).decode('latin-1')
                        except:
                            logger.warning("Failed to decode email body")
                
                logger.info(f"📄 Email body length: {len(body) if body else 0}")
                
                if body:
                    # Parse with Gemini
                    parsed_data = parse_with_gemini(body)
                    jobs = parsed_data.get("jobs", [])
                    
                    if jobs:
                        success = append_jobs_to_sheet(jobs, sheet)
                        if success:
                            processed_count += 1
                            # Mark email as read only if processing was successful
                            mail.store(e_id, '+FLAGS', '\\Seen')
                            logger.info(f"✅ Email {e_id.decode()} processed successfully")
                        else:
                            logger.error(f"❌ Failed to add jobs to sheet for email {e_id.decode()}")
                    else:
                        logger.info(f"ℹ️ No jobs found in email {e_id.decode()}")
                        # Mark as read even if no jobs found
                        mail.store(e_id, '+FLAGS', '\\Seen')
                        processed_count += 1
                else:
                    logger.warning(f"⚠️ Empty body for email ID {e_id.decode()}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing email ID {e_id.decode()}: {e}")
                logger.error(traceback.format_exc())
        
        mail.logout()
        logger.info(f"🎉 Successfully processed {processed_count}/{len(email_ids)} emails.")
        
        return {
            "success": True, 
            "message": f"Processed {processed_count}/{len(email_ids)} emails",
            "processed": processed_count,
            "total_found": len(email_ids)
        }
        
    except Exception as e:
        logger.error(f"🔥 Critical error in run_job: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

@app.route('/webhook', methods=['POST'])
def webhook_trigger():
    """Webhook endpoint that triggers the email processing job."""
    logger.info("🔔 Webhook received! Starting job...")
    try:
        result = run_job()
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Webhook execution failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test-connections', methods=['GET'])
def test_connections():
    """Test all connections and configurations."""
    logger.info("🧪 Testing all connections...")
    
    results = {
        "environment_vars": env_valid,
        "gmail_connection": False,
        "sheets_access": False,
        "gemini_api": False
    }
    
    # Test Gmail
    if env_valid:
        results["gmail_connection"] = test_gmail_connection()
        results["sheets_access"] = test_google_sheets_access()
        
        # Test Gemini
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content("Hello, respond with 'OK'")
            if "OK" in response.text:
                results["gemini_api"] = True
                logger.info("✅ Gemini API test successful")
        except Exception as e:
            logger.error(f"❌ Gemini API test failed: {e}")
    
    return jsonify(results), 200

@app.route('/manual-run', methods=['POST'])
def manual_run():
    """Manually trigger job processing for testing."""
    logger.info("🔧 Manual job run triggered")
    result = run_job()
    return jsonify(result), 200 if result["success"] else 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "message": "Service is running"}), 200

@app.route('/', methods=['GET'])
def home():
    """Basic status page."""
    return jsonify({
        "status": "running", 
        "message": "Job Scraper Service",
        "endpoints": {
            "/webhook": "POST - Main webhook endpoint",
            "/test-connections": "GET - Test all connections",
            "/manual-run": "POST - Manually trigger job",
            "/health": "GET - Health check"
        }
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
