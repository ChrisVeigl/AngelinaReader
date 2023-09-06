# Angelina Braille Reader

Angelina Braille Reader is an Optical Braille Recognition system. It is designed to convert Braille text on photos into plain text.
This (forked) version provides the `run_local_camInteractive.py` script for live processing of camera/webcame images and a speech-guided menu for processing and appending text results of the braille recognition process (see Usage and Instructions for pyhsical setup).

## General description of the solution

The solution is a web-service.

Users interact with it via a standard web browser on a smartphone or a desktop computer. Results are displayed on the screen as images and text and can be sent to the user's E-mail.

This solution can also be installed as a standalone program on a personal computer and can be used through a command-line interface.

Video presentation: https://youtu.be/_vcvxPtAzOM   

This service is available at the address: http://angelina-reader.ru   


### Solution key features

* Can handle images of deformed braille pages
* Can recognize either one- or two-side Braille printouts
* Can recognize both recto and verso sides of a page using a single image
* Can automatically find the correct orientation of an image
* Can process:
  * images taken on a smartphone camera directly from the application (only mobile web version)
  * image files (jpg etc.)
  * pdf files
  * zip-archives with images
* Results can be sent to the user's e-mail
* Can recognize Russian, English, German, Uzbek, Latvian and Greek braille texts

### Limitations

* Page image must be taken approximately from a top view
* Light must fall from the upper side of the page. I.e. shadow of a subject placed on a page must be directed at the bottom side of the page. Top light, side light, and light from the bottom side of the page are not allowed.
* Braille symbols must not be too small or too large. Optimally A4 page with standard braille text must  occupy the whole image area.

### Approaches used in the project

* Braille symbols are detected using object detection CNN (RetinaNet https://arxiv.org/abs/1708.02002)
* Primary network training was done using the DSBI dataset
* Additional training data were prepared using several rounds of manual correction of results produced by CNN trained on a previous round dataset 
* At first rounds poetry texts were used, errors were found using line-by-line comparison with the original text
* At later stages, recognition errors were found using spell-checker
* A new annotated dataset of 360 pages of single-side handwritten and two-side printed Braille texts is prepared, including annotation of 76 paged from the dataset, provided by World AI&DATA Challenge contest. This dataset will be published later.
* For an automatic search of correct page orientation, the page is processed in all 4 possible orientations and the orientation with the maximum presence of the most wide-spread Braille chars is selected 
* For recognizing or verso side text we use the effect, that dented points became visually convex on the inverted image. We invert an image and flip it horizontally to recognize the verso side.
* We use a heuristic algorithm to form strings from detected symbols.
* We translate Braille symbols into plain Russian or English text using an algorithm where Braille interpretation rules are coded.

## Environment requirements

Standalone workstation requires NVIDIA GPU with at least 3GB memory (i.e. GeForce GTX 1050 3GB or better), web-server requires at least 4GB GPU memory (GeForce GTX 1050Ti or better)

OS: Ubuntu, Windows   
 CUDA 10.2   
 Python 3.8   
 python packages see requirements.txt   
 
 Python path should be added to PATH.

A client requires a standard web-browser (Chrome, Firefox) 

### Python CUDA support NVIDIA Jetson Nano

On an Ubuntu 18.x on a NVIDIA Jetson:
* use pytorch-1.10 and torchvision-0.11 from https://qengineering.eu/install-pytorch-on-jetson-nano.html
* use numpy and other wheels from https://github.com/jetson-nano-wheels/jetson-nano-wheels
* for pygame installation use https://forums.developer.nvidia.com/t/install-pygame-on-jetson-nano/83731/8
* pip3 install -r requirements-jetson-nano.txt
* pip3 install opencv-python

## Installation

On NVDIA Jetson Nano use the python 3.6 wheels linked above to get CUDA support.

```
sudo apt-get install libttspico-utils sox 
git clone --recursive https://github.com/IlyaOvodov/AngelinaReader.git
cd AngelinaReader
pip install --upgrade pip
pip install -r requirements.txt
pip uninstall opencv-python-headless
pip install opencv-python
wget -O weights/model.t7 http://angelina-reader.ovdv.ru/retina_chars_eced60.clr.008    
python run_local_camInteractive.py
```
Windows: pip directory (i.e. `<python>\Scripts`) should be added to Path .   
Be sure  `python` and `pip` start Python3 if both Python 3 and Python 2.7 are installed.   

Open http://127.0.0.1:5000 in a browser. The main page of the application should be displayed.

To access the application from Internet forward port 80 to port 5000 of the server. It is not required to test the service locally (at http://127.0.0.1:5000 address).  


## Usage

### Using as a web service

start server: `python run_web_app.py`
For Windows: you can use bat-file `start_web_app.bat`

Open page http://127.0.0.1:5000 in a browser. Follow instructions.

If some Braille symbols can not be interpreted by the application, they are displayed as `~?~`.

Usage of web-application is demonstrated in a brief video: https://youtu.be/_vcvxPtAzOM and in a video presentation  https://youtu.be/_vcvxPtAzOM


### Command-line interface 

`python run_local.py [-h] [-l LANG] [-o] [-2] input [results_dir]`   
or, in Windows:   
`start.bat [-h] [-l LANG] [-o] [-2] input [results_dir]`   
Parameters:   
`input` - image file (jpg, png etc.), pdf file, zip file with images or directory name.   
If directory name or zip file is supplied, all image and pdf files in it will be processed.   
`results_dir` - folder to place results in. If not supplied, the input files folder will be used. For every input file will be created files `<input file>.marked.txt` with results in a plain text form and `<input file>.marked.jpg` with plain text printed over input image.   
`-l <language>` - input document language (default is RU). Use `-l EN` for English texts, `-l GR` for Greek etc. See languages list below. 
`-o` - switch off automatic orientation search. Sometimes auto orientation can work incorrectly (for non-typical texts or if there are many recognition errors). In such cases adjust image orientation manually and use `-o` option.   
`-2` - recognize both recto and verso sides of two-side printouts. Verso side results are stored in `<input file>.rev.marked.txt` и `<input file>.rev.marked.jpg` files.   
`-h` - print help.   

Languages:
`RU` - Russian
`EN` - English (grade 1)
`DE` - German
`GR` - Greek
`LV` - Latvian
`PL` - Polish
`UZ` - Uzbek (cyrillic)
`UZL` - Uzbek (latin)

### Command-line interface for speech based interaction with live cam interface

`python run_local_camInteractive.py [-h] [-l LANG] [-o] [input]`   

Note that the `input` parameter is optional in this version. If not image source is provided, the live camera can be used to acquire image data.  
Note that the ./results folder holds current image and text data. It must exit when starting the script.


Parameters:   
`input` - image file (jpg, png etc.), pdf file, zip file with images or directory name.   
`-o` - switch off automatic orientation search. Sometimes auto orientation can work incorrectly (for non-typical texts or if there are many recognition errors). In such cases adjust image orientation manually and use `-o` option.   
`-l <language>` - input document language (default is RU). Use `-l EN` for English texts, `-l GR` for Greek etc. See languages list below. 
`-h` - print help.   


Languages: see above

Hotkeys:
`h`: print and speak help text (including hotkey information, in german)
`k`: enable live camera / change between stored images and live cam
`<SPACE>`: start image processing for current page
`l`: delete all stored image and text files
`v`: read mode (reads/speaks out current page)
`<PageUp>`: select next page
`<PageDown>`: select previous page
`<CursorUp>`: read/speak out previous line of current page
`<CursorDown>`: read/speak out next line of current page
`<CursorRight>`: read/speak out next character of current line
`<CursorLeft>`: read/speak out previous character of current line
`<Delete>`: replace current character (input new one)
`z`: turn on/off line number readout
`p`: pause/resume ongoing speech output
`+`: increase speed of speech output
`-`: decrease speed of speech output
`Escape`: Exit read mode / exit program (results.txt is created when program is exited).


## Datasets being used

Network weights: see repository `./weights` folder.

## Instructions and recommendations for physical setup

In order to achieve good and repeatable results, we experimented with different webcams and light sources.
We achived good results with a Logitech HD pro C920 1080p Webcam, mounted 50 cm above the center of the braille page center.
Two light sources are placed in a distance of 50 cm to the braille page center and with 50 cm distance to each other.
(The light shines from top, so that the shadow is oriented towards the page bottom, see instructions on the Angelina Reader webpage).
A dark table surface is important for the image segmentation which is applied before the processing in order to create two independent processing runs for a double sided image (e.g. a book with two pages).
