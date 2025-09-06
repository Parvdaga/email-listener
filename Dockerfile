# Use an official lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the Gunicorn web server with an increased timeout
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--timeout", "120", "main:app"]