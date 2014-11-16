import os
import dataset

engine = dataset.connect(os.environ.get('NPO_DB_URI'))
npo = engine['npo']

for row in list(npo.distinct('category')):
    category = row.get('category')
    c1, c2, c3 = category.split(' > ')
    data = {
        'category': category,
        'category1': c1,
        'category2': c2,
        'category3': c3
    }
    print data
    npo.update(data, ['category'])
