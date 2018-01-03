#! /usr/bin/env python

__author__ = "Brady Johnson"
__copyright__ = "Copyright(c) 2015, Inocybe, Inc."
__license__ = "Eclipse Public License v1.0"
__version__ = "0.1"
__email__ = "bjohnson@inocybe.com"
__status__ = "demo code"

import os
import re
import time
import datetime
import json
import argparse
import tempfile


default_timing_analysis_data = {
    "timing-analysis" : {
        "events" : [
            { "name"       : "Java Build",
              "start-tag"  : "Building ODL :: sfc :: sfc",
              "end-tag"    : "T E S T S"
            },
            { "name"       : "Feature Build",
              "start-tag"  : "Building ODL :: sfc :: odl",
              "end-tag"    : "T E S T S"
            },
            { "name"       : "Karaf Build",
              "start-tag"  : "Building ODL :: sfc :: sfc-karaf",
              "end-tag"    : "Reactor Summary"
            },
            { "name"       : "Unit-Test",
              "start-tag"  : "Surefire report directory: /w/workspace/sfc-maven-verify-oxygen-mvn33-openjdk8/sfc",
              "end-tag"    : "Results :"
            },
            { "name"       : "SingleFeatureTest",
              "start-tag"  : "Surefire report directory: /w/workspace/sfc-maven-verify-oxygen-mvn33-openjdk8/feature",
              "end-tag"    : "in org.opendaylight.odlparent.featuretest.SingleFeatureTest"
            }
        ]
    }
}

# { "name"       : "Findbugs - included in Java Build",
#   "start-tag"  : ">>> findbugs-maven-plugin",
#   "end-tag"    : "Done FindBugs Analysis"
# },

KEY_TIMING = 'timing-analysis'
KEY_EVENTS = 'events'
KEY_NAME = 'name'
KEY_START_TAG = 'start-tag'
KEY_END_TAG = 'end-tag'
KEY_TIME_START = 'time-start'
KEY_TIME_END = 'time-end'
KEY_TIME_DIFF = 'time-diff'

class Context(object):
    def __init__(self):
        self.timing_analysis_filename =  ''
        self.csit_log_filename        =  ''
        self.csit_sub_log_filename    =  ''
        self.timing_info              =  {}


def get_cmd_line(context):
    opts = argparse.ArgumentParser()

    opts.add_argument('--info', '-i',
                      dest='input_info',
                      help='Timing analysis input json file')

    opts.add_argument('--logfile', '-l',
                      dest='log_file',
                      default='console-timestamp.log',
                      help='CSIT log file')

    args = opts.parse_args()

    context.timing_analysis_filename = args.input_info
    context.csit_log_filename = args.log_file

    # Put cmd-line parsing logic here, and return False if something's not right

    return True


def get_timing_analysis_data(json_file=None):
    if not json_file:
        return default_timing_analysis_data

    if not os.path.exists(json_file):
        print 'ERROR: Timing analysis json file [%s] does not exist' % json_file
        return {}

    return json.load(open(json_file, 'r'))


def get_timing_start_end_list(data):
    timing_start_end_list = []
    events_list = data[KEY_TIMING][KEY_EVENTS]
    for event in events_list:
        timing_start_end_list.append(re.escape(event[KEY_START_TAG]))
        timing_start_end_list.append(re.escape(event[KEY_END_TAG]))

    return timing_start_end_list


def create_log_sub_file(csit_log_filename, timing_info):
    if not os.path.exists(csit_log_filename):
        print 'ERROR: CSIT log file [%s] does not exist' % csit_log_filename
        return False

    regex_tag_list = get_timing_start_end_list(timing_info)
    regex_pattern = r'|'.join(regex_tag_list)
    regex = re.compile(regex_pattern)

    csit_sub_log_file = tempfile.NamedTemporaryFile(delete=False)
    #print "Created temp file: %s" % csit_sub_log_file.name

    with open(csit_log_filename) as f:
        for line in f:
            match = regex.search(line)
            if match:
                csit_sub_log_file.write(line)

    csit_sub_log_file.close()

    return csit_sub_log_file.name


def diff_times(start_time, end_time):
    start = time.strptime(start_time, '%H:%M:%S')
    td_start = datetime.timedelta(hours=start.tm_hour, minutes=start.tm_min, seconds=start.tm_sec)

    end = time.strptime(end_time, '%H:%M:%S')
    td_end = datetime.timedelta(hours=end.tm_hour, minutes=end.tm_min, seconds=end.tm_sec)

    return td_end - td_start

def get_event_timing_data(event, sub_log_filename):
    # Return a list of dicts: [{"start-tag" : "", "time-start" : timeStart, "time-diff" : timeDiff}, ...]
    # The idea is the start-tag will start the same for all, but have specific info like for which test or build

    regex_start = re.compile(re.escape(event[KEY_START_TAG]))
    regex_end   = re.compile(re.escape(event[KEY_END_TAG]))

    results = []
    start_time = ''
    start_tag = ''
    started = False
    with open(sub_log_filename) as f:
        for line in f:
            if not started:
                match_start = regex_start.search(line)
                if match_start:
                    started = True
                    line_data = line.split(' ', 1)
                    start_time = line_data[0]
                    start_tag  = line_data[1]
            else:
                match_end = regex_end.search(line)
                if match_end:
                    started = False
                    end_time = line.split(' ', 1)[0]
                    results.append({KEY_START_TAG  : start_tag,
                                    KEY_TIME_START : start_time,
                                    KEY_TIME_END   : end_time,
                                    KEY_TIME_DIFF  : diff_times(start_time, end_time)})

    if started:
        print "Couldnt find end time for [%s] start tag: %s %s" % (event[KEY_NAME], start_time, start_tag)

    return results


def process_timing_data(timing_info, csit_sub_log_filename):
    results = []
    events_list = timing_info[KEY_TIMING][KEY_EVENTS]
    for event in events_list:
        event_timing_data = get_event_timing_data(event, csit_sub_log_filename)
        results.append( {event[KEY_NAME] : event_timing_data} )

    os.remove(csit_sub_log_filename)

    return results


def display_results(results):
    total_time = datetime.timedelta()
    timing_data_string_list = []

    for entry in results:
        for key, value in entry.iteritems():
            event_timing_data_string_list = []
            total_event_time = datetime.timedelta()
            for timing_data in value:
                total_event_time = total_event_time + timing_data[KEY_TIME_DIFF]
                event_timing_data_string_list.append("\t %s" % timing_data[KEY_START_TAG].rstrip().lstrip())
                event_timing_data_string_list.append("\t\t start-time [%s] end-time [%s] total-time [%s]" %
                          (timing_data[KEY_TIME_START], timing_data[KEY_TIME_END], timing_data[KEY_TIME_DIFF]))

            timing_data_string_list.append("\nTiming data for [%s] total-time [%s]" % (key, total_event_time))
            timing_data_string_list.extend(event_timing_data_string_list)
            total_time = total_time + total_event_time

    print 'Total accumulated time [%s]' % total_time
    print '\n'.join(timing_data_string_list)

def main():
    context = Context()
    if not get_cmd_line(context):
        return

    context.timing_info = get_timing_analysis_data(context.timing_analysis_filename)
    #print json.dumps(context.timing_info, indent=4, separators=(',', ': '))

    context.csit_sub_log_filename = create_log_sub_file(context.csit_log_filename, context.timing_info)

    results = process_timing_data(context.timing_info, context.csit_sub_log_filename)

    display_results(results)

if __name__ == '__main__':
    main()
