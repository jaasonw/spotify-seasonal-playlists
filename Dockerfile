FROM python:3.11.4-slim

COPY . .

RUN pip install -r requirements.txt

RUN chmod +x run.sh

CMD ["./run.sh"]