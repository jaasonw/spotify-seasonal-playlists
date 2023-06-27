FROM python:3.10.9-slim

COPY . .

RUN pip install -r requirements.txt

CMD ["./run.sh"]