FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV FLASK_APP=src.api.main
ENV PORT=5000

EXPOSE 5000

CMD ["gunicorn", "src.api.main:app", "--workers", "2", "--timeout", "120", "--bind", "0.0.0.0:5000"]