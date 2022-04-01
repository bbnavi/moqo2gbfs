# BARShare GBFS publishing

This directory contains [a script](main.sh) that
1. uses `moqo2gbfs` to generate three [BARShare](https://barshare.de) GBFS feeds (`bicycle`, `car` & `other`)
2. copies the feeds into the `barshare` bucket within the [bbnavi](https://bbnavi.de) [open data portal](https://opendata.bbnavi.de)
3. repeats this process every 5 minutes.

## Docker

To build a Docker image for this publishing tool, run the following command *within this directory*:

```shell
docker build -t publish-barshare-gbfs .
```

*Note:* The [`Dockerfile`](Dockerfile) assumes that you have built the [moqo2gbfs](..) Docker image as `moqo2gbfs`.

Run a container as follows:

```shell
docker run -it --rm \
	-e MOQO_ACCESS_TOKEN=… -e MINIO_ACCESS_KEY=… -e MINIO_SECRET_KEY=… \
	publish-barshare-gbfs
```