
pybabel extract --no-wrap --project=OBR-Reader --version=1 --copyright-holder=AsTeRICS-Foundation -o messages.pot ../run_local_camInteractive.py
pybabel init --no-wrap -l de -i messages.pot -d . 
pybabel init --no-wrap -l en -i messages.pot -d . 
python translateMessages.py
pybabel compile -d .

