# moqo2gbfs

moqo2gbfs is a small python script, which generates a GBFS feed from MOQO's API.

To generate a feed for e.g. BARshare network, execute

```sh
python moqoToGBFS.py -t <secret> -b https://portal.moqo.de/api_aggregator/ -c BARshare
```

where <secret> needs to be replaced by the MOQO API secret.

Note: Not every GBFS information can be retrieved from the API. The content of  system_information and system_pricing_plans is hard coded in moqoToGBFS.py and need to be updated, if this information changes.

## Using Docker

```sh
docker build -t mfdz/moqo2gbfs
run -v $PWD/out:/usr/src/app/out mfdz/moqo2gbfs moqoToGBFS.py -t <secret> -b https://portal.moqo.de/api_aggregator/ -c BARshare

```

## Documentation

MOQO-API-Documentation is available here 
https://source.digital-mobility.solutions/moqo-public/aggregator-api/-/blob/master/aggregator_openapi.yaml nachlesbar.





