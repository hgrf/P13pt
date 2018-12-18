P13pt
=====

- find easy way of creating app icon on Mac
- pywin32 dependency is not automatically installed on Windows systems !!
- fix DLL load issue, c.f. installation on David's PC and on Janis
- make new version for PyPI or "discontinue" PyPI releases (i.e. remove everything from PyPI)
- P13pt version should be in a well defined place (e.g. version.py, c.f. numpy)
- write instructions to create development environment
- write instructions for developer to create new release

MAScriL
=======

- enable saving and loading of parameters
- add note on rohdeschwarz python module in README.md
- make measurement scripts lighter by creating default parameters like data_dir and comment and automating the saving a bit more (e.g. the parameter list should automatically be saved); keep in mind that there are sometimes additional params to add like chuck voltage... 
- move instrument initialisation to separate part and standardise more

SpectrumFitter
==============

- on Erwann's MacOS with Python 3, plots are displayed huge -> check qtpy and matplotlib version

- fix Erwann's bug (i.e. when saving sessions with files that contain formats like _Vg_0.1_ instead of _Vg=0.1_)
- warn the user when a value in the results file exceeds the range of the model sliders
- don't crash when de-embedding fails due to different number of frequency points
- display detailed error message when model fails
- generalise objective function to be in BaseModel class
- adapt all model files (also maybe edited versions on other PCs) to new "format"
- save all images still saves even when user clicks cancel -> fix this and check if same problem occurs for single
  image and for session saving...
- when new spectra are detected too early (during file saving), they are not entirely read -> fix this
- plot title disappears when changing the deembedding -> fix this
- do not crash when file saving fails (e.g. when trying to write to read-only file)
- improve initial data display (ax limits)
- spectrum fitter bug: when data is on C: and results file is on D: (make sure this does not happen, i.e. tell user to
  save on same drive)
- check if for the fitting, the data array is correctly copied and not only referenced (in which case calculation time
  would be significantly higher)
- detect when session was modified (*)
- enable the user to change contact resistance without reloading everything (i.e. like changing de-embedding)
- ask user for a file format when saving all spectra images
- indicate in navigator which files are in cache
- indicate in navigator which files have been fitted
- add mag/phase view for all parameters
- add button to unload the model / remove the model curves
- do not crash when trying to save results file without model loaded
- add functions for fitting thru delay and dummy capacitance and for manual thru and dummy deembedding

distribution for windows:
- make sure "updating" works
- figure out icons and models folder for exe file creation
- there is an error message when we execute and close in Win10

high priority:
- file and folder fields should be reset to previous value when browse is cancelled, not to nothing
- enable displaying model on a broader frequency range
- let the user also decide a frequency range in which he wants to fit

medium priority:
- when saving the results, make sure there is no KeyError for filename parameters
- loading the fitting parameters: verify that model params / dataset are compatible
- allow non-integer values for fitting params
- need to be able to modify range of sliders

low priority:
- make a program that can plot spectra from fitresults (by clicking on datapoints)
- add fit result "grade"
- put a function to export deembedded admittance spectra
- we should impose the order of the fitting parameters
- the default fit method could be created automatically / be in a base class
- give priority for full vertical display for fitter
