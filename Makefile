PY=env/bin/python
PIP=env/bin/pip
IN2CSV=env/bin/in2csv
PSQL=psql $(DATABASE_URI)
FREEZE=env/bin/datafreeze --db $(DATABASE_URI)
PEPCSV=env/bin/csvsql -S --db $(DATABASE_URI) --insert

CSVLOAD=env/bin/csvsql -t -S --db $(DATABASE_URI) --insert


all: install dmr wikipeps

install: env/bin/python

clean:
	rm -rf env
	rm -f data/pa/pombola.json
	rm -f data/dmr/dmr.csv
	rm -f data/wikipeps.csv

env/bin/python:
	virtualenv env
	$(PIP) install -r requirements.txt

data/pa/pombola.json:
	mkdir -p data/pa
	curl -o data/pa/pombola.json http://www.pa.org.za/media_root/popolo_json/pombola.json

pa: install data/pa/pombola.json
	python src/sa_pa_load.py

data/dmr/dmr.csv:
	$(IN2CSV) data/dmr/d1_2015.xlsx >data/dmr/dmr.csv

dmr: data/dmr/dmr.csv
	$(PY) src/dmr_load.py

data/wikipeps.csv:
	curl -o data/wikipeps.csv "https://api.morph.io/pudo/wikipeps/data.csv?key=zFa6NPAczqboYkiwPcPD&query=select%20*%20from%20%27data%27%20where%20collection%20%3D%20%27southafrica%27"

wikipeps: data/wikipeps.csv
	$(PSQL) -c "DROP TABLE IF EXISTS sa_wiki_pep"
	$(PEPCSV) --tables sa_wiki_pep data/wikipeps.csv
