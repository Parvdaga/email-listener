# Automated Job Posting Scraper

An intelligent email-to-spreadsheet automation system that processes job postings from Gmail using AI parsing and real-time updates to Google Sheets.

## Overview

This project creates a seamless pipeline that automatically:

  - Monitors a Gmail account for specific job posting emails.
  - Uses Google Apps Script for near real-time detection of new emails.
  - Triggers a webhook to a Python application hosted on Railway.
  - Extracts and parses job details from the email content using the Google Gemini API.
  - Populates a Google Sheet with structured job data automatically.

## Architecture

The system uses a robust, serverless, event-driven architecture for instant processing. The reliance on third-party automation services like Zapier or Make.com has been eliminated.

```
Gmail → Google Apps Script → Webhook → Railway App → Google Sheets
```

1.  **Email Detection**: A Google Apps Script, running every minute on a time-based trigger, checks for unread emails with a specific subject line.
2.  **Webhook Trigger**: Upon finding a new email, the script instantly sends a `POST` request to a webhook endpoint on a Railway-hosted Python Flask application.
3.  **AI Processing**: The Flask application connects to the Gmail account via IMAP, fetches the email content, and sends it to the Gemini API for intelligent parsing.
4.  **Data Storage**: The structured job data returned by the AI is appended as a new row to a designated Google Sheet.

## Features

  - **Near Real-Time Processing**: Sub-minute email-to-sheet updates via the Google Apps Script trigger.
  - **AI-Powered Parsing**: Google Gemini API intelligently extracts key job details like company, position, location, and more.
  - **Cloud-Native Deployment**: Fully containerized application deployed and managed on Railway.
  - **Cost-Effective & Scalable**: A completely free-tier-friendly architecture with no third-party subscription costs.
  - **Resilient**: If processing fails, the email remains unread and is automatically re-processed on the next trigger, preventing data loss.

## Prerequisites

Before setting up, ensure you have:

  - A Google account (e.g., Gmail) with 2-Factor Authentication enabled.
  - A Google Cloud Platform project with billing enabled to use the Gemini API.
  - A Railway account connected to your GitHub account.

## Setup Instructions

Follow these steps to deploy and configure the application.

### Step 1: Google Cloud & Service Account Setup

1.  Create a new project in the [Google Cloud Console](https://console.cloud.google.com).
2.  Enable the following APIs for your project:
      - **Gmail API**
      - **Google Sheets API**
      - **Gemini API** (or Vertex AI API)
3.  Create a **Service Account**:
      - In the Google Cloud Console, navigate to **IAM & Admin → Service Accounts**.
      - Click **"Create Service Account"**. Give it a name (e.g., `job-sheet-bot`) and grant it the **"Editor"** role.
      - After creating the account, go to its **"Keys"** tab, click **"Add Key"**, and create a new **JSON** key. A JSON file will be downloaded—keep it secure.
4.  Note down the email address of the newly created service account (e.g., `...iam.gserviceaccount.com`).

### Step 2: Gmail App Password

1.  Navigate to your Google Account security settings.
2.  Under "How you sign in to Google," click on **"App passwords"**. You may need to sign in again.
3.  Create a new app password. For the app, select **"Mail"**, and for the device, select **"Other (Custom name)"** and type "Job Scraper App".
4.  Google will generate a 16-character password. Copy this password and save it securely. **This is not your regular Gmail password.**

### Step 3: Google Sheet Setup

1.  Create a new Google Sheet in your Google account.
2.  Copy the **Sheet ID** from its URL. The ID is the long string of characters between `/d/` and `/edit`.
3.  Click the **"Share"** button and share the sheet with the **Service Account email address** you noted in Step 1. Assign it the **"Editor"** role.

### Step 4: Deploy to Railway

1.  **Fork this repository** to your own GitHub account.
2.  On the [Railway](https://railway.app) dashboard, create a new project and select **"Deploy from GitHub repo"**. Choose the repository you just forked.
3.  In your Railway project, go to the **"Variables"** tab and add the following environment variables:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `GMAIL_ADDRESS` | The Gmail address the script will read from. | `your.email@gmail.com` |
| `GMAIL_APP_PASSWORD` | The 16-character App Password from Step 2. | `abcd efgh ijkl mnop` |
| `GEMINI_API_KEY` | Your API key for the Google Gemini API. | `AIzaSy...` |
| `GOOGLE_SHEET_ID` | The ID of your target Google Sheet from Step 3. | `1qA2b...` |
| `GCP_SA_CREDS_JSON` | The **entire content** of the JSON key file you downloaded in Step 1, pasted as a single line. | `{ "type": "service_account", ... }` |

4.  Railway will automatically deploy your application. Once it's live, go to the **"Settings"** tab and find your application's public URL (e.g., `https://my-app.up.railway.app`).

### Step 5: Configure the Google Apps Script Trigger

This script replaces the need for any third-party service like Make.com or IFTTT.

1.  Open your Google Sheet.
2.  Click on **Extensions \> Apps Script**.
3.  Delete any boilerplate code and paste the following script into the editor.
4.  **Crucially, replace `YOUR_RAILWAY_WEBHOOK_URL` with your public Railway URL from the previous step.**

<!-- end list -->

```javascript
// Replace with your actual Railway app's webhook URL
const WEBHOOK_URL = 'https://your-app-name.up.railway.app/webhook';

// The subject line the script will search for in Gmail
const SUBJECT_FILTER = '"God bless you"';

/**
 * Checks for new, unread emails matching the filter and triggers the webhook.
 */
function checkForNewEmailsAndTriggerWebhook() {
  const searchQuery = `is:unread subject:${SUBJECT_FILTER}`;
  const threads = GmailApp.search(searchQuery, 0, 1);
  
  if (threads.length > 0) {
    console.log(`Found new email thread(s). Triggering webhook.`);
    sendWebhookNotification();
  } else {
    console.log("No new emails found.");
  }
}

/**
 * Sends a POST request to the application's webhook.
 */
function sendWebhookNotification() {
  const options = {
    'method': 'post',
    'contentType': 'application/json',
    'muteHttpExceptions': true
  };

  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    console.log(`Webhook triggered. Response code: ${response.getResponseCode()}`);
  } catch (e) {
    console.error(`Failed to trigger webhook: ${e.toString()}`);
  }
}
```

5.  **Set up the trigger:**
      - On the left menu, click the **Triggers** (alarm clock) icon.
      - Click **"+ Add Trigger"**.
      - Set the function to run to `checkForNewEmailsAndTriggerWebhook`.
      - Set the event source to `Time-driven`.
      - Set the time-based trigger type to `Minutes timer` and the interval to `Every minute`.
      - Click **Save**.
6.  **Authorize the script.** You will be prompted to grant permissions for the script to access your Gmail and send requests to external services. Allow these permissions.

## Project Structure

```
.
├── app/
│   ├── __init__.py        # Flask application factory
│   ├── config.py          # Configuration loading and validation
│   ├── routes.py          # API endpoints (e.g., /webhook)
│   └── services.py        # Business logic (Gmail, Gemini, GSheets)
├── main.py                # Application entry point for Gunicorn
├── Dockerfile             # Container configuration for Railway
├── requirements.txt       # Python dependencies
├── .gitignore             # Files to be ignored by Git
└── README.md              # This file
```

## Troubleshooting

  - **Sheet Not Updating**:
      - Check the **Railway deployment logs**. This is your most important tool. Look for any errors related to "Google Sheets access failed" or "Error parsing with Gemini".
      - Verify that all your environment variables in Railway are correct.
      - Ensure your Google Sheet is shared with the service account email with **"Editor"** permissions.
  - **Webhook Not Firing**:
      - In the Google Apps Script editor, check the **Executions** tab. You should see the script running every minute. If it's failing, the logs will show the error.
      - Ensure the `WEBHOOK_URL` in your Apps Script is correct.
