# source venv/bin/activate

all:
	./venv/bin/python3 run.py

create:
	python3 -m venv venv
	source venv/bin/activate && \
		pip install -r requirements.txt

redirect:
	ngrok http 9090