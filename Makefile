.PHONY: dev install eval lint deploy

dev:
	uvicorn app.main:app --reload --port 8000

install:
	pip install -r requirements.txt

eval:
	python eval.py

lint:
	python -m py_compile app/main.py app/pipeline/*.py app/tools/*.py app/config.py app/schemas.py app/taxonomy.py && echo "OK"

deploy:
	railway up
