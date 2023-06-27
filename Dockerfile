FROM python:3.10.9-slim

COPY . .

RUN pip install -r requirements.txt

RUN chmod +x run.sh

CMD ["./run.sh"]