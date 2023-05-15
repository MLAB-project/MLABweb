# syntax=docker/dockerfile:1
FROM ubuntu:latest
ENV GIT_PYTHON_REFRESH=quiet
RUN apt-get update
RUN apt-get install -y gcc musl-dev python3 python3-pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt 
EXPOSE 5000
COPY src .
WORKDIR MLABweb
#RUN tree .
CMD ["python3", "mlab_web.py"]
