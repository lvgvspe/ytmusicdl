cd /home/lucas/repos/ytmusicdl
/home/lucas/repos/ytmusicdl/.venv/bin/gunicorn api:app -b 0.0.0.0:5000 --reload