import json
import os
import dataset
import requests

engine = dataset.connect(os.environ.get('NPO_DB_URI'))
npo = engine['npo']
geo = engine['geo']
URL = 'http://nominatim.openstreetmap.org/search'


def geocode(address):
    match = geo.find_one(address=address)
    if match is not None:
        match = json.loads(match.get('match'))
        return match

    params = {
        'q': address,
        'countrycodes': 'za',
        'limit': 1,
        'format': 'json',
        'addressdetails': 1,
        'accept-language': 'en'
    }
    #print params
    res = requests.get(URL, params=params)
    for match in res.json():
        data = json.dumps(match)
        geo.insert({'address': address, 'match': data})
        return match
    
    geo.insert({'address': address, 'match': json.dumps(None)})


def geocode_parts(parts):
    while len(parts) > 1:
        address = ', '.join(parts)
        match = geocode(address)
        if match is not None:
            return match, len(parts)
        parts = parts[1:]


for row in list(npo.distinct('physical_address')):
    address = row.get('physical_address').upper()
    address = address.replace(',', '').replace('/', '')
    address_parts = address.split('\n')
    match = geocode_parts(address_parts)
    print 'final', match
