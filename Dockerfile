FROM python:3.11-slim

WORKDIR /

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--workers", "4", "--threads", "2", "--bind", "0.0.0.0:5201", "app:app"]
