cd $HOME/repos/ytmusicdl
$HOME/repos/ytmusicdl/.venv/bin/gunicorn api:app -b 0.0.0.0:5000 --reload
