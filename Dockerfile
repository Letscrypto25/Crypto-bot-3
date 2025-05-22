FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN ls -la /app

# Copy app files
COPY . .

# Expose the Flask app port
EXPOSE 8080

# Run the app
CMD ["python", "main.py"]
