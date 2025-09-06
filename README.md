# Automated Job Posting Scraper

An intelligent email-to-spreadsheet automation system that processes job postings from Gmail using AI parsing and real-time updates to Google Sheets.

## Overview

This project creates a seamless pipeline that automatically:
- Monitors Gmail for specific job posting emails
- Extracts and parses job details using Google Gemini AI
- Populates a Google Sheet with structured job data in real-time

## Architecture

The system uses an event-driven architecture for instant processing:

```
Gmail → Make.com → Webhook → Railway App → Google Sheets
```

1. **Email Detection**: Make.com monitors Gmail for emails with subject "God bless you"
2. **Webhook Trigger**: New emails trigger a POST request to the Railway-hosted webhook
3. **AI Processing**: Python application extracts email content and parses it with Gemini API
4. **Data Storage**: Structured job data is appended to Google Sheets automatically

## Features

- **Real-time Processing**: Instant email-to-sheet updates via webhook architecture
- **AI-Powered Parsing**: Google Gemini API extracts job details (company, position, location, etc.)
- **Cloud Deployment**: Containerized application deployed on Railway
- **Automated Workflow**: No manual intervention required once configured

## Prerequisites

Before setting up, ensure you have:

- Gmail account with App Password enabled
- Google Cloud Platform account with Gemini API access
- Google Service Account with Sheets API permissions
- Make.com account (free tier available)

## Setup Instructions

### 1. Clone and Prepare Repository

```bash
git clone <repository-url>
cd automated-job-scraper
```

### 2. Google Cloud Setup

1. Create a new project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the following APIs:
   - Gmail API
   - Google Sheets API
   - Gemini API
3. Create a Service Account:
   - Go to IAM & Admin → Service Accounts
   - Create new service account with Editor role
   - Generate and download JSON key file
4. Get your Gemini API key from [Google AI Studio](https://aistudio.google.com)

### 3. Gmail Configuration

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → App passwords
   - Generate password for "Mail" application
   - Save the 16-character password

### 4. Railway Deployment

1. Fork this repository to your GitHub account
2. Sign up for [Railway](https://railway.app) and connect your GitHub
3. Create new project from GitHub repository
4. Add environment variables in Railway dashboard:

```env
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
GEMINI_API_KEY=your-gemini-api-key
GCP_SA_CREDS_JSON=your-service-account-json-content
GOOGLE_SHEET_ID=your-google-sheet-id
```

5. Deploy the application
6. Copy the generated public domain URL

### 5. Google Sheets Setup

1. Create a new Google Sheet
2. Copy the Sheet ID from the URL (the long string between `/d/` and `/edit`)
3. Share the sheet with your service account email address
4. Set up headers in the first row (e.g., Company, Position, Location, Salary, Date)

### 6. Make.com Configuration

1. Create new scenario in [Make.com](https://make.com)
2. **Module 1 - Gmail Trigger**:
   - Select "Watch emails"
   - Connect your Gmail account
   - Set filter: Subject contains "God bless you"
   - Set to watch unread emails only
3. **Module 2 - HTTP Request**:
   - Select "Make a request"
   - Method: POST
   - URL: `https://your-railway-app.up.railway.app/webhook`
   - Headers: `Content-Type: application/json`
4. Save and activate the scenario

## Project Structure

```
├── Dockerfile              # Container configuration
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
└── config/
    └── logging.conf       # Logging configuration
```

## API Endpoints

- `POST /webhook` - Receives triggers from Make.com and processes emails
- `GET /health` - Health check endpoint
- `GET /` - Basic status page

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GMAIL_ADDRESS` | Your Gmail email address | Yes |
| `GMAIL_APP_PASSWORD` | 16-character Gmail app password | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GCP_SA_CREDS_JSON` | Service account credentials JSON | Yes |
| `GOOGLE_SHEET_ID` | Target Google Sheet ID | Yes |
| `PORT` | Application port (default: 8000) | No |

## Usage

Once configured, the system works automatically:

1. Send an email with subject "God bless you" containing job posting content
2. Make.com detects the email and triggers the webhook
3. The application processes the email and extracts job details
4. Parsed data is automatically added to your Google Sheet

## Troubleshooting

### Common Issues

**Webhook not triggered**:
- Verify Make.com scenario is active
- Check Gmail filters in Make.com configuration
- Ensure Railway app is running

**Authentication errors**:
- Verify Gmail app password is correct
- Check service account permissions on Google Sheet
- Ensure all API keys are valid

**Parsing errors**:
- Check Gemini API quota and billing
- Verify email content format
- Review application logs in Railway

### Logs and Monitoring

View application logs in Railway dashboard under the "Deployments" tab for debugging.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Parv Daga**
- GitHub: [@parvdaga](https://github.com/parvdaga)
- Email: parv@example.com

## Acknowledgments

- Google Gemini API for intelligent text parsing
- Make.com for webhook automation
- Railway for seamless deployment

---

*Built with ❤️ for automating job application workflows*
