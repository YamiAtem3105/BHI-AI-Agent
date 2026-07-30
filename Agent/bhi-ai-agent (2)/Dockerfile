FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x scripts/start.sh
EXPOSE 8080
CMD ["sh", "scripts/start.sh"]
