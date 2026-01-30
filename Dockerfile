# Use a slim version of Python
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system-level dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# This ensures you never deploy a broken agent. 
# If tests fail, the build fails.
RUN python -m unittest tests.py

# Create output directory
RUN mkdir -p /app/output

# Run the agent script
CMD ["python", "agent.py"]