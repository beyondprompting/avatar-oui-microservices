FROM python:3.11-slim

WORKDIR /app

COPY messages.json /app/messages.json
COPY server.py /app/server.py

RUN pip install flask flask-cors

EXPOSE 2222

CMD ["python", "server.py"]
