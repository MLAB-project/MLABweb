FROM ubuntu:latest

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

COPY requirements.txt .
#RUN add-apt-repository universe
RUN apt-get update
RUN apt-get install -y python3 python3-pip cron git
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY script.py .
COPY crontab /etc/cron.d/my-cron

RUN chmod 0644 /etc/cron.d/my-cron
RUN crontab /etc/cron.d/my-cron

CMD ["cron", "-f"]
