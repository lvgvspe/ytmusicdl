python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --upgrade
.venv/bin/gunicorn api:app -b 0.0.0.0:5000 --reload
