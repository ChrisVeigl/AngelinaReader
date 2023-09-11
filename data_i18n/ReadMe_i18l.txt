
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

these .po-files can now be translated. In case no translation (msgstr) is added, the message id (msgid) will be be used as default text.


Finally, run:

pybabel compile -d data_i18n/

this creates the .mo files from the .po files (the .mo files are used by the gettext tool to retrieve the correctly localised message texts during runtime)

scripts which automate the process are provided in folder /data_i18n
(translateMessages.py translates the messages automatically via googletranslate)


