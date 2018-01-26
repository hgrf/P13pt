# P13 python tools is the new RFLPA

## setting up the dependencies

it is recommended to do this in a virtual environment

    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    
we also require PyQt5, this requirement is probably already fulfilled (and not always by the same package, so I did not put it in the requirements.txt)

TODO: instructions for installation with Anaconda

## building the doc

cd into the docs directory and execute

    make html
    
then the doc can be accessed: /docs/\_build/html/index.html

## file name strucure

file names for DC or RF data should contain parameters separated by underscores, i.e. in the format "...\_name=value\_..."

ideally the filename should start with a timestamp in the format "YYYY-MM-DD\_HHhMMmSSs\_..."

for example, a measurement taken on the 1st of February 2003 at 12:34:56 pm with Vg=-0.1V would look like this:

2003-02-01_12h34m56s_Vg1=0.1.txt

for readability and easy interpretation by the analysis scripts, the parameter values should not be stated with units, we assume SI units (i.e. for Vg1=1mV write "...\_Vg1=1e-3\_...")

it is possible to add parameters without value, they will be added to the parameter dictionary, but not assigned any value (useful for "flagging" files)


## file structure

values should be separated by tabs, the decimal point should be "."

comments should be at the beginning of the file and preceeded by a hashtag "#"
