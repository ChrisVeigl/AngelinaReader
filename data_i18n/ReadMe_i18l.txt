
For internationalisation, babel and gettext are used, as outlined here:
https://phrase.com/blog/posts/python-localization/

Currently, only DE and EN are supported, but more languages could be added easily.
In order translate the german text messages / speech output messages in the python source file, 
open a commandline window and install babel and googletrans:

pip install babel
pip install googletrans==3.1.0a0

then, enter the subfolder ./data_i18n and run the translation script:

cd data_i18n
python translateMessages.py

This extracts the german messages from source file, translates them to english using googletrans (internet connection is needed) and creates the .po files

Where necessary, manually correct the englsh translations in the file data_i18n/en/LC_MESSAGES/messages.po 

and finally, run (also in subfolder ./data_i18n):

pybabel compile -d .

this creates the .mo files from the .po files (which are used by the gettext tool to retrieve the correctly localised message texts during runtime)




