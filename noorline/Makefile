PY=.venv/bin/python
.PHONY: install test demo serve node node-prod data diagram
install: ; ./install.sh
test: ; $(PY) -m pytest -q
demo: ; $(PY) -W ignore -m noorline.demo
data: ; $(PY) scripts/make_data.py && $(PY) -c "from noorline.intent import IntentClassifier as C; C.train()"
serve: ; $(PY) -m uvicorn --factory noorline.server:create_app --host 0.0.0.0 --port 8000
node: ; $(PY) -m noorline.cli --server http://localhost:8000
node-prod: ; $(PY) -m noorline.cli --server $(URL)
diagram: ; $(PY) scripts/make_diagram.py
