#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Optical Braille Recognition - user interface and control script
#
# Place braille sheets (or book) on a dark background.
# Set up light and camera as described here: https://angelina-reader.ru/help/#how_to_photo
# This script captures single frames from the webcam or uses existing images (in args.results_dir), 
# then seperates bright area from background, 
# then decides if orientation is portrait (1 page) or landscape (2 pages, book),
# in case of landscape orientation extracts 2 single pages,
# then performs optical braille recognition using Angelina Reader
# and optionally speaks out results using pyttsx3 
#
# thanks to:
#   https://www.codegrepper.com/code-examples/python/python+capture+image+from+webcam
#   https://stackoverflow.com/questions/13887863/extract-bounding-box-and-save-it-as-an-image
#   https://github.com/IlyaOvodov/AngelinaReader
#


import pyttsx3
import cv2
import os
import glob
import argparse
from pathlib import Path
from pygame import mixer

import local_config
import model.infer_retinanet as infer_retinanet

model_weights = 'model.t7'
MIN_AREA=100000
tmpwavfile = "temp.wav"
lastKey=-1
img_counter = 1
speakText=True
fromCam=True
fn=0


parser = argparse.ArgumentParser(description='Angelina Braille Reader: optical Braille text recognizer - interactive version using camera input.')

#parser.add_argument('input', type=str, help='File(s) to be processed: image, pdf or zip file or directory name')
parser.add_argument('results_dir', type=str, help='Output directory for results.')
parser.add_argument('-l', '--lang', type=str, default='DE', help='(Optional) Document language (RU, EN, DE, GR, LV, PL, UZ or UZL). If not specified, is RU')
parser.add_argument('-o', '--orient', action='store_false', help="Don't find orientation, use original file orientation")
#parser.add_argument('-2', dest='two', action='store_true', help="Process 2 sides")

args = parser.parse_args()

args.results_dir=os.path.join(args.results_dir, '')  # add trailing slash if necessary
if not Path(args.results_dir).exists():
    print('output directory does not exist: ' + args.results_dir)
    exit()


# Initialize the speech synthesizer and pygame mixer
speechSynthesizer = pyttsx3.init()
voices = speechSynthesizer.getProperty("voices")[0] 
speechSynthesizer.setProperty('voice', voices)
speechSynthesizer.setProperty('rate', 200)
speechSynthesizer.setProperty('volume', 0.7)
mixer.init()


def announce (text):
    global fn
    global lastKey
    global speakText

    print(text, flush=True)
        
    # speechSynthesizer.say(text)
    # using workaround with pygame mixer because ttsx3 can't be interrupted!
    fn = (fn+1) % 2  # another workaround because ttsx3 does not close the last file!
    fil="{}{}".format(tmpwavfile,fn)
    speechSynthesizer.save_to_file(text, fil)
    speechSynthesizer.runAndWait()
    speechSynthesizer.stop()
    mixer.music.load(fil)
    mixer.music.play()
    
    pause=False
    lastKey=-1
    while (mixer.music.get_busy() and lastKey==-1) or (pause == True):
        lastKey = cv2.waitKeyEx(10)
        if lastKey == ord('s'):   # s: interrupt and disable speech output
            speakText=False
            announce("Sprachausgabe von Ergebnissen ausgeschaltet")
            break
        if lastKey == ord('p'):   # p: pause/resume ongoing speech output
            if pause==False:
                mixer.music.pause()                
            else:
                mixer.music.unpause()
                lastKey=-1
            pause = not pause

def readResult():
    global img_counter
    global speakText

    marked_name = "{}page_{}.marked.txt".format(args.results_dir,img_counter)
    marked_jpg = "{}page_{}.marked.jpg".format(args.results_dir,img_counter)    

    cv2.namedWindow("OBR-Result")
    cv2.moveWindow("OBR-Result", 500,40)
    img = cv2.imread(marked_jpg)
    cv2.imshow("OBR-Result", img)
    
    file1 = open(marked_name, 'r', encoding='utf-8', errors='ignore')
    Lines = file1.readlines()
      
    actLine = 0
    while (actLine < len (Lines)):
        line=Lines[actLine]
        line=line.replace("~?~", " (unbekannt) ")
        line=line.replace("\"", " (Hochkomma) ")
        line=line.replace(":", " (Doppelpunkt) ")
        line=line.replace(";", " (Strichpunkt) ")
        line=line.replace(",", " (Beistrich) ")
        line=line.replace(".", " (Punkt) ")
        line=line.replace("-", " (Minus) ")
        line=line.replace("+", " (Plus) ")
        line=line.replace("*", " (Stern) ")
        
        if speakText==True:
            announce("Zeile{}: {}".format(actLine+1, line.strip()))
            if (lastKey == 2490368 and actLine > 0):   # up arrow
                actLine-=1
            elif (lastKey == 2621440 and actLine < len(Lines)):   # down arrow
                actLine+=1
            elif (lastKey == -1):   # no key -> progress to next line!
                actLine+=1
            elif (lastKey == 27):   # ESC: end readout
                actLine = len(Lines)
        else:
            actLine+=1
            
    cv2.destroyWindow("OBR-Result")
    
def process_image (img,x,y,w,h):
    global img_counter
    global frameCopy
    global speakText
    ROI = img[y:y+h, x:x+w]
    cv2.rectangle(frameCopy,(x,y),(x+w,y+h),(10,10,255),2)
    cv2.imshow("brailleImage", frameCopy)

    img_name = "{}page_{}".format(args.results_dir,img_counter)
    if (os.path.exists(img_name+".marked.brl")==True):
        os.remove(img_name+".marked.brl")
    if (os.path.exists(img_name+".marked.txt")==True):
        os.remove(img_name+".marked.txt")
    if (os.path.exists(img_name+".marked.jpg")==True):
        os.remove(img_name+".marked.jpg")
        
    img_name=img_name+".png"
    
    if fromCam==True:
        announce("verarbeite Seite {} von Kamera".format(img_counter))
    else:
        announce("verarbeite Seite {} aus bestehender Datei".format(img_counter))
    cv2.imwrite(img_name, ROI)
    # os.system("run_local.py -o -l DE {}".format(img_name))
    recognizer.run_and_save(img_name, args.results_dir, target_stem=None,
                                           lang=args.lang, extra_info=None,
                                           draw_refined=recognizer.DRAW_NONE,
                                           remove_labeled_from_filename=False,
                                           find_orientation=args.orient,
                                           align_results=True,
                                           process_2_sides=False,
                                           repeat_on_aligned=False,
                                           save_development_info=False)    
    readResult()
    announce("Verarbeitung Seite {} - abgeschlossen".format(img_counter));
    img_counter += 1


# welcome message, create live window
announce("Programm startet ...")

# Initialize the Braille recognizer
recognizer = infer_retinanet.BrailleInference(
    params_fn=os.path.join(local_config.data_path, 'weights', 'param.txt'),
    model_weights_fn=os.path.join(local_config.data_path, 'weights', model_weights),
    create_script=None)

# Initialize the webcam and opencv
cam = cv2.VideoCapture(0)
cv2.namedWindow("brailleImage")
cv2.moveWindow("brailleImage", 10,50)
announce ("Bereit. Taste h für Hilfe drücken.");

# main loop
while True:
    actfile="{}page_{}.png".format(args.results_dir,img_counter)
    if (fromCam==True):        
        ret, frame = cam.read()
        if not ret:
            announce("Kamera konnte kein Bild aufnehmen.")
            break
    elif (os.path.exists(actfile)==True):
        frame = cv2.imread(actfile)
    else:
        announce("Datei nicht vorhanden. Kamera eingeschaltet - verwende Kamerabild")
        fromCam=True
        continue

    cv2.imshow("brailleImage", frame)

    k = cv2.waitKeyEx(1)
    if k%256 == 27:       # ESC pressed
        announce("Escape gedrueckt, Programm wird beendet")
        break

    elif k%256 == ord('l'):    # l pressed
        announce("Lösche alle bestehenden Ergebnisdateien.")
        img_counter=1
        files = glob.glob('{}*'.format(args.results_dir))
        for f in files:
            os.remove(f)        

    elif k%256 == ord('k'):    # k pressed
        fromCam = not fromCam
        if fromCam==True:
            announce("Kamera eingeschaltet - verwende Kamerabild")
        else:
            announce("Kamera ausgeschaltet - verwende bestehende Ergebnisdateien")

    elif k%256 == ord('s'):    # s pressed
        speakText = not speakText
        if speakText==True:
            announce("Sprachausgabe von Ergebnissen eingeschaltet")
        else:
            announce("Sprachausgabe von Ergebnissen ausgeschaltet")

    elif k%256 == ord('h'):    # h pressed
        announce("Taste h: Ausgabe Hilfetext")
        announce("Taste k: zwischen Kamera und Ergebnisdateien wechseln")
        announce("Leertaste: Bildverarbeitung starten")
        announce("Taste l: löschen der bestehenden Ergebnisdateien")
        announce("Taste s: Sprachausgabe von Ergebnissen ein- oder ausschalten")
        announce("Taste p: Sprachausgabe pausieren")
        announce("Pfeiltaste rauf: vorige Ergebniszeile lesen")
        announce("Pfeiltaste runter: nächste Ergebniszeile lesen")
        announce("Plustaste: nächste Seite aktivieren")
        announce("Minustaste: vorige Seite aktivieren")
        announce("Escapetaste: Programm beenden")

    elif k%256 == ord('-'):    # - pressed
        if (img_counter>1):
            img_counter-=1
        announce("Seite {}".format(img_counter))

    elif k%256 == ord('+'):    # + pressed
        img_counter+=1
        announce("Seite {}".format(img_counter))
            
    elif k%256 == ord(' '):     # SPACE pressed
        frameCopy = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray,0,255,cv2.THRESH_OTSU + cv2.THRESH_BINARY)[1]
        #cv2.imshow('thresh', thresh)

        # find contours of biggerst bounding rectangle
        cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        maxArea=0
        actIndex=0
        for c in cnts:
            x,y,w,h = cv2.boundingRect(c)
            #print("w: {}, h: {}, area: {}, ratio: {}".format(w,h,w*h,w/h), flush=True)
            #cv2.rectangle(frameCopy,(x,y),(x+w,y+h),(100,100,100),2)
            #cv2.imshow("brailleImage", frameCopy)
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
                announce("Doppelseite erkannt")
                half_w=round(w/2)
                process_image(frame,x,y,half_w,h)
                process_image(frame,x+half_w,y,half_w,h)
        else:
            announce("keine Seite erkannt");
    
    elif k==-1:  # normally -1 returned,so don't print it
        continue
    else:
        print ("Tastencode {} nicht verwendet".format(k)) # else print its value
        
cam.release()
cv2.destroyAllWindows()
