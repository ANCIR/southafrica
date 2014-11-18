import os
import dataset

engine = dataset.connect(os.environ.get('NPO_DB_URI'))
npo = engine['npo']

for row in list(npo.distinct('category')):
    category = row.get('category')
    if category is None or not len(category):
        continue
    #print [category]
    cats = category.split(' > ')
    data = {
        'category': category,
        'category1': cats[0],
        'category2': cats[1] if len(cats) > 1 else None,
        'category3': cats[2] if len(cats) > 2 else None,
    }
    #print data
    npo.update(data, ['category'])
