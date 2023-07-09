FROM ubuntu:latest

WORKDIR /app

COPY requirements.txt .
RUN apt-get update
RUN apt-get install -y python3 python3-pip cron git
RUN pip install --no-cache-dir -r requirements.txt

COPY script.py .
COPY crontab /etc/cron.d/my-cron

RUN chmod 0644 /etc/cron.d/my-cron
RUN crontab /etc/cron.d/my-cron

CMD ["cron", "-f"]
