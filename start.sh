cd $HOME/repos/ytmusicdl
source .venv/bin/activate
pip install -r requirements.txt --upgrade
$HOME/repos/ytmusicdl/.venv/bin/gunicorn api:app -b 0.0.0.0:5000 --reload
