FROM python:3.10.9-slim

COPY . .

RUN pip install -r requirements.txt

CMD ["gunicorn", "--chdir", "src/", "-k", "gevent", "-t", "900", "web_auth:auth_server", "--bind", "0.0.0.0:8080", "--capture-output", "--log-level", "debug"]
# CMD ["python", "src/app.py"]
