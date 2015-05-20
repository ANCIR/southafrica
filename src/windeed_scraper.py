import os
import logging
from time import time
from itertools import count
from urlparse import urljoin
import requests

from common import database, DATA_PATH

log = logging.getLogger(__name__)
URL = 'https://www.windeedsearch.co.za/'
table = database['sa_cipc_windeed']


def collapse_whitespace(text):
    return text


def download_pdf(session, data):
    key = data.get('DbKey')
    file_name = 'windeed_' + str(key) + '.pdf'
    file_name = os.path.join(DATA_PATH, 'windeed', 'pdf', file_name)
    if not os.path.exists(file_name):
        dir_name = os.path.dirname(file_name)
        try:
            os.makedirs(dir_name)
        except:
            pass
        url = urljoin(URL, '/Cipc/OtherPrintout/%s?format=Pdf' % key)
        res = session.get(url)
        with open(file_name, 'wb') as fh:
            fh.write(res.content)
    return file_name


def box_to_kv(block, prefix=None):
    data = {}
    for row in block.findall('./div[@class="result-section-row"]'):
        label = None
        for div in row.findall('./div'):
            clazz = div.get('class')
            if 'result-label' in clazz:
                label = collapse_whitespace(div.text_content())
            else:
                value = collapse_whitespace(div.text)
                if not len(value) or value == '-':
                    value = None
                if prefix:
                    label = '%s %s' % (prefix, label)
                data[label] = value
                label = None
    return data


def login_session(session):
    url = urljoin(URL, '/Account/LoginByEmailPartial')
    params = {
        'GetCampaigns': 'True',
        'EmailIntegrationMode': 'False',
        'EmailAddress': os.environ.get('WINDEED_USER'),
        'Password': os.environ.get('WINDEED_PASS'),
        'RememberMe': 'true',
        'submitemail': 'Log%20In',
    }
    res = session.get(url, params=params)
    assert res.json().get('success'), res.json()


def all_results(session):
    url = urljoin(URL, '/Client/AllResultsList')
    for page_no in count(1):
        params = {
            'SortOrder': 'Descending',
            'ColumnToSortBy': 'SearchDate',
            'firstLoad': 'false',
            'dateFilter': '4',
            'userScope': '1',
            'ResultCategoryFilter': '0',
            '_search': 'false',
            'nd': str(int(time() * 1000)),
            'rows': '50',
            'page': page_no,
            'sidx': 'SearchDate',
            'sord': 'desc'
        }
        res = session.post(url, params)
        data = res.json()
        for row in data.get('Data'):
            scrape_result(session, row)

        if page_no >= data.get('Total'):
            break


def scrape_result(session, data):
    url = urljoin(URL, data.get('SearchAction'))
    if 'Cipc' not in url:
        return
    data['url'] = url
    # data['pdf'] = download_pdf(session, data)
    if 'DirectorResult' in url:
        director_details(session, data)
    if 'CompanyResult' in url:
        company_details(session, data)


def director_details(session, data):
    doc = session.get(data['url'], cache='force').html()
    for block in doc.findall('.//div[@class="result-section-block"]'):
        prof = block.find('./a[@rel="DirectorCompanyProfile"]')
        if prof is None:
            continue
        title = collapse_whitespace(block.findtext('./h4'))
        _, title = title.split('COMPANY:', 1)
        title, _ = title.rsplit('(', 1)
        title = map(collapse_whitespace, title.rsplit(', ', 1))
        company_name, company_regno = title
        data['company_name'] = company_name
        data['company_regno'] = company_regno
        data.update(box_to_kv(block, prefix="CIPC"))
        log.info("Director's details: %s" % company_name)
        # csv.write('windeeds/windeeds_directors.csv', data)


def company_details(session, data):
    doc = session.get(data['url'], cache='force').html()
    for block in doc.findall('.//div[@class="result-block"]'):
        if block.find('./a[@name="CompanyInformation"]') is None:
            continue
        data.update(box_to_kv(block, prefix="CIPC-Company"))

    for block in doc.findall('.//div[@class="result-section-block"]'):
        prof = block.find('./a[@rel="Directors"]')
        if prof is None:
            continue
        title = collapse_whitespace(block.findtext('./h4'))
        title, _ = title.rsplit(' - ', 1)
        data['director_name'] = collapse_whitespace(title)
        log.info("Company details: %s" % data['director_name'])
        data.update(box_to_kv(block, prefix="CIPC-Person"))
        # csv.write('windeeds/windeeds_companies.csv', data)


def scrape():
    session = requests.Session()
    login_session(session)
    all_results(session)


if __name__ == '__main__':
    scrape()
