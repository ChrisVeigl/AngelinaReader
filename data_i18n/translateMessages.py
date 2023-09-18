#
# Run this script in a commandline window in subfolder data_i18n.
# The script extracts all message id strings from the python sourcefile '../run_local_camInteractive.py'
# and then creates the files './de/LC_MESSAGES/messages.po' and './en/LC_MESSAGES/messages.po'
# Then, it translates the german messages to english via the googletrans API. 
# (the translated messages are injected into the file './en/LC_MESSAGES/messages.po')
#
# if the script does not work, following procedure can be applied manually:
#
#    - create the messages.pot file using following command in the AngelinaReader root folder:
#      pybabel extract -o messages.pot ../run_local_camInteractive.py --no-wrap
# 
#    - create the language-specific .po-files: 
#      pybabel init -l de -i messages.pot -d . --no-wrap
#      pybabel init -l en -i messages.pot -d . --no-wrap
#
#    - manually translate the msgstr strings in file ./en/LC_MESSAGES/messages.po 
#
#    - compile the .mo files:
#      pybabel compile -d . 
#
#


import os

from babel.messages.frontend import CommandLineInterface
from googletrans import Translator, constants

translator = Translator()

CommandLineInterface().run(['pybabel','extract','-o','messages.pot','../run_local_camInteractive.py ','--no-wrap'])
CommandLineInterface().run(['pybabel','init','-l','de','-i','messages.pot', '-d', '.', '--no-wrap'])
CommandLineInterface().run(['pybabel','init','-l','en','-i','messages.pot', '-d', '.', '--no-wrap'])


file1 = open('de/LC_MESSAGES/messages.po', 'r', encoding='utf-8', errors='ignore')
Lines = file1.readlines()
file1.close()
file2 = open('messages.txt', 'w', encoding='utf-8', errors='ignore')

if (len (Lines) > 1):
    for i in range (len(Lines)):
        if (Lines[i].find('msgid ')) > -1:
            print (Lines[i][6:].strip())
            file2.writelines(Lines[i][6:])


file2.close()


file1 = open('messages.txt', 'r', encoding='utf-8', errors='ignore')
Messages = file1.readlines()
file1.close()

file2 = open('en/LC_MESSAGES/messages.po', 'r', encoding='utf-8', errors='ignore')
Lines = file2.readlines()
file2.close()

file3 = open('en/LC_MESSAGES/messages.po', 'w', encoding='utf-8', errors='ignore')

messageCount=0
actline=""
for i in range (len(Lines)):
    actline=Lines[i]
    if (Lines[i].find('msgstr ')) > -1:
        translation = translator.translate(Messages[messageCount], dest="en")
        print ("translated: " + Messages[messageCount] + " to: " + translation.text)
        actline="msgstr "+translation.text+'\n'
        messageCount+=1
    file3.writelines(actline)

file3.close()

CommandLineInterface().run(['pybabel','compile','-d','.'])


print ("Done.")
print ("Now verify the english translation './en/LC_MESSAGES/messages.po' and run 'pybabel compile -d .'")

