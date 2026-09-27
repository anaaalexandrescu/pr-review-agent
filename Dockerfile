# Use a lightweight Python 3.12 image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py server.py /app/

CMD ["python", "agent.py"]