FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variable for config
ENV APP_CONFIG_FILE=appconfig.development

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 5551

# Use gunicorn for production, or flask run for development
CMD ["gunicorn", "--bind", "0.0.0.0:5551", "--workers", "2", "run:app"]
