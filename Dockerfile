FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py main.py ./
COPY parser/ parser/
COPY dashboard/ dashboard/
COPY db/ db/
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["python", "main.py"]
