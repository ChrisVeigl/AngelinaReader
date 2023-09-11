# This tool extracts all message id strings from the file 'de/LC_MESSAGES/messages.po'
# and translates the messages via the googletrans API. 
# Then, the translated messages are injected into the file 'en/LC_MESSAGES/messages.po'


import os
from googletrans import Translator, constants

translator = Translator()

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
    if (Lines[i].find('msgstr ')) > -1:
        translation = translator.translate(Messages[messageCount], dest="en")
        print ("translated: " + Messages[messageCount] + " to: " + translation.text)
        actline="msgstr "+translation.text+'\n'
        messageCount+=1
    else:
        actline=Lines[i]
    file3.writelines(actline)

file3.close()
