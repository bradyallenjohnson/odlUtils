# odlUtils
General ODL Utilities

csit_verify_timing_analyzer:

Usage:
$ ./timing_analyzer.py --help
usage: timing_analyzer.py [-h] [--info INPUT_INFO] [--logfile LOG_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --info INPUT_INFO, -i INPUT_INFO
                        Timing analysis input json file
  --logfile LOG_FILE, -l LOG_FILE
                        CSIT log file

An example logfile can be found in the verify directory. An example info file called timing_info.json has also been included. If no info file is included, default info will be used.

The idea is to create testing events in the info JSON file by specifying a "start-tag" and "end-tag" as can be found in the logfile. The information for all of these events will be accumulated, and the time for each will be displayed together with the accumulated time.
