# This Dockerfile builds a service that regularly publishes the BARShare GBFS to the bbnavi open data portal.
FROM python:3-alpine

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apk add --no-cache --update tree minio-cli

WORKDIR /usr/src/app

COPY main.sh ./
COPY index.html barshare-logo.png ./

ENV MOQO_ACCESS_TOKEN=""
ENV MINIO_ACCESS_KEY="" MINIO_SECRET_KEY=""
ENV PUBLISH_INTERVAL=""

# prevent inheriting `python` as entrypoint
ENTRYPOINT []

CMD ["/bin/sh", "main.sh"]
