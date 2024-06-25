cd /home/lucas/repos/ytmusicdl/api
/home/lucas/repos/ytmusicdl/api/.venv/bin/gunicorn api:app -b 0.0.0.0:5000 --reload