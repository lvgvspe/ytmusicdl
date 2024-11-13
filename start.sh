cd $HOME/repos/ytmusicdl
#cp cipher.py $HOME/repos/ytmusicdl/.venv/lib/python3.12/site-packages/pytube
$HOME/repos/ytmusicdl/.venv/bin/gunicorn api:app -b 0.0.0.0:5000 --reload
