# This Dockerfile builds a service that regularly publishes the BARShare GBFS to the bbnavi open data portal.
FROM minio/mc as mc

FROM moqo2gbfs

ENV MOQO_ACCESS_TOKEN=""
ENV MINIO_ACCESS_KEY="" MINIO_SECRET_KEY=""
ENV PUBLISH_INTERVAL=""

RUN apk add --no-cache --update tree

# install MinIO client a.k.a. mc
COPY --from=mc /usr/bin/mc /usr/bin/mc

COPY main.sh ./
COPY index.html ./

# prevent inheriting `python` as entrypoint
ENTRYPOINT []

CMD ["/bin/sh", "main.sh"]
