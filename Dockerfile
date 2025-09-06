# Use an official lightweight Python image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install the requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the Gunicorn web server, using the port provided by Railway
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "main:app"]