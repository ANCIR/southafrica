import scrapekit
import re
from pprint import pprint # noqa
from urlparse import urljoin
from itertools import count
from lxml import html
from scrapekit.util import collapse_whitespace
from common import database

QUERY = 'http://www.npo.gov.za/PublicNpo/JqGridDataTableControl/Json/PublicNpoSearch_Index?filter=&_search=false&nd=1415907408632&rows=100&page=%s&sidx=DateRegistered&sord=asc'
URL_PATTERN = "http://www.npo.gov.za/PublicNpo/Npo/DetailsAllDocs/%s"


scraper = scrapekit.Scraper('sa_npo', config={'threads': 5})


@scraper.task
def scrape_npo(url, data):
    res = database['sa_npo'].find_one(source_url=url)
    if res is not None:
        scraper.log.info("Already done: %s", data['name'])
        return
    res = scraper.get(url)
    if 'internal server error' in res.content:
        scraper.log.warning("Skipping: %s", url)
        return
    doc = html.fromstring(res.content)
    data.update({
        'source_url': url,
        'name': doc.find('.//h1').find('.//span').text.strip(),
        'status': doc.find('.//h1').find('.//span[@class="npo-status"]').text,
        'email': None
    })
    scraper.log.info("Scraping: %s", data['name'])
    sub_titles = doc.findall('.//h5')
    next_heading = None
    for sub_title in sub_titles:
        text = collapse_whitespace(sub_title.text)
        if 'Registration No' in text:
            data['reg_no'] = sub_title.find('./span').text.strip()
            next_heading = 'category'
        elif 'Your Name' in text:
            next_heading = None
        elif next_heading == 'category':
            data['category'] = text
            next_heading = 'legal_form'
        elif next_heading == 'legal_form':
            data['legal_form'] = text
            next_heading = None
    for span in doc.findall('.//span'):
        text = collapse_whitespace(span.text)
        if text is not None and 'Registered on' in text:
            match = re.search(r'\d+.\d+.\d+', text)
            if match:
                data['reg_date'] = match.group(0)
    for addr in doc.findall('.//div[@class="address"]'):
        addr_type = collapse_whitespace(addr.find('./h4').text)
        addrs = [collapse_whitespace(a) for a in
                 addr.xpath('string()').split('\n')]
        addrs = '\n'.join([a for a in addrs if len(a)][1:])
        if 'Physical' in addr_type:
            data['physical_address'] = addrs
        elif 'Postal' in addr_type:
            data['postal_address'] = addrs
        elif 'Contact' in addr_type:
            data['contact_name'] = collapse_whitespace(addr.find('./p').text)
            for li in addr.findall('.//li'):
                contact = collapse_whitespace(li.xpath('string()'))
                contact_type = {
                    'phone': 'phone',
                    'mailinfo': 'email',
                    'fax': 'fax'
                }.get(li.get('class'))
                data[contact_type] = contact
    off_div = './/li[@data-sha-context-enttype="Npo.AppointedOfficeBearer"]'
    database['sa_npo'].upsert(data, ['source_url'])
    for li in doc.findall(off_div):
        s = li.find('.//strong')
        a = s.find('./a')
        id_number = li.find('.//div/span')
        if id_number is not None:
            id_number = id_number.text
            id_number = id_number.replace('(', '')
            id_number = id_number.replace(')', '')
            id_number = id_number.strip()
            if 'Neither ID or Passport' in id_number:
                id_number = None
        officer = {
            'role': collapse_whitespace(s.text).replace(' :', ''),
            'npo_name': data['name'],
            'source_url': url,
            'officer_id': urljoin(url, a.get('href')),
            'officer_name': collapse_whitespace(a.text),
            'officer_id_number': id_number
        }
        pprint(officer)
        database['sa_npo_officer'].upsert(officer, ['source_url', 'officer_id'])


@scraper.task
def scrape_npos():
    for page in count(1):
        page_url = QUERY % page
        res = scraper.get(page_url)
        data = res.json()
        if data.get('total') < page:
            break
        for row in data.get('rows', []):
            id = row.get('id')
            cell = row.get('cell')
            npo = {
                'name': cell[2],
                'reg_no_cell': cell[3],
                'reg_status_cell': cell[4],
            }
            url = URL_PATTERN % id
            scrape_npo.queue(url, npo)

if __name__ == '__main__':
    scrape_npos.run()
