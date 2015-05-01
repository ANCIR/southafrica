import logging
import json
import requests

from common import database

log = logging.getLogger(__name__)

npo = database['sa_npo']
geo = database['sa_npo_geo']
URL = 'http://nominatim.openstreetmap.org/search'


def geocode(address):
    try:
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
        # print params
        res = requests.get(URL, params=params)
        for match in res.json():
            data = json.dumps(match)
            geo.insert({'address': address, 'match': data})
            return match

        geo.insert({'address': address, 'match': json.dumps(None)})
    except Exception, e:
        log.exception(e)


def geocode_parts(parts):
    while len(parts) > 1:
        address = ', '.join(parts)
        match = geocode(address)
        if match is not None:
            return match, len(parts)
        parts = parts[1:]


for row in list(npo.distinct('physical_address')):
    label = row.get('physical_address').replace('\n', ', ')
    address = row.get('physical_address').upper()
    address = address.replace(',', '').replace('/', '')
    address_parts = address.split('\n')
    match = geocode_parts(address_parts)
    if match is None:
        log.warning("Cannot decode: %s", label)
    else:
        addr, length = match
        log.warning("Best guess: %s is %s", label,
                    addr.get('display_name'))
