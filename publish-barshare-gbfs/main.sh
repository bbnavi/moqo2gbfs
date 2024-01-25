#!/bin/sh
# This script regularly publishes the BARShare GBFS to the bbnavi open data portal.

set -e

if [ -z "$MOQO_ACCESS_TOKEN" ]; then
	1>&2 echo 'missing/empty $MOQO_ACCESS_TOKEN'
	exit 1
fi
if [ -z "$MINIO_ACCESS_KEY" ]; then
	1>&2 echo 'missing/empty $MINIO_ACCESS_KEY'
	exit 1
fi
if [ -z "$MINIO_SECRET_KEY" ]; then
	1>&2 echo 'missing/empty $MINIO_SECRET_KEY'
	exit 1
fi

# default: 5 minutes
PUBLISH_INTERVAL="${PUBLISH_INTERVAL:-300}"

export MC_HOST_bbnavi="https://$MINIO_ACCESS_KEY:$MINIO_SECRET_KEY@opendata.bbnavi.de"

dir="$(mktemp -d -t barshare-gbfs.XXXXXX)"

set -x

mcli cp -q index.html barshare-logo.png bbnavi/barshare/

while true; do
	# We sleep first so that, if the GBFS generation fails contantly, we don't DOS the Moqo API.
	sleep "$PUBLISH_INTERVAL"

	python ../moqoToGBFS.py \
		--config BARshare --serviceUrl 'https://portal.moqo.de/api_aggregator/' \
		--baseUrl 'https://opendata.bbnavi.de/barshare' \
		--outputDir "$dir" \
		--token "$MOQO_ACCESS_TOKEN"

	tree -sh "$dir"

	mcli cp -q -r $dir/* bbnavi/barshare/
done
