# Use a smaller Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy only the requirements first to leverage Docker's caching mechanism
COPY requirements.txt /app/requirements.txt

# Install only the dependencies specified in the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application
COPY . /app

# Set environment variables (optional here—better to use secrets in Fly.io)
ENV FIREBASE_CREDENTIALS="path/to/firebase-credentials.json"
ENV BOT_TOKEN="your-telegram-bot-token"

# Expose the port for health checks
EXPOSE 8080

# Start the application
CMD ["python", "main.py"]
