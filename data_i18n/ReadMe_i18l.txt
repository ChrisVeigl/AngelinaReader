
For internationalisation, babel and gettext are used, as outlined here:
https://phrase.com/blog/posts/python-localization/

Currently, only DE and EN are supported, but more languages could be added easily.
In order to modify or update text messages / speech output messages, first install babel:

pip install babel

then, create the messages.pot file using following command in the AngelinaReader root folder:

pybabel extract -o data_i18n/messages.pot run_local_camInteractive.py --no-wrap

then, create the language-specific .po-files: 

pybabel init -l de -i data_i18n/messages.pot -d data_i18n/ --no-wrap
pybabel init -l en -i data_i18n/messages.pot -d data_i18n/ --no-wrap

these .po-files can now be translated using the script translateMessages.py

cd data_i18n
python translateMessages.py

This translates the messages from german to english automatically via googletranslate (internet connection is needed)

Where necessary, manually correct the translations in the file data_i18n/en/LC_MESSAGES/messages.po 


Finally, run:

cd ..
pybabel compile -d data_i18n/

this creates the .mo files from the .po files (the .mo files are used by the gettext tool to retrieve the correctly localised message texts during runtime)



