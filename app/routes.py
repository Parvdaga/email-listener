import email
import logging
import traceback # Import the traceback module
from flask import Blueprint, jsonify, request
from . import services

logger = logging.getLogger(__name__)
bp = Blueprint('api', __name__)

@bp.route("/", methods=['GET'])
def index():
    return jsonify({
        "status": "running",
        "message": "Job Scraper Service is active."
    })

@bp.route("/health", methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@bp.route("/webhook", methods=['POST'])
def webhook_trigger():
    """Main webhook to trigger the email processing job."""
    # Added for debugging
    print("-".center(50, "-"))
    logger.info("🎯 Webhook endpoint hit! Request received.")
    print("🎯 Webhook endpoint hit! Request received.")
    
    logger.info("🔔 Webhook received! Starting email processing job...")
    
    sheet = services.get_google_sheet()
    if not sheet:
        return jsonify({"success": False, "error": "Failed to access Google Sheet"}), 500

    email_ids, mail = services.fetch_unread_emails()
    if not email_ids:
        logger.info("✅ No new unread emails found.")
        return jsonify({"success": True, "message": "No new emails to process", "processed": 0}), 200

    logger.info(f"📩 Found {len(email_ids)} new email(s).")
    total_jobs_added = 0
    processed_emails = 0

    for e_id in email_ids:
        try:
            # --- DEBUG STEP 1: Check if the loop starts ---
            print(f"Processing email ID: {e_id.decode()}")

            _, msg_data = mail.fetch(e_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            body = services.get_email_body(msg)

            # --- DEBUG STEP 2: Check the extracted email body ---
            print(f"Extracted Email Body (first 200 chars): {body[:200]}")

            if not body:
                logger.warning(f"⚠️ Empty body for email ID {e_id.decode()}, marking as read.")
                mail.store(e_id, '+FLAGS', '\\Seen')
                continue
            
            # --- DEBUG STEP 3: Check right before the Gemini call ---
            print("🤖 Calling Gemini API to parse email content...")
            parsed_data = services.parse_email_with_gemini(body)
            print("🤖 Gemini API call finished.")
            
            jobs = parsed_data.get("jobs", [])
            
            # --- DEBUG STEP 4: Check the jobs found by Gemini ---
            print(f"Found {len(jobs)} jobs in the email.")

            if jobs:
                print("📝 Appending jobs to Google Sheet...")
                jobs_added_count = services.append_jobs_to_sheet(sheet, jobs)
                if jobs_added_count > 0:
                    total_jobs_added += jobs_added_count
                print(f"✅ Appended {jobs_added_count} jobs.")
            else:
                logger.info(f"ℹ️ No jobs found in email {e_id.decode()}.")

            # Mark email as read after processing
            mail.store(e_id, '+FLAGS', '\\Seen')
            processed_emails += 1
            logger.info(f"✅ Email {e_id.decode()} processed.")

        except Exception as e:
            # --- IMPORTANT: This will print the exact error to your logs ---
            logger.error(f"❌ An error occurred while processing email ID {e_id.decode()}: {e}")
            print(f"❌ An error occurred. Full traceback below:")
            traceback.print_exc() # This prints the full error stack trace

    if mail:
        mail.logout()
    
    # Added for debugging
    print("🎉 Webhook processing finished.")
    logger.info("🎉 Webhook processing finished.")
    print("-".center(50, "-"))

    return jsonify({
        "success": True,
        "message": f"Processed {processed_emails}/{len(email_ids)} emails and added {total_jobs_added} jobs."
    }), 200