#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 17:32:29 2019

@author: eo
"""


# ---------------------------------------------------------------------------------------------------------------------
#%% Imports

import os
import json
import subprocess
import argparse

import datetime as dt

from platform import uname

from local.eolib.utils.cli_tools import cli_prompt_with_defaults
from local.eolib.utils.ranger_tools import ranger_file_select

# ---------------------------------------------------------------------------------------------------------------------
#%% Define functions

# .....................................................................................................................

def parse_args():
    
    # Set up argparser options
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video", default = None, type = str, help = "Source video to clip")
    ap.add_argument("-s", "--start", default = None, type = str, help = "Clipping start timestamp")
    ap.add_argument("-e", "--end", default = None, type = str, help = "Clipping end timestamp")
    ap.add_argument("-n", "--outname", default = None, type = str, help = "Output video file name")
    ap.add_argument("-p", "--outpath", default = None, type = str, help = "Output video file path")
    
    ap.add_argument("-x", "--exact", action = "store_true", help = "Clip video exactly at timestamps. \
                                                                    Requires re-encoding! (slow)")
    
    # Convert argument inputs into a dictionary
    ap_result = vars(ap.parse_args())
    
    return ap_result

# .....................................................................................................................

def captured_subprocess(run_command_list):
    ''' Use subprocess with captured stdout and stderr '''
    return subprocess.run(run_command_list, stderr = subprocess.PIPE, stdout = subprocess.PIPE)

# .....................................................................................................................

def check_req_installs():
    
    # Make sure we use the right 'check for program' command
    system_type = uname().system
    system_is_windows = ("windows" in system_type.lower())
    check_cmd = "where" if system_is_windows else "which"
    
    ffmpeg_check = captured_subprocess([check_cmd, "ffmpeg"])
    ffprobe_check = captured_subprocess([check_cmd, "ffprobe"])
    ranger_check = captured_subprocess([check_cmd, "ranger"])
    
    if ffmpeg_check.returncode != 0:
        print("",
              "WARNING: Couldn't find ffmpeg! This script may fail...",
              "On Ubuntu, install with:",
              "",
              "  sudo apt install ffmpeg",
              "",
              sep = "\n")
    
    if ffprobe_check.returncode != 0:
        print("",
              "WARNING: Couldn't find ffprobe! This script may fail...",
              "On Ubuntu, this program comes with ffmpeg, so install with:",
              "",
              "  sudo apt install ffmpeg",
              "",
              sep = "\n")
    
    if ranger_check.returncode != 0:
        print("",
              "WARNING: Couldn't find ranger! This script may fail...",
              "On Ubuntu, install with:",
              "",
              "  sudo apt install ranger",
              "",
              sep = "\n")
    
    return

# .....................................................................................................................

def history_date_format():
    return "%Y/%m/%d"

# .....................................................................................................................

def history_save_data(search_directory, date_dt):
    
    # Some useful variables
    history_file = ".history.json"    
    date_str = date_dt.strftime(history_date_format())
    
    # Create a new history data
    date_str = date_dt.strftime(history_date_format())
    save_data = {"search_directory": search_directory, "last_used_date": date_str}
    
    return history_file, save_data

# .....................................................................................................................

def load_default_search_directory():
    
    # Get current date, since we'll use this to determine if the history is 'fresh' enough to use
    date_now_dt = dt.datetime.now()
    default_directory = "~/Desktop"
    
    # Save a new history file if one doesn't already exist
    history_file, default_history = history_save_data(default_directory, date_now_dt)
    if not os.path.exists(history_file):
        with open(history_file, "w") as out_file:
            json.dump(default_history, out_file, indent = 2)
    
    # Load history file and compare with current date to decide if we should use it
    with open(history_file, "r") as in_file:
        history_dict = json.load(in_file)
    
    # Pull out history data
    history_directory = history_dict.get("search_directory")
    history_date = history_dict.get("last_used_date")    
    
    # Check if the history data is fresh enough to use
    history_dt = dt.datetime.strptime(history_date, history_date_format())
    history_age_delta = (date_now_dt - history_dt)
    fresh_enough = (history_age_delta < dt.timedelta(days = 1))
    
    search_directory = history_directory if fresh_enough else default_directory
    
    return search_directory

# .....................................................................................................................

def save_search_directory(video_source):
    
    # Get data to save into history file
    date_now_dt = dt.datetime.now()
    file_directory = os.path.dirname(video_source)
    
    # Remove user pathing for cleanliness
    user_path = os.path.expanduser("~")
    save_file_directory = file_directory.replace(user_path, "~")
    
    # Construct saving dictionary and save the file!
    history_file, save_data = history_save_data(save_file_directory, date_now_dt)
    with open(history_file, "w") as out_file:
        json.dump(save_data, out_file, indent = 2)

# .....................................................................................................................

def parse_user_times(fake_date_offset, full_end_dt, start_str, end_str):
    
    # Check if either time is using relative timing
    start_is_relative = (start_str[0] == "-") or (start_str[0] == "n")
    end_is_pos_relative = (end_str[0] == "+") or (end_str[0] == "p")
    end_is_neg_relative = (end_str[0] == "-") or (end_str[0] == "n")
    
    # Error if both start and end wer egiven as relative, since the meaning is ambiguous
    if start_is_relative and end_is_pos_relative:
        raise AttributeError("Start & end times cannot both be specified using relative times!")
        
    # Clean up input strings
    start_str = (start_str[1:] if start_is_relative else start_str).strip()
    end_str = (end_str[1:] if (end_is_pos_relative or end_is_neg_relative) else end_str).strip()
    
    # Split by colons and count how many colons there are, since that will affect the interpretation
    start_split = start_str.split(":")
    end_split = end_str.split(":")
    start_num_colons = len(start_split) - 1
    end_num_colons = len(end_split) - 1
    
    # Switch/case mimicry to use the proper parsing function
    parse_func = {0: parse_0_colons, 1: parse_1_colon, 2: parse_2_colons}
    start_dt = parse_func[start_num_colons](fake_date_offset, start_split)
    end_dt = parse_func[end_num_colons](fake_date_offset, end_split)
    
    # Apply relative timing if needed
    #   (-) start -> subtract off end time 
    #   (+) end -> add to start time
    #   (-) end -> subtract off full video time
    if end_is_neg_relative:
        end_dt = full_end_dt - end_dt + fake_date_offset
    if start_is_relative:
        start_dt = end_dt - (start_dt - fake_date_offset)
    if end_is_pos_relative:
        end_dt = start_dt + (end_dt - fake_date_offset)
    
    return start_dt, end_dt

# .....................................................................................................................

def parse_0_colons(fake_date_offset, time_str_list):
    
    num_seconds = float(time_str_list[0])    
    time_dt = fake_date_offset + dt.timedelta(seconds = float(num_seconds))
    
    return time_dt

# .....................................................................................................................

def parse_1_colon(fake_date_offset, time_str_list):
    
    num_minutes = int(time_str_list[0])
    num_seconds = float(time_str_list[1]) + (60 * num_minutes)    
    time_dt = fake_date_offset + dt.timedelta(seconds = num_seconds)
    
    return time_dt

# .....................................................................................................................

def parse_2_colons(fake_date_offset, time_str_list):
    
    num_hours = int(time_str_list[0])
    num_minutes = int(time_str_list[1]) + (60 * num_hours)
    num_seconds = float(time_str_list[2]) + (60 * num_minutes)    
    time_dt = fake_date_offset + dt.timedelta(seconds = num_seconds)
    
    return time_dt

# .....................................................................................................................

def generate_default_save_name(original_video_source, start_clip_time, end_clip_time):
    
    # Get the name of the video & the original extension
    input_filename = os.path.basename(video_source)
    input_name_only, input_ext = os.path.splitext(input_filename)
    save_folder_path = os.path.dirname(original_video_source)
    
    # Convert user specified start/end times into more filename-friendly format
    start_time_str = dt.datetime.strftime(start_clip_time, "%H%M%S")
    end_time_str = dt.datetime.strftime(end_clip_time, "%H%M%S")
    
    default_output_filename = input_name_only + "-({}-to-{})".format(start_time_str, end_time_str)
    
    return default_output_filename, input_ext, save_folder_path

# .....................................................................................................................

def video_too_long_warning(fake_date_offset, video_end_dt):
    
    video_length_delta = (video_end_dt - fake_date_offset)
    max_length_delta = dt.timedelta(days = 1)
    
    if video_length_delta >= max_length_delta:
        raise NotImplementedError("Videos longer than 1 day are not (currently) supported!")

# .....................................................................................................................

def get_video_duration_sec(video_source):
    
    ''' Function to get the duration of the input video '''
    
    # Call ffprobe, which seems to be bundled with ffmpeg install
    run_command_list = ["ffprobe",
                        "-v", "error",
                        "-show_entries",
                        "format=duration", 
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        video_source]
    subproc_return = captured_subprocess(run_command_list)
    
    # Handle case where this may fail!
    if subproc_return.returncode != 0:
        print("",
              "Error reading video file duration!",
              "(This may not be a problem...)",
              sep="\n")
        return 0.0
    
    # Duration comes back as a b-string with a \n return character, so clean it up
    # (Example: b'24651.926000\n')
    duration_str = subproc_return.stdout.decode().strip()
    duration_sec = float(duration_str)

    return duration_sec

# .....................................................................................................................

def build_ffmpeg_command(input_source, start_dt, end_dt, output_path, use_exact_clip = False):
    
    # Calculate video duration, since ffmpeg -t parameters seems better than explicit end time arg
    clip_duration_sec = (end_clip_dt - start_clip_dt).total_seconds()
    t_arg = str(clip_duration_sec)
    
    # Create -ss argument value, which takes timestamps in 00:00:00 format
    ss_arg = start_clip_dt.strftime("%H:%M:%S")
    
    # Build command list for subprocess call
    run_command_list = ["ffmpeg", "-y",
                        "-ss", ss_arg, 
                        "-t", t_arg, 
                        "-i", video_source,
                        "-c", "copy", 
                        "-avoid_negative_ts", "1",
                        save_path]
    
    # Remove copy commands (-c copy) if we're clipping at exact timestamps
    if use_exact_clip:
        copy_flag_idx = 8
        run_command_list.pop(copy_flag_idx)
        run_command_list.pop(copy_flag_idx)
    
    # Also make a human reable version (by removing full pathing), in case the user needs to debug
    human_friendly_list = ["ffmpeg", 
                           "-ss", ss_arg, 
                           "-t", t_arg, 
                           "-i", "<input_path>", 
                           "-c", "copy", 
                           "-avoid_negative_ts", "1",
                           "<output_path>"]
    
    # Remove copy commands (-c copy) if we're clipping at exact timestamps
    if use_exact_clip:
        copy_flag_idx = 8
        human_friendly_list.pop(copy_flag_idx)
        human_friendly_list.pop(copy_flag_idx)
    
    human_readable_str = " ".join(human_friendly_list)
    
    return run_command_list, human_readable_str

# .....................................................................................................................

def process_feedback(subproc_return, output_save_path, human_readable_command_str):
    
    no_errors = (subproc_return.returncode == 0)
    if no_errors:
        print("",
              "*** Done! No errors ***", 
              "", 
              sep="\n")
    else:
        save_exists = os.path.exists(output_save_path)
        print("", 
              "!" * 48,
              "",
              "Possible error! Got return code: {}".format(subproc_return.returncode),
              "File {} saved...".format("was" if save_exists else "was not"),
              "",
              "Using command:",
              "  {}".format(human_readable_command_str),
              "",
              "!" * 48,
              sep="\n")

# .....................................................................................................................
# .....................................................................................................................


# ---------------------------------------------------------------------------------------------------------------------
#%% Setup
        
# Try to make sure ffmpeg and ranger are installed
check_req_installs()

# Get script arguments
input_args = parse_args()
arg_video_source = input_args.get("video")
arg_start_time = input_args.get("start")
arg_end_time = input_args.get("end")
arg_output_name = input_args.get("outname")
arg_output_path = input_args.get("outpath")
arg_exact = input_args.get("exact")

# Get file search directory
video_search_directory = load_default_search_directory()

# ---------------------------------------------------------------------------------------------------------------------
#%% Select video to clip

# Get the user to select a video or use the script argument
if arg_video_source is None:
    
    # Some feedback before suddenly jumping into ranger
    print("", "Please use ranger cli to select a video file", sep="\n")
    input("  Press Enter key to continue...")
        
    video_source = ranger_file_select(start_dir = video_search_directory)
else:
    video_source = arg_video_source
    print("", "Using input argument for video source:", "@ {}".format(video_source), sep="\n")

# Save the file directory, for easier re-use
save_search_directory(video_source)

# ---------------------------------------------------------------------------------------------------------------------
#%% Load the video to get it's data

# Get the video duration and some pathing info
video_length_sec = get_video_duration_sec(video_source)
video_folder = os.path.dirname(video_source)
video_name = os.path.basename(video_source)

# Get video end time stamp
fake_date_offset = dt.datetime(2000, 1, 1, 0, 0, 0)     # Added to all times to convert to datetime objects, easier!
video_end_dt = fake_date_offset + dt.timedelta(seconds = video_length_sec)
video_end_str = dt.datetime.strftime(video_end_dt, "%H:%M:%S")

# Error out for videos that cannot be represented with hour:minute:second timestamp alone
video_too_long_warning(fake_date_offset, video_end_dt)  # Not tested! Need some longer videos to try this


# ---------------------------------------------------------------------------------------------------------------------
#%% Have user enter start/end clip points

# Feedback about the video
print("",
      "Selected: {}".format(video_name),
      "  Total duration: {}".format(video_end_str),
      sep="\n")

# Get the user to enter a start time or use the script argument
if arg_start_time is None:
    user_start_time = cli_prompt_with_defaults("Enter starting time: ", default_value = "00:00:00", return_type = str)
else:
    user_start_time = arg_start_time
    print("", "Using input argument for start time:", "  {}".format(user_start_time), sep="\n")

# Get the user to enter an end time or use the script argument
if arg_end_time is None:
    user_end_time = cli_prompt_with_defaults("Enter ending time: ", default_value = video_end_str, return_type = str)
else:
    user_end_time = arg_end_time
    print("", "Using input argument for end time:", "  {}".format(user_end_time), sep="\n")

# Convert user entries to a common datetime format for easier manipulation
start_clip_dt, end_clip_dt = parse_user_times(fake_date_offset, video_end_dt, user_start_time, user_end_time)

# ---------------------------------------------------------------------------------------------------------------------
#%% Figure out saving

# Figure out a reasonable save name and then ask the user if they want to go with something different
default_save_name, save_ext, save_folder_path = generate_default_save_name(video_source, start_clip_dt, end_clip_dt)

# Ask the user for a file name or user the script argument
if arg_output_name is None:
    user_outname = cli_prompt_with_defaults("Enter recording name: ", 
                                            default_value = default_save_name, 
                                            return_type = str)
else:
    user_outname = arg_output_name
    print("", "Using input argument for output file name:", "  {}".format(user_outname), sep="\n")

# Overwrite the default output path if a script argument is available
if arg_output_path is not None:
    save_folder_path = arg_output_path
    print("", "Using input argument for output path:", "  {}".format(save_folder_path), sep="\n")

# Add back extension (and remove any user-added ext)
save_name = "{}{}".format(user_outname, save_ext)
save_path = os.path.join(save_folder_path, save_name)


# ---------------------------------------------------------------------------------------------------------------------
#%% *** FFMPEG Call *** 

# Some feedback
print("",
      "Clipping from/saving to:",
      "  {}".format(save_folder_path),
      "",
      "  Original: {}".format(os.path.basename(video_source)),
      "       New: {}".format(os.path.basename(save_path)),
      "",
      sep = "\n")

if arg_exact:
    print("Using exact clipping. Output file creation will take some time...", "", sep="\n")

# Run ffmpeg command to clip video (runs very fast!)
run_command_list, human_readable_str = build_ffmpeg_command(video_source, start_clip_dt, end_clip_dt, save_path,
                                                            use_exact_clip = arg_exact)
proc_out = captured_subprocess(run_command_list)

# Final feedback
process_feedback(proc_out, save_path, human_readable_str)


# ---------------------------------------------------------------------------------------------------------------------
#%% Scrap


