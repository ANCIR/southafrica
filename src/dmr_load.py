import os
import unicodecsv
from normality import slugify

from common import database, DATA_PATH

IN = os.path.join(DATA_PATH, 'dmr', 'dmr.csv')

table = database['sa_mines']


def convert_row(row):
    data = {}
    for key, value in row.items():
        key = slugify(key, sep='_')
        data[key] = value.strip()
    return data


def load():
    table.delete()
    with open(IN, 'rb') as fh:
        for row in unicodecsv.DictReader(fh):
            row = convert_row(row)
            if not row['mine_name']:
                continue
            table.insert(row)


if __name__ == '__main__':
    load()
