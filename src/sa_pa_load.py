import os
import json
import logging
# from pprint import pprint

from common import database, DATA_PATH

log = logging.getLogger('pa')

DATA_FILE = os.path.join(DATA_PATH, 'pa', 'pombola.json')
pa_parties = database['sa_pa_parties']
pa_committees = database['sa_pa_committees']
pa_persons = database['sa_pa_persons']
pa_memberships = database['sa_pa_memberships']
pa_directorships = database['sa_pa_directorships']
pa_financial = database['sa_pa_financial']
pa_aliases = database['sa_pa_aliases']


def load_interests(person, register):
    for report, sections in register.items():
        for section, items in sections.items():
            for item in items:
                if 'DIRECTORSHIP' in section:
                    company = item.get('Directorship/Partnership')
                    if company is None or not len(company.strip()):
                        continue
                    data = {
                        'person_name': person['name'],
                        'person_id': person['popit_id'],
                        'report': report,
                        'company_name': company.strip(),
                        'company_type': item.get('Type of Business')
                    }
                    pa_directorships.upsert(data, ['person_id', 'report',
                                                   'company_name'])
                if 'FINANCIAL INTERESTS' in section:
                    company = item.get('Name of Company')
                    if company is None or not len(company.strip()):
                        continue
                    data = {
                        'person_name': person['name'],
                        'person_id': person['popit_id'],
                        'report': report,
                        'company_name': company.strip(),
                        'nature': item.get('Nature'),
                        'number': item.get('No'),
                        'nominal_value': item.get('Nominal Value')
                    }
                    pa_financial.upsert(data, ['person_id', 'report',
                                               'company_name'])


def load_persons(data, orgs):
    for person in data:
        name = person.get('name').strip()
        if name is None:
            continue
        name = name.strip()
        if not len(name):
            continue
        log.info("Loading person: %s", name)
        data = {
            'name': name,
            'popit_id': person.get('id'),
            'pa_url': person.get('pa_url'),
            'given_name': person.get('given_name'),
            'family_name': person.get('family_name'),
            'summary': person.get('summary'),
            'telephone_number': None,
            'email': None
        }

        for contact in person.get('contact_details', []):
            if contact.get('type') == 'voice':
                data['telephone_number'] = contact.get('value')
            if contact.get('type') == 'email':
                data['email'] = contact.get('value')

        pa_persons.upsert(data, ['popit_id'])

        load_interests(data, person.get('interests_register', {}))

        for name in person.get('other_names', []):
            pa_aliases.upsert({
                'alias': name['name'],
                'canonical': data['name']
            }, ['alias', 'canonical'])

        for membership in person.pop('memberships'):
            org_id = membership.get('organization_id')
            if org_id not in orgs:
                continue
            mem = {
                'organization_id': org_id,
                'organization_name': orgs[org_id].get('name'),
                'role': membership.get('role'),
                'person_id': data['popit_id'],
                'person_name': data['name'],
                'start_date': membership.get('start_date'),
                'end_date': membership.get('end_date')
            }
            pa_memberships.upsert(mem, ['organization_id', 'person_name',
                                        'role'])


def load_organizations(data):
    orgs = {}
    for org in data:
        log.info("Loading organisation: %s", org.get('name'))
        clazz = org.get('classification')
        data = {
            'name': org.get('name'),
            'popit_id': org.get('id'),
            'pa_url': org.get('pa_url'),
            'org_category': org.get('category'),
            'org_classification': clazz
        }

        if clazz == 'Party':
            pa_parties.upsert(data, ['popit_id'])
            orgs[org.get('id')] = data
        elif 'Committee' in clazz:
            pa_committees.upsert(data, ['popit_id'])
            orgs[org.get('id')] = data
    return orgs


def load():
    with open(DATA_FILE, 'rb') as fh:
        data = json.load(fh)
        orgs = load_organizations(data['organizations'])
        load_persons(data['persons'], orgs)


if __name__ == '__main__':
    load()
