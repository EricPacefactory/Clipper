# Video Clipper (cli)

Helper script for (losslessly) clipping sections of video using ffmpeg.

(Only tested on: Linux Mint 19.1 Tessa, Python 3.5+)

## Requirements

This script relies on a command line tool called [ranger](https://github.com/ranger/ranger). On Ubuntu, this can be installed as follows:

`sudo apt install ranger`

Additionally, this script uses [FFmpeg](https://ffmpeg.org/) to clip videos. On Ubuntu, this can be installed as follows:

`sudo apt install ffmpeg`

## Usage

This script is entirely command-line based. Launch using:

`python3 clipper_cli.py`

The user is first prompted with a message about using ranger. The file system can be navigated with arrow keys in order to find a video. Use the ```Enter``` key to select a video.

Following the file selection, the user will be prompted with a start and end timestamp to use for clipping the video. Finally, a prompt for the (clipped) file name will appear. 

**Note1:** The clipping time entries accept multiple input formats. See the section below for more details.

**Note2:** Each of the prompts have default settings (which are displayed above the prompt). If nothing is entered, the default will be used.

**Note3:** The output file will be saved in the same location as the input file. This can be changed using script arguments!

**Note4:** By default, clipping is lossless, meaning that the video is not re-encoded. However, this also means that the clipped video may not have the exact timestamps specified by the user, as the clipping must occur on keyframes of the original file. If exact clipping is needed, use the appropriate script argument.

# Script Arguments

This script accepts multiple input arguments:

```
-v / --video : <String>
    Input video source (including pathing)

-s / --start : <String>
    Starting timestamp. 
    (To enter a negative relative value, type 'n' in place of '-')

-e / --end : <String>
    Ending timestamp. 
    (To enter a negative relative value, type 'n' in place of '-')
    
-n / --outname : <String>
    Output file name (no extension)
    
-p / --outpath : <String>
    Folder path for the output file (defaults to the same as the source)
    
-x / --exact : (boolean flag)
    If present, exact (re-encoded) clipping is performed
```

## Timestamp Input Formats

The clip times accept multiple formats, though they must follow a number-colon-etc. notation. The interpretation depends on the number of colons and the presence/absence of a +/- sign (for relative timestamps). For example:

```
Zero colons (ex. 17)       -> Interpretted as seconds
One colon   (ex. 7:47)     -> Interpretted as minutes : seconds
Two colons  (ex. 12:34:56) -> Interpretted as hours : minutes : seconds
```

Using two digits for each entry is not strictly required. Conventional rollovers are not required either (for example, 00:1:120 is valid and equivalent to 03:00, or 3 minutes).

#### Relative timestamps

In addition to the number-colon notation, the start timestamp can also accept a minus sign (-), while the end timestamp accepts a plus sign (+) as well as a negative sign. If the end time is relative-positive, the start time cannot also be relative!

A minus sign on the start timestamp is interpretted as a duration *before* the end timestamp. For example:

```
start_timestamp = -5:30
  end_timestamp = 00:15:00
-> start is interpretted as 5 minutes, 30 seconds before the end timestamp (e.g. 09:30)
```

Similarly, a plus sign on the end timestamp is interpretted as a duration *after* the start timestamp. For example:

```
start_timestamp = 7:45
  end_timestamp = + 45
-> end is interpretted as 45 seconds after the start timestamp (e.g. 08:30)
```

A minus sign on the end timestamp is interpretted as a duration before the end of the video. Note that the relative times continue to use the same number-colon-etc. formatting as regular timestamps.

## TODOs

- Option to change video encoding? (e.g. convert to h264)
