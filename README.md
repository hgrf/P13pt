# P13 python tools

[![Build Status](https://travis-ci.org/HolgerGraef/P13pt.svg?branch=master)](https://travis-ci.org/HolgerGraef/P13pt)
[![Anaconda](https://anaconda.org/green-mercury/p13pt/badges/version.svg)](https://anaconda.org/green-mercury/p13pt)

P13pt is a set of python tools (some helper scripts, rudimentary instrument drivers,
automation software, a plotting tool and a fitting tool for vector network analyzer - VNA -
spectra) that I have developed during my PhD thesis in the P13 lab at École Normale
Supérieure in Paris, France.

It has no ambition to become a full-fledged tool suite, but should rather be seen as
a set of example scripts. If you are interested in data acquisition software for python,
check out [Exopy](https://github.com/Exopy/exopy). The VNA spectra analysis is done using 
[scikit-rf](http://scikit-rf-web.readthedocs.io/), combined with a "home-made" de-embedding
algorithm.


## Components

* Instrument drivers for Anritsu VNA MS4644B, iTest Bilt voltage sources and meters, Keithley
2400 and 2600 SMUs, the Yokogawa 7651 source and the SI9700 temperature controller (zilockin.py
is not a driver, just a "frontend" for the Zurich Instruments lock-in driver)
* [SpectrumFitter](https://github.com/green-mercury/P13pt/tree/master/P13pt/spectrumfitter), a
fitting tool for 2-port network VNA spectra.
* [Graphulator](https://github.com/green-mercury/P13pt/tree/master/P13pt/graphulator), a calculator
for graphene charge carrier density, Fermi level etc.
* [MAScriL](https://github.com/green-mercury/P13pt/tree/master/P13pt/mascril), the "Mercury
Acquisition Script Launcher", which is the result of an attempt to "standardize" my
acquisition scripts and facilitate live plotting.
* [MDB](https://github.com/green-mercury/P13pt/tree/master/P13pt/mdb), the "Mercury Data Browser",
a tool to quickly plot data from text files, not maintainted anymore.
* fundconst.py: some fundamental physical constants for convenience
* n_from_vg.py: to quickly calculate the graphene charge carrier density from gate voltage
* params_from_filename.py: a tool to extract parameters from the filename, see below
* rfspectrum.py: a wrapper for [scikit-rf](http://scikit-rf-web.readthedocs.io/)'s Network
class
* savitzky_golay.py: a smoothing filter (not my work, see in the file)


## Installation

Use conda to set up a new environment (if you don't have Anaconda, get it from
[here](https://www.anaconda.com/download/)). It should be a Python 2.7, 3.6 or 3.7 environment.

    conda create -n P13pt

Make sure the conda-forge channel is installed:

    conda config --append channels conda-forge
    
If you want the P13pt application to show up in Anaconda-Navigator, add the green-mercury channel:

    conda config --append channels green-mercury
    
Activate the environment and install P13pt:

    conda activate P13pt
    conda install -c green-mercury p13pt

If you want to automatically create links for the applications in P13pt, you can use the following command:

    p13pt-makelinks
    
On a Windows system, this will create shortcuts on the Desktop, on a Linux system, it will create links in
~/.local/share/applications.

If you wish to use the "driver" for the Zurich Instruments lock-in amplifier, you should
install version 16.04 of ziPython.

## Creating a development environment

Use these instructions to create a conda environment for development, i.e. where the P13pt package is imported from its GitHub source, so that you can make changes and test them immediately. Start by cloning the P13pt environment you have created in the previous section or by creating an equivalent one, that we will call P13pt_dev in the following. The first step is to remove the P13pt conda package from this environment (installing it in the first place only serves to install all the dependencies automatically):

    conda activate P13pt_dev
    conda uninstall p13pt

Now we want to clone the P13pt GitHub repository, e.g. in the home folder:

    cd ~
    git clone git@github.com:HolgerGraef/P13pt.git
    
Finally, we want to set up the PYTHONPATH to contain P13pt's path. This should be set automatically whenever we activate the P13pt_dev environment. For that, we create the file: \[conda root\]/envs/P13pt_dev/etc/conda/activate.d/env_vars.sh and add the following content:

    #!/bin/bash
    
    export OLDPYTHONPATH=$PYTHONPATH
    export PYTHONPATH=$PYTHONPATH:$HOME/P13pt/
    
    alias spectrumfitter='bash -c ". \[conda root\]/etc/profile.d/conda.sh && conda activate P13pt_dev && python $HOME/P13pt/P13pt/spectrumfitter/spectrumfitter.py"'
    
Obviously, you should replace \[conda root\] by Anaconda's root directory. If you wish to create aliases for the other scripts, e.g. for MAScriL, just add the corresponding lines. Now, if you switch to a different conda environment, you also want the terminal to "forget" the modifications to PYTHONPATH and the aliases, so we also create the file: \[conda root\]/envs/P13pt_dev/etc/conda/deactivate.d/env_vars.sh with the content:

    #!/bin/bash
    
    export PYTHONPATH=$OLDPYTHONPATH
    
    unalias spectrumfitter

## Building the doc

The documentation is work in progress, but in principle you can build it by cd'ing
into the docs directory and executing

    make html
    
Then the doc can be accessed: /docs/\_build/html/index.html


## File name strucure for data files

File names for DC or RF data should contain parameters separated by underscores,
i.e. in the format "...\_name=value\_...". That way they can be extracted as a python
dictionary using **params_from_filename**. Ideally, the filename should start with a
timestamp in the format "YYYY-MM-DD\_HHhMMmSSs\_...".

For example, a measurement taken on the 1st of February 2003 at 12:34:56 pm
with gate voltage Vg=-0.1V would look like this:

2003-02-01_12h34m56s_Vg1=0.1.txt

For readability and easy interpretation by the analysis scripts, the parameter
values should not be stated with units, we assume SI units (i.e. for Vg1=1mV
write "...\_Vg1=1e-3\_...")

It is possible to add parameters without value, they will be added to the
parameter dictionary, but not assigned any value (useful for "flagging" files).


## Data file structure

Values should be separated by tabs ("TSV" format), the decimal point should be ".".

Comments should be at the beginning of the file and preceeded by a hashtag "#".
