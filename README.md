# P13 python tools is the new RFLPA

## file name strucure

file names for DC or RF data should contain parameters separated by underscores, i.e. in the format "..._name_value_..."

ideally the filename should start with a timestamp in the format "YYYY-MM-DD_HHhMMmSSs_..."

for example, a measurement taken on the 1st of February 2003 at 12:34:56 pm with Vg=-0.1V would look like this:

2003-02-01_12h34m56s_Vg1_0.1.txt

for readability and easy interpretation by the analysis scripts, the parameter values should not be stated with units, we assume SI units (i.e. for Vg1=1mV write "..._Vg1_1e-3")


## file structure

values should be separated by tabs, the decimal point should be "."

there should be only one sweeped parameter (e.g. gate voltage or source drain voltage) per file, if possible

comments should be at the beginning of the file and preceeded by a hashtag "#"
