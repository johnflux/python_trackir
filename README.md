This is a windows-only program and library to read the 6 DOF (six degrees of freedom: x,y,z,roll,pitch,yaw) data from a TrackIR camera.

To use, buy a TrackIR device, and run the TrackIR software, and make sure that it's working there.  If you want raw data, make sure you set the profile to "one:one" and set the smoothing to 0.

Then run the log_to_csv.py  program, and see the data printed out at approximately 100hz.

To run, you can use run it within visual studio code, or from a git bash command line like:

    winpty python3.exe ./log_to_csv.py

(It might ask you to install python3 first)

Or log to a file like:

    winpty python3.exe ./log_to_csv.py > log.csv

