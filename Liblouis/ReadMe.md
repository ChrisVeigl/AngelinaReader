
## Liblouis installation for Windows

## The files in this folder belong to the Liblouis project

https://liblouis.io/
https://github.com/liblouis/liblouis

See the license information: https://github.com/liblouis/liblouis/blob/master/License.md

As the instructions provided in the Liblouis documentation https://github.com/liblouis/liblouis/blob/master/README.windows
seem to depend on a specific version of the MSVC compiler and also showed other problems with the setup process using a recent python3 environment, 
the .dll for Win64, the python site package folder and the translation tables for LibLouis V3.27.0 are provided here
(for Linux, follow the installation procedure as described here: https://github.com/liblouis/liblouis#installation ).

* unzip louis_3.27.0.zip into this folder (so that you get the subfolders ./louis and ./tables)
* copy ./louis/liblouis.dll to a Windows system path (e.g. C:\Windows\System32)
* copy ./louis (the whole folder) to your python environment's user site packages location (see output of 'python -m site --user-site')
