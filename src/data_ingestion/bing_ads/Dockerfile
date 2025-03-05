FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create reports directory for storing downloaded reports
RUN mkdir -p /app/reports

COPY . .

CMD ["python", "main.py"]
