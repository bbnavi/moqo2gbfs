# Run as: ENV_SOURCE=<path to source .geojson> ENV_DEST=<path to destination folder> python geojsonToStatus.py
from argparse import ArgumentParser
import requests
import copy
from xml.etree import ElementTree as ET
import json
import os
from datetime import datetime, timedelta
import csv
import requests
import logging
from pathlib import Path


logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger("moqoToGBFS")

DEFAULT_MAX_RANGE_METERS = 30000
MIN_HOURS_AVAILABLE = 5
CARGO_BIKE_MODELS = {'E-Trike Babboe Curve-E'}

configs = {
	'BARshare': {
		'publication_base_url': 'https://data.mfdz.de/gbfs/barshare',
		'system_information_data' : { 
			"language": "de-DE",
			"name": "BARshare Barnim",
			"operator": "Kreiswerke Barnim GmbH",
			"system_id": "barshare",
			"timezone": "CET",
			"url": "https://www.barshare.de/",
			"purchase_url": "https://portal.moqo.de/js_sign_up/barshare#/team-selection",
			"email": "support@moqo.de",
			"feed_contact_email": "info@mfdz.de",
			"terms_url": "https://barshare.de/images/page/download/Agb_07_2020.pdf",
			"terms_last_updated": "2020-07-01",
			"privacy_url": "https://barshare.de/datenschutz",
			"rental_apps": {
				"android": {
					"store_uri": "https://play.google.com/store/apps/details?id=de.bebgbarnim.app",
					"discovery_uri": "https://barshare.de/yet_unknown" 
				},
				"ios": {
					"store_uri": "https://itunes.apple.com/de/app/barshare/id1463396603",
					"discovery_uri": "https://barshare.de/yet_unknown" 
				}
			}	
		},
		'pricing_plans': [
			{
				"plan_id": "mitnutzer_kleinwagen",
				"url": "https://www.barshare.de/barshare-preise-tarife",
				"name": "Mitnutzer-Tarif Kleinwagen",
				"currency": "EUR",
				"price": 2,
				"is_taxable": False,
				"description": "Standard Tarif Mitnutzer. 2€ pro Buchung, 10 Cent pro Kilometer (inkl. Stromkosten für die Nutzung des emobility Ladenetzes Barnim), 3,90€ pro Stunde. Jede erste Stunde eines neuen Stundentarifs wird jeweils voll berechnet, ab der zweiten Stunde erfolgt eine Abrechnung alle 15 Minuten. Die hier angegebenen Tarife entsprechen den Bruttopreisen in Euro inklusive der jeweils gültigen Umsatzsteuer (z.Zt. 19%).",
				"per_km_pricing": [
				  {
					"start": 0,
					"rate": 0.1,
					"interval": 1
				  }
				],
				"per_min_pricing": [
					{
						"start": 0,
						"rate": 3.9,
						"interval": 60,
						"end": 60
					},
					{
						"start": 60,
						"rate": 0.975,
						"interval": 15
					}
				]
	  		},
			{
				"plan_id": "mitnutzer_van",
				"url": "https://www.barshare.de/barshare-preise-tarife",
				"name": "Mitnutzer-Tarif Van",
				"currency": "EUR",
				"price": 2,
				"is_taxable": False,
				"description": "Standard Tarif Mitnutzer. 2€ pro Buchung, 10 Cent pro Kilometer (inkl. Stromkosten für die Nutzung des emobility Ladenetzes Barnim), 4,90€ pro Stunde. Jede erste Stunde eines neuen Stundentarifs wird jeweils voll berechnet, ab der zweiten Stunde erfolgt eine Abrechnung alle 15 Minuten. Die hier angegebenen Tarife entsprechen den Bruttopreisen in Euro inklusive der jeweils gültigen Umsatzsteuer (z.Zt. 19%).",
				"per_km_pricing": [
				  {
					"start": 0,
					"rate": 0.1,
					"interval": 1
				  }
				],
				"per_min_pricing": [
					{
						"start": 0,
						"rate": 4.9,
						"interval": 60,
						"end": 60
					},
					{
						"start": 60,
						"rate": 1.225,
						"interval": 15
					},
				]
			},
			{
				"plan_id": "mitnutzer_bike",
				"url": "https://www.barshare.de/barshare-preise-tarife",
				"name": "Mitnutzer-Tarif Bike",
				"currency": "EUR",
				"price": 1,
				"is_taxable": False,
				"description": "Standard Tarif Mitnutzer. Die hier angegebenen Tarife entsprechen den Bruttopreisen in Euro inklusive der jeweils gültigen Umsatzsteuer (z.Zt. 19%).",
				"per_min_pricing": [
					{
						"start": 0,
						"rate": 2,
						"interval": 60,
						"end": 360
					},
					{
						"start": 360,
						"rate": 0,
						"interval": 60,
						"end": 3600
					},
					{
						"start": 3600,
						"rate": 12,
						"interval": 3600
					}
				]
			}
		]
	}
}

def get_form_factor(vehicle):
	form_factor = map_car_type(vehicle['vehicle_type'])
	if form_factor == "bicycle":
		vehicle_model = vehicle['label']
		if vehicle_model in CARGO_BIKE_MODELS or 'cargo' in vehicle_model.lower() or 'lasten' in  vehicle_model.lower():
			return "other"
	return form_factor

def map_car_type(car_type):
	if car_type in {'bike'}:
		return 'bicycle'
	elif car_type in {'car', 'compact_car', 'convertible', 'demo_car', 'limousine', 'mini_car',
		'small_family_car', 'sportscar', 'vintage_car',
		'station_wagon', 'suv', 'transporter',
		'recreational_vehicle', 'van'}:
		return 'car'
	elif car_type in {'scooter'}:
		return 'moped'
	elif car_type in {'kick_scooter'}:
		return 'scooter'
	elif car_type in {'other'}:
		return 'other'
	else:
		logger.warning('Unknown car_type: %s', car_type)
		return 'other'
	
def map_fuel_type(fuel_type):
	if fuel_type in {'electric'}:
		return 'electric'
	elif fuel_type in {'super_petrol', 'diesel', 'natural_gas', 'liquid_gas', 'bio_gas',
		'hybrid_electric_petrol', 'hybrid_electric_diesel', 'hydrogen', 'plugin_hybrid_petrol', 'plugin_hybrid_diesel'}:
		return 'combustion'
	elif fuel_type in {'other_fuel'}:
		return 'electric_assist'
	else:
		logger.warning('Unknown fuel_type: %s', car_type)
		return 'other'

def default_pricing_plan_id(car_type):
	if car_type in {'bike'}:
		return 'mitnutzer_bike'
	elif car_type in {'van'}:
		return 'mitnutzer_van'
	elif car_type in {'compact_car'}:
		return 'mitnutzer_kleinwagen'
	else:
		logger.warning('No default_pricing_plan mapping for car_type %s', car_type)
		return None

def get_max_range_meters(vehicle):
	if vehicle['cruising_range'] and vehicle['fuel'] and vehicle['fuel']['cents'] > 0:
		current_range_km = vehicle['cruising_range']['value']['cents']
		charging_state = vehicle['fuel']['cents']
		return round(current_range_km / charging_state *100*1000)
	else:
		return DEFAULT_MAX_RANGE_METERS

def extract_vehicle_type(vehicle_types, vehicle):
	vehicle_model = vehicle['vehicle_model']
	id = vehicle['label']
	form_factor = get_form_factor(vehicle)
	if not vehicle_types.get(id):
		vehicle_types[id] = {
			'vehicle_type_id': id,
			'form_factor': form_factor,
			'propulsion_type': map_fuel_type(vehicle['fuel_type']),
			'max_range_meters': get_max_range_meters(vehicle),
			'name': id,
			'return_type': 'roundtrip',
			'default_pricing_plan_id': default_pricing_plan_id(vehicle['car_type'])
		}
	return id

def get_or_create_virtual_station(location, station_infos, status):
	virtual_station_id = get_station_id(location)
	if not virtual_station_id in station_infos:
		station_infos[virtual_station_id] = {
			"lat": location['lat'],
			"lon": location['lng'],
			'name': location['name'] if location['name'] else virtual_station_id,
			'station_id': virtual_station_id,
			'addresss': location['street'],
			'post_code': location['postcode'],
			'city': location['city'], # Non-standard
			'rental_methods': ['key'],
			'is_virtual_station ': True
		}

		status[virtual_station_id] = {
			"num_bikes_available": 0,
			"vehicle_types_available": {},
			"is_renting": True,
			"is_installed": True,
			"is_returning": True,
			'station_id': virtual_station_id,
			'last_reported': int(datetime.timestamp(datetime.now()))
		}

	return virtual_station_id

def get_station_id(location):
	return location['id'] if location['id'] else "{}, {}".format(location['city'], location['street'])

def extract_from_vehicles(data, status, station_infos, vehicles, vehicle_types):
	for vehicle in data['vehicles']:
		vehicle_type_id = extract_vehicle_type(vehicle_types, vehicle)
		vehicle_id = vehicle['id']
		station_id = vehicle['location']['id']
		# Workaround: Some MOQO vehicles seem to be station based but have no station id
		# ==> We create a virtual station for these...
		if station_id == None:
			station_id = get_or_create_virtual_station(vehicle['location'], station_infos, status)
		
		gbfs_vehicle = {
			'bike_id': str(vehicle_id),
			'is_reserved': True,
			'is_disabled': False,
			'vehicle_type_id': vehicle_type_id,
			'station_id': str(station_id),
		}
		if vehicle.get('cruising_range') != None and vehicle['cruising_range'].get('value'):
			gbfs_vehicle['current_range_meters'] = vehicle['cruising_range']['value']['cents'] * 1000

		vehicles[vehicle_id] = gbfs_vehicle

def update_availability_status(data, status, vehicles):
	for vehicle in data['vehicles']:
		vehicle_id = vehicle['id']
		vehicles[vehicle_id]['is_reserved'] = False
	
		station_id = get_station_id(vehicle['location'])
		station_info = status.get(station_id)
		if station_info:
			vehicle_type_id = vehicle['label']
			if not station_info["vehicle_types_available"].get(vehicle_type_id):
				station_info["vehicle_types_available"][vehicle_type_id] = 0
			station_info["vehicle_types_available"][vehicle_type_id] += 1
			station_info["num_bikes_available"] += 1
		else:
			logger.warning("No station status for %s (%s), assume free floating", vehicle_id, station_id)
			vehicles[vehicle_id].pop('station_id', None)
			vehicles[vehicle_id]['lat'] = vehicle['location']['lat']
			vehicles[vehicle_id]['lng'] = vehicle['location']['lng']

def load_stations(token, base_url):
	infos = {}
	status = {}
	vehicles = {}
	vehicle_types = {}

	default_last_reported = int(datetime.timestamp(datetime.now()))

	areas_url = base_url + 'stations'
	vehicles_url = base_url + 'vehicles'
	headers = {'Authorization': 'Bearer '+token, 'accept': 'application/json'}
	page = 1
	while True:
		areas = requests.get(areas_url+'?page='+str(page), headers=headers).json()
		for elem in areas['stations']:
			station_id = elem['id']
			station = {
				"lat": elem['lat'],
				"lon": elem['lng'],
				'name': elem['name'],
				'station_id': str(elem['id']),
				'addresss': elem['street'],
				'post_code': elem['postcode'],
				'city': elem['city'], # Non-standard
				'rental_methods': ['key'],
			}

			if elem['capacity_max']:
				station['capacity'] = elem['capacity_max']

			infos[station_id] = station

			status[station_id] = {
				"num_bikes_available": 0,
				"vehicle_types_available": {},
				"is_renting": True,
				"is_installed": True,
				"is_returning": True,
				'station_id': str(elem['id']),
				'last_reported': default_last_reported
			}

		if areas['pagination'].get('next_page'):
			page += 1
		else:
			break
		
	page = 1
	while True:
		response = requests.get(vehicles_url+'?page='+str(page), headers=headers).json()
		extract_from_vehicles(response, status, infos, vehicles, vehicle_types)
	
		if response['pagination'].get('next_page'):
			page += 1
		else:
			break

	page = 1
	available_from = datetime.now()
	available_to = available_from + timedelta(hours = MIN_HOURS_AVAILABLE)
	while True:
		params = '?page={}&from={}&until={}'.format(page, available_from, available_to)
		response = requests.get(vehicles_url+params, headers=headers).json()
		update_availability_status(response, status, vehicles)
	
		if response['pagination'].get('next_page'):
			page += 1
		else:
			break

	
	return list(infos.values()), list(status.values()), vehicle_types, vehicles

def write_gbfs_file(filename, data, timestamp, ttl=60 ):
	with open(filename, "w") as dest:
		content = {
			"data": data,
			"last_updated": timestamp,
			"ttl": ttl,
			"version": "2.2"
		}
		json.dump(content, dest, indent=2)

def gbfs_data(base_url):
	gbfs_data = { "de": {
		  "feeds": [
			{
			  "name": "system_information",
			  "url": base_url+"/system_information.json"
			},
			{
			  "name": "station_information",
			  "url": base_url+"/station_information.json"
			},
			{
			  "name": "station_status",
			  "url": base_url+"/station_status.json"
			},
			{
			  "name": "free_bike_status",
			  "url": base_url+"/free_bike_status.json"
			},
			{
			  "name": "vehicle_types",
			  "url": base_url+"/vehicle_types.json"
			},
			{
			  "name": "system_pricing_plans",
			  "url": base_url+"/system_pricing_plans.json"
			},
			
		  ]
		}}
	return gbfs_data


def station_with_available_vehicles_array(station, vehicle_types_orig, form_factor):
	new_station = copy.deepcopy(station)
	vehicle_types_available = []
	num_vehicles_available = 0
	for available_type in new_station["vehicle_types_available"]:
		if vehicle_types_orig[available_type]["form_factor"] == form_factor:
			num_available_types = new_station["vehicle_types_available"][available_type]
			vehicle_types_available.append({
				"vehicle_type_id": available_type,
				"count": num_available_types
				})
			num_vehicles_available += num_available_types
	new_station["vehicle_types_available"] = vehicle_types_available
	new_station["num_bikes_available"] = num_vehicles_available

	return new_station

def filter_by_form_factor(info_orig, status_orig, vehicle_types_orig, vehicles_orig, pricing_plans_orig, form_factor):
	
	status = []
	form_factor_map = {}
	vehicle_types = {}
	vehicles = {}
	required_stations = set()
	required_pricing_plans = set()
	for key in vehicle_types_orig:
		if vehicle_types_orig[key]["form_factor"] == form_factor:
			vehicle_types[key]= vehicle_types_orig[key]
			required_pricing_plans.add(vehicle_types[key].get("default_pricing_plan_id"))
	for key in vehicles_orig:
		vehicle = vehicles_orig[key]
		if vehicle["vehicle_type_id"] in vehicle_types:
			vehicles[key] = vehicle
			required_stations.add(vehicle.get("station_id"))
	
	info = list(filter(lambda station: station["station_id"] in required_stations, info_orig))
	for station in status_orig:
		if station["station_id"] not in required_stations:
			continue
		status.append(station_with_available_vehicles_array(station, vehicle_types_orig, form_factor))
	
	pricing_plans = list(filter(lambda pricing_plan: pricing_plan["plan_id"] in required_pricing_plans, pricing_plans_orig))
	return info, status, vehicle_types, vehicles, pricing_plans

def write_gbfs_feed(config, destFolder, info, status, vehicle_types, vehicles, form_factor = None):
	base_url = config['publication_base_url']
	pricing_plans = config.get('pricing_plans')
	system_information = copy.deepcopy(config['system_information_data'])
	if form_factor:
		base_url = "{}/{}".format(base_url, form_factor)
		destFolder = "{}/{}".format(destFolder, form_factor)
		Path(destFolder).mkdir(parents=True, exist_ok=True)
		(info, status, vehicle_types, vehicles, pricing_plans) = filter_by_form_factor(info, status, vehicle_types, vehicles, pricing_plans, form_factor)
		system_information["system_id"] = system_information["system_id"]+"-"+form_factor
		
	timestamp = int(datetime.timestamp(datetime.now()))
	write_gbfs_file(destFolder + "/gbfs.json", gbfs_data(base_url) , timestamp)
	write_gbfs_file(destFolder + "/station_information.json", {"stations": info} , timestamp)
	write_gbfs_file(destFolder + "/station_status.json", {"stations": status}, timestamp)
	write_gbfs_file(destFolder + "/free_bike_status.json", {"bikes": list(vehicles.values())}, timestamp)
	write_gbfs_file(destFolder + "/system_information.json", system_information, timestamp)
	write_gbfs_file(destFolder + "/vehicle_types.json", {"vehicle_types": list(vehicle_types.values())}, timestamp)
	if pricing_plans:
		write_gbfs_file(destFolder + "/system_pricing_plans.json", {"plans": pricing_plans}, timestamp)

def main(args, config):
	destFolder=  args.outputDir
	(info, status, vehicle_types, vehicles) = load_stations(args.token, args.baseUrl)
	write_gbfs_feed(config, destFolder, info, status, vehicle_types, vehicles, "car")
	write_gbfs_feed(config, destFolder, info, status, vehicle_types, vehicles, "bicycle")
	write_gbfs_feed(config, destFolder, info, status, vehicle_types, vehicles, "other")
	write_gbfs_feed(config, destFolder, info, status, vehicle_types, vehicles)
		
if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument("-o", "--outputDir", help="output directory the transformed files are written to", default="out")
	parser.add_argument("-b", "--baseUrl", required=True, help="baseUrl for service")
	parser.add_argument("-t", "--token", required=True, help="token for service")
	parser.add_argument("-c", "--config", required=True, help="service provider")
	args = parser.parse_args()

	main(args, configs[args.config])


