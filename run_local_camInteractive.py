#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Optical Braille Recognition - speech guided interactive user interface for Angelina Reader
#
# This script either processes either
#   a) single frames from a live webcam video or 
#   b) existing images (in folder args.input_dir) 
#
# Place braille sheets (or book) on a dark background.
# Set up light and camera as described here: https://angelina-reader.ru/help/#how_to_photo
# When processing images, the script seperates bright area from background, 
# then decides if orientation is portrait (1 page) or landscape (2 pages, book),
# in case of landscape orientation extracts 2 single pages,
# then performs optical braille recognition using Angelina Reader
# and optionally speaks out results using pyttsx3 / picoTTS
#
# thanks to:
#   https://www.codegrepper.com/code-examples/python/python+capture+image+from+webcam
#   https://stackoverflow.com/questions/13887863/extract-bounding-box-and-save-it-as-an-image
#   https://github.com/IlyaOvodov/AngelinaReader
#


import cv2
import os
import glob
import argparse
from pathlib import Path
from pygame import mixer
import gettext

import local_config
import model.infer_retinanet as infer_retinanet


translations = {}
supported_langs = ['en', 'de']

# load translation files dynamically
for lang in supported_langs:
    translations[lang] = gettext.translation('messages', localedir='data_i18n', languages=[lang])


# Initialize the speech synthesizer and other OS-dependent resources

BACKSPACE_KEY = 8
ESCAPE_KEY = 27
ENTER_KEY = 13

if os.name=='nt':
    onWindows=True
    import pyttsx3
    voiceSpeed=200
    UP_ARROW_KEY = 2490368
    DOWN_ARROW_KEY = 2621440   
    LEFT_ARROW_KEY = 2424832
    RIGHT_ARROW_KEY = 2555904
    PAGEUP_KEY = 2162688
    PAGEDOWN_KEY = 2228224
    DEL_KEY = 3014656
    INSERT_KEY = 2949120
    RIGHTSHIFT_KEY = 65505  # TBD
    LEFTSHIFT_KEY = 65506   # TBD
    
else:
    onWindows=False
    #from gtts import gTTS
    voiceSpeed=150
    UP_ARROW_KEY = 65362
    DOWN_ARROW_KEY = 65364
    LEFT_ARROW_KEY = 65361
    RIGHT_ARROW_KEY = 65363
    PAGEUP_KEY = 65365
    PAGEDOWN_KEY = 65366
    DEL_KEY = 65535
    INSERT_KEY = 65379
    RIGHTSHIFT_KEY = 65505
    LEFTSHIFT_KEY = 65506


# file paths and filename prefixes
model_weights = 'model.t7'
results_dir = './results'
results_prefix = 'Seite'

MIN_AREA=100000   # for detecting a valid page
WINDOW_WIDTH=700  # for displaying result windows

langMapping = {
	"DE": ["de-DE","German"],
	"EN": ["en-US","English"]
}

lastKey=-1
img_counter = 1
fromCam=False
readLinenumbers=True
replaceKey=False
frame=None
cam=None
fn=0
PAGEMODE=1
READMODE=2
EDITMODE=3
mode=PAGEMODE



def announce (text):
    global fn
    global lastKey

    if (len(text)==0):
        announce (_("leere Zeile"))
        return
        
    print(text, flush=True)
    if (args.silent == True):
        return
    
    if onWindows == True:
        # speechSynthesizer.say(text)
        fn = (fn+1) % 2  # a workaround because ttsx3 does not close the most recent file correctly
        tempFile="temp{}.wav".format(fn)
        speechSynthesizer.setProperty('rate', voiceSpeed)
        speechSynthesizer.save_to_file(text, tempFile)
        speechSynthesizer.runAndWait()
        speechSynthesizer.stop()
    else:
        # use google TTS
        #tts = gTTS(text, lang='de')
        #tts.save("temp.mp3")
        
        # use PicoTTS
        os.system('pico2wave --lang={} -w pico.wav "{}"'.format(langMapping.get(args.UIlang)[0],text))
        os.system("sox " + "pico.wav temp.wav tempo {}".format(voiceSpeed/100))
        tempFile="temp.wav"

    # using pygame mixer to interrupt/pause voice playback!
    
    try:
        if (os.path.getsize(tempFile) > 500):  # sanity check to prevent empty soundfile
            mixer.music.load(tempFile)        
            mixer.music.play()
    except:
        print (_("Could not play music file (maybe empty)!"))
    
    pause=False
    lastKey=-1
    while (mixer.music.get_busy() and lastKey==-1) or (pause == True):
        lastKey = cv2.waitKeyEx(10)
        if lastKey == 27:         # ESC: end readout
                mixer.music.stop()
        if lastKey == ord('p'):   # p: pause/resume ongoing speech output
            if pause==False:
                mixer.music.pause()                
            else:
                mixer.music.unpause()
                lastKey=-1
            pause = not pause

def expandUnreadableCharacters(line,expandSpaceKey):
    if (expandSpaceKey==True):
        line=line.replace(" ",  _("Leertaste")+" ") 
    line=line.replace("(",  " "+_("runde Klammer öffnen")+" ")
    line=line.replace(")",  " "+_("runde Klammer schließen")+" ")
    line=line.replace("~",  " "+_("unbekannt")+" ")
    line=line.replace("\"", " "+_("Hochkomma")+" ")
    line=line.replace(":",  " "+_("Doppelpunkt")+" ")
    line=line.replace(";",  " "+_("Strichpunkt")+" ")
    line=line.replace(",",  " "+_("Beistrich")+" ")
    line=line.replace(".",  " "+_("Punkt")+" ")
    line=line.replace("-",  " "+_("Minus")+" ")
    line=line.replace("+",  " "+_("Plus")+" ")
    line=line.replace("*",  " "+_("Stern")+" ")
    line=line.replace("!",  " "+_("Rufzeichen")+" ")
    line=line.replace("?",  " "+_("Fragezeichen")+" ")
    return(line)

def exportResults():
    actFile=1    
    results_name = "{}result.txt".format(results_dir)
    resultsFile = open(results_name, 'w', encoding='utf-8', errors='ignore')
    while True:
        marked_name = "{}{}{:04d}.marked.txt".format(results_dir,results_prefix,actFile)
        if (os.path.exists(marked_name)):
            file1 = open(marked_name, 'r', encoding='utf-8', errors='ignore')
            Lines = file1.readlines()
            file1.close()
            resultsFile.writelines(Lines)
        else:
            break
        actFile+=1

    resultsFile.close()


def readResult():
    global img_counter
    global readLinenumbers
    global lastKey
    global replaceKey
    global mode

    announce(_("Lesen und Editieren Seite {}").format(img_counter))

    marked_name = "{}{}{:04d}.marked.txt".format(results_dir,results_prefix,img_counter)
    marked_jpg = "{}{}{:04d}.marked.jpg".format(results_dir,results_prefix,img_counter)    

    if (not os.path.exists(marked_name)) or (not os.path.exists(marked_jpg)):
        announce (_("Ergebnisdateien für diese Seite nicht vorhanden, bitte zuerst Bild verarbeiten"))
        return

    file1 = open(marked_name, 'r', encoding='utf-8', errors='ignore')
    Lines = file1.readlines()
    file1.close()
    if (len (Lines) < 1):
        announce (_("es konnten keine Ergebnisse für diese Seite gefunden werden"))
        return
    for i in range (len(Lines)):
        Lines[i]=Lines[i].replace("~?~", "~")
    
        
    windowName="OBR-Ergebnis Seite {}".format(img_counter)
    cv2.namedWindow(windowName)
    cv2.moveWindow(windowName, 50+WINDOW_WIDTH,40)
    img = cv2.imread(marked_jpg)
    cv2.imshow(windowName, resizeImg(img))
      
    actLine = 0
    actLetter = -1
    readNextLetter = False
    readNextLine = True
    linesChanged=False
    mode=READMODE
    
    while mode!=PAGEMODE:

        if mode==READMODE:
            lastKey=-1
            if readNextLine == True:
                line=Lines[actLine]
                line=expandUnreadableCharacters(line, False)
                if (readLinenumbers==True):
                    announce(_("Zeile{}: {}").format(actLine+1, line.strip()))
                else:
                    announce(line.strip())
            elif readNextLetter == True:
                line=Lines[actLine]
                letter=line[actLetter]
                announce(expandUnreadableCharacters(letter,True))
                readNextLetter=False
            if lastKey==-1:
                lastKey = cv2.waitKeyEx(10)                

            if (lastKey == UP_ARROW_KEY and actLine > 0):
                actLine-=1
                readNextLetter=False
                readNextLine=True

            elif (lastKey == DOWN_ARROW_KEY and actLine < len(Lines)):
                actLine+=1
                actLetter=-1
                readNextLetter=False
                readNextLine=True

            elif lastKey == RIGHT_ARROW_KEY:
                readNextLine=False
                if (actLetter<len(line)-2):
                    readNextLetter=True
                    actLetter+=1
                else:
                    announce(_("Zeilenende"))
                    #actLetter=len(line)

            elif lastKey == LEFT_ARROW_KEY: 
                readNextLine=False
                if (actLetter>0):
                    readNextLetter=True
                    actLetter-=1
                else:
                    announce(_("Zeilenanfang"))
                    #actLetter=-1

            elif lastKey == ord('z'):
                readLinenumbers = not readLinenumbers
                if (readLinenumbers==True):
                    announce(_("Zeilennummern werden vorgelesen"))
                else:
                    announce(_("Zeilennummern werden nicht vorgelesen"))

            elif lastKey == ord('h'):
                printHelpReadmode()
                readNextLine=False

            if readNextLine==False:
                if lastKey == BACKSPACE_KEY:
                    announce (_("1 drücken für Zeichen löschen, 2 für Zeile löschen"))
                    option=getOption(2)
                    if option == 1:
                        if (actLetter<1):
                            Lines[actLine] = Lines[actLine][1:]
                        else:
                            Lines[actLine] = Lines[actLine][:actLetter] + Lines[actLine][actLetter+1:]
                        announce (_("Zeichen gelöscht"))
                        linesChanged=True
                    if option == 2:
                        Lines=Lines[:actLine]+Lines[actLine+1:]
                        announce (_("Zeile gelöscht"))
                        linesChanged=True
                    
                elif lastKey == INSERT_KEY:
                    announce (_("1 drücken für Zeichen einfügen, 2 für Zeile einfügen"))
                    option=getOption(2)
                    if (option == 1):
                        Lines[actLine]= Lines[actLine][:actLetter+1] + ' ' + Lines[actLine][actLetter+1:]
                        announce (_("Leerzeichen eingefügt"))
                        linesChanged=True
                    elif (option == 2):
                        Lines.insert(actLine," ")
                        announce (_("Leere Zeile eingefügt"))
                        linesChanged=True
                        
                elif lastKey == DEL_KEY:
                    announce (_("Ersetze Buchstabe ")+expandUnreadableCharacters(letter,True))
                    mode=EDITMODE
                    lastKey=0

        if mode==EDITMODE:
            lastKey = cv2.waitKeyEx(10)
            if (lastKey>0) and (lastKey!=LEFTSHIFT_KEY) and (lastKey!=RIGHTSHIFT_KEY):  
                if (lastKey<0x110000):
                    strlist = list(line)
                    strlist[actLetter] = chr(lastKey)
                    letter=chr(lastKey)
                    announce (_("Ersetzt durch ")+expandUnreadableCharacters(chr(lastKey),True))
                    line = ''.join(strlist)
                    # print (line, flush=True)
                    Lines[actLine]=line
                    linesChanged=True
                else:
                    announce (_("Ersetzen beendet"))
                mode=READMODE     

        if (lastKey == -1) and (readNextLine == True):   # no key -> progress to next line!
            if (actLine < len (Lines)):
                actLine+=1
            else:
                readNextLine=False
                
        if (lastKey == ESCAPE_KEY):
            actLine = len(Lines)
            announce (_("Lesemodus beendet"))
            if linesChanged ==True:
                announce (_("Sollen die Änderungen gespeichert werden?"))
                if getYesNo()==True:
                    announce(_("ja"))
                    file1 = open(marked_name, 'w', encoding='utf-8', errors='ignore')
                    file1.writelines(Lines)
                    file1.close()
                else:
                    announce(_("nein"))
            mode=PAGEMODE
      
    cv2.destroyWindow(windowName)
    
    
def process_image (img,x,y,w,h):
    global img_counter

    ROI = img[y:y+h, x:x+w]
    frameCopy = img.copy()
    cv2.rectangle(frameCopy,(x,y),(x+w,y+h),(10,10,255),2)
    cv2.imshow("brailleImage", resizeImg(frameCopy))
    cv2.waitKey(1)

    img_name = "{}{}{:04d}".format(results_dir,results_prefix,img_counter)
    if (os.path.exists(img_name+".marked.brl")==True):
        os.remove(img_name+".marked.brl")
    if (os.path.exists(img_name+".marked.txt")==True):
        os.remove(img_name+".marked.txt")
    if (os.path.exists(img_name+".marked.jpg")==True):
        os.remove(img_name+".marked.jpg")
        
    img_name=img_name+".png"
    
    cv2.imwrite(img_name, ROI)
    recognizer.run_and_save(img_name, results_dir, target_stem=None,
                                           lang=args.lang, extra_info=None,
                                           draw_refined=recognizer.DRAW_NONE,
                                           remove_labeled_from_filename=False,
                                           find_orientation=args.orient,
                                           align_results=True,
                                           process_2_sides=False,
                                           repeat_on_aligned=False,
                                           save_development_info=False)


def slice_and_process_image(frame):
    global img_counter
    if frame is None:
        announce (_("Bildaten für Seite {} nicht vorhanden, Verarbeitung nicht möglich").format(img_counter))
        return
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray,0,255,cv2.THRESH_OTSU + cv2.THRESH_BINARY)[1]
    #cv2.imshow('thresh', thresh)

    # find contours of biggest bounding rectangle
    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    maxArea=0
    actIndex=0
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        if maxArea < w*h:
            maxArea= w*h
            maxContour=c
        actIndex+=1

    if (maxArea>MIN_AREA):
        x,y,w,h = cv2.boundingRect(maxContour)
        print("w: {}, h: {}, area: {}, ratio: {}".format(w,h,w*h,w/h), flush=True)
        if (w/h < 1.3 ):  # assume page with portrait orientation, extract 1 page
            process_image(frame,x,y,w,h)
                            
        else:   # assume book with landscape orientation, extract 2 pages!
            announce(_("Doppelseite erkannt, verarbeite linke Seite"))
            half_w=round(w/2)
            process_image(frame,x,y,half_w,h)
            img_counter += 1
            announce(_("verarbeite rechte Seite"))
            process_image(frame,x+half_w,y,half_w,h)
    else:
        announce(_("keine Seite erkannt")); 

def processFolder (importPath):
    global img_counter
    removeResults()
    img_files = list(Path(importPath).glob("*"))
    
    for img_file in img_files:
        ext = os.path.splitext(img_file)[-1].lower()
        if (ext==".jpg" or ext==".png") and (not ".marked" in os.path.basename(img_file)):
            announce('Verarbeite Seite {} aus Datei {}'.format(img_counter,os.path.basename(img_file)))
            frame = cv2.imread(str(img_file))
            slice_and_process_image(frame)
            img_counter += 1
    if (img_counter > 1):
        img_counter-=1


def removeResults():
    global img_counter
    announce(_("Lösche alle bestehenden Ergebnisdateien."))
    img_counter=1
    files = glob.glob('{}*'.format(results_dir))
    for f in files:
        os.remove(f)     
        
def getYesNo():
    while (True):
        k=cv2.waitKey(10)
        if k==ord('j') or k==ord('y'):
            return True
        if k==ord('n'):
            return False
        if k==-1 or k==0 or k==255:
            continue
        else:
            announce(_("bitte j für ja oder n für nein drücken"))

def getOption(max):
    while (True):
        k=cv2.waitKey(10)
        if k>=ord('1') and k<=ord('1')+max:
            return k-ord('1')+1
        if k%256==ESCAPE_KEY:
            announce(_("Auswahl abgebrochen"))
            return(-1)
        if k==-1 or k==0 or k==255:
            continue
        else:
            announce(_("bitte Option mit den Zifferntasten wählen oder Escape zum Abbrechen drücken"))


def resizeImg(image):
    (h, w) = image.shape[:2]
    r = WINDOW_WIDTH / float(w)
    dim = (WINDOW_WIDTH, int(h * r))
    return cv2.resize(image, dim, cv2.INTER_AREA)

def openCamera():
    global cam
    global fromCam
    # checks the first 10 cams!
    i = 0
    while i < 10:
        print("checking Camera {}".format(i))
        cam = cv2.VideoCapture(i)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
        ret, frame = cam.read()
        if ret:        
        # if cam.read()[0]:
            cv2.imshow("brailleImage", resizeImg(frame))
            announce (_("Kamera Index {} gefunden, Name:{}").format(i,cam.getBackendName()))
            announce (_("diese Kamera verwenden?"));
            if getYesNo()==True:
                announce (_("ja"))
                fromCam=True
                break
            else:
                announce (_("nein"))
                cam.release()
        i+=1       

def printHelp():
    announce(_("Taste h: Hilfetext Hauptmenü"))
    announce(_("Taste k: zwischen Kamera und Bilddateien wechseln"))
    announce(_("Leertaste: Übersetzung der aktuellen Seite starten"))
    announce(_("Bildtaste rauf: vorige Seite"))
    announce(_("Bildtaste runter: nächste Seite"))
    announce(_("Entertaste: zum Lesemodus wechseln"))
    announce(_("Plustaste: schneller sprechen"))
    announce(_("Minustaste: langsamer sprechen"))
    announce(_("Taste l: löschen aller bestehenden Bild- und Ergebnisdateien"))
    announce(_("Escape: Programm beenden und Textdatei speichern"))

def printHelpReadmode():
    announce(_("Taste h: Hilfetext Lesemodus"))
    announce(_("Pfeiltaste rauf: vorige Zeile"))
    announce(_("Pfeiltaste runter: nächste Zeile"))
    announce(_("Pfeiltaste links: voriges Zeichen"))
    announce(_("Pfeiltaste rechts: nächstes Zeichen"))
    announce(_("Entfernen: Zeichen ersetzen"))
    announce(_("Einfügen: Leerzeichen oder leere Zeile einfügen"))
    announce(_("Backspace: Zeichen oder Zeile löschen"))
    announce(_("Taste z: Zeilennummern vorlesen oder nicht"))
    announce(_("Taste p: Pausieren der laufenden Sprachausgabe"))
    announce(_("Escape: Lesemodus beenden"))


def selectVoice(engine, language):
    for voice in engine.getProperty('voices'):
        print (voice)
        #print(voice.languages)
        #if language in voice.languages:   # didnt work under windows..
        if voice.name.find(langMapping.get(language)[1]) > 0:
            engine.setProperty('voice', voice.id)
            return True

    raise RuntimeError("Language '{}' not found".format(language))


#
# program execution starts here!
#

parser = argparse.ArgumentParser(description='Angelina Braille Reader: optical Braille text recognizer - interactive version using camera input.')
parser.add_argument('input', nargs='?', type=str, help='(optional): Input source to be processed: directory name or "camera". If not specified, existing files in results folder will be used')
#parser.add_argument('results_dir', type=str, help='Output directory for results.')
parser.add_argument('-l', '--lang', type=str, default='DE', help='Document language (RU, EN, DE, GR, LV, PL, UZ or UZL). If not specified, default is DE')
parser.add_argument('-u', '--UIlang', type=str, default='DE', help='User interface language (EN, DE). If not specified, default is DE')
parser.add_argument('-o', '--orient', action='store_false', help="Don't find orientation, use original file orientation (faster)")
parser.add_argument('-s', '--silent', action='store_true', help="silent mode, do not generate speech output")
#parser.add_argument('-2', dest='two', action='store_true', help="Process 2 sides")
args = parser.parse_args()

results_dir=os.path.join(results_dir, '')  # add trailing slash if necessary
if not Path(results_dir).exists():
    print('results directory does not exist: ' + results_dir)
    exit()


# set active locale
if args.UIlang.lower() in supported_langs:
    translations[args.UIlang.lower()].install(names=['gettext', 'ngettext'])
else:
    translations['de'].install(names=['gettext', 'ngettext'])

# Initialize the speech synthesizer and try to selet voice for locale
if onWindows==True:
    speechSynthesizer = pyttsx3.init()
    selectVoice(speechSynthesizer, args.UIlang) 
    voiceSpeed=200
    #speechSynthesizer.setProperty('volume', 0.7)
else:
    voiceSpeed=150

mixer.init()

# welcome message
announce(_("Programm startet ..."))

# Initialize the webcam and opencv, create live window
cv2.namedWindow("brailleImage", cv2.WINDOW_AUTOSIZE)
cv2.moveWindow("brailleImage", 10,50)

# Initialize the Braille recognizer
recognizer = infer_retinanet.BrailleInference(
    params_fn=os.path.join(local_config.data_path, 'weights', 'param.txt'),
    model_weights_fn=os.path.join(local_config.data_path, 'weights', model_weights),
    create_script=None)

if args.input:
    if (args.input=='camera'):
        openCamera()
    else:
        announce(_("Verarbeite Dateien aus Verzeichnis ")+args.input)
        processFolder(args.input)
        announce(_("Verarbeitung abgeschlossen"))
        img_counter=1

announce (_("Bereit. Taste h für Hilfe drücken."));
updateImage = True

# main loop
while True:
    actfile="{}{}{:04d}.png".format(results_dir,results_prefix,img_counter)

    if updateImage == True:
        if (fromCam==True):
            if cam==None:
                openCamera()
            ret, frame = cam.read()
            if not ret:
                announce(_("Kamera konnte Seite {} nicht aufnehmen.").format(img_counter))
                # fromCam=False
                updateImage=False
        elif (os.path.exists(actfile)==True):
            frame = cv2.imread(actfile)
            updateImage=False
        else:
            announce(_("Datei für Seite {} nicht vorhanden").format(img_counter))
            updateImage=False
            continue

    if frame is not None:
        cv2.imshow("brailleImage", resizeImg(frame))

    k = cv2.waitKeyEx(10)
    if k%256 == ESCAPE_KEY:       # ESC pressed
        announce(_("Programm wird beendet."))
        exportResults()
        break

    elif k%256 == ord('l'):    # l pressed
        removeResults()

    elif k%256 == ord('k'):    # k pressed
        fromCam = not fromCam
        if fromCam==True:
            announce(_("Kamera eingeschaltet - verwende Kamerabild"))
        else:
            announce(_("Kamera ausgeschaltet - verwende bestehende Ergebnisdateien"))
        updateImage=True

    elif k%256 == ord('h'):    # h pressed
        printHelp()
        
    elif k%256 == ord('-'):    # - pressed
        voiceSpeed -= 10
        announce(_("Sprechgeschwindigkeit {} Prozent").format(voiceSpeed))

    elif k%256 == ord('+'):    # + pressed
        voiceSpeed += 10
        announce(_("Sprechgeschwindigkeit {} Prozent").format(voiceSpeed))
            
    elif k == PAGEUP_KEY:        # previous page
        updateImage=True
        if (img_counter>1):
            img_counter-=1
            announce(_("Seite {}").format(img_counter))
        else:
            announce(_("Bereits auf Seite eins"))

    elif k == PAGEDOWN_KEY:          # next page
        updateImage=True
        img_counter+=1
        announce(_("Seite {}").format(img_counter))

    elif k == UP_ARROW_KEY or k == DOWN_ARROW_KEY or k == RIGHT_ARROW_KEY or k == LEFT_ARROW_KEY:     # up or down arrow pressed
        announce(_("Zum Wechseln in den Lesemodus Entertaste drücken"))

    elif k%256 == ENTER_KEY:    # ENTER pressed
        readResult()            

    elif k%256 == ord(' '):     # SPACE pressed
        updateImage=True
        if fromCam==True:
            announce(_("verarbeite Seite {} von Kamera").format(img_counter))
        else:
            announce(_("verarbeite Seite {} aus bestehender Datei").format(img_counter))
        slice_and_process_image(frame)
        announce(_("Verarbeitung abgeschlossen"))

    elif k==-1:  # normally -1 returned,so don't print it
        continue
    else:
        print (_("Tastencode {} nicht verwendet").format(k)) # else print key value
        
if (cam != None):
    cam.release()
cv2.destroyAllWindows()
