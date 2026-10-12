FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
