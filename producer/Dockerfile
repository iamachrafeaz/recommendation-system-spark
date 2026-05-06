FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

COPY reviews_10.csv .

RUN pip install --no-cache-dir -r requirements.txt

COPY producer.py .

CMD ["bash"]