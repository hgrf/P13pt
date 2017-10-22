# Mercury Acquisition SCRIpt Launcher

This is a very lean launcher for acquisition scripts (i.e. scripts that control measurement apparatus and retrieve data).
The user can define an acquisition script with parameters (see MeasurementBase class in measurement.py) that can then
be adjusted for each execution. The launcher features live viewing/plotting of measured data and the user can define alarm
values that will lead to cancelling the measurement.
