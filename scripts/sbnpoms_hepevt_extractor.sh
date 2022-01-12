#!/bin/bash
#======================================================================
#
# Name: sbnpoms_hepevt_extractor.sh
#
# Purpose: Extract a subset of events from a hepevt text file.
#
# Usage: sbnpoms_hepevt_extractor.sh [options]
#
# Options:
#
# -h|-?|--help          - Print help message.
# -i|--input            - Specify input hepevt text file (no default).
# -o|--output           - Specify output hepevt text file
#                         (default HEPevents.txt in current directory).
# -n <nev>              - Number of events to extract (default 20).
# --nskip <nev>         - Number of events to skip (default 0).
# --nskip_process <nev> - Number of events to skip per process (default same as -n).
# --process <proc>      - Override $PROCESS environment variable for the
#                         purpose of calculating skip events.
#
#======================================================================
#
# Usage notes.
#
# 1.  This script will look for the input file in the current directory,
#     and in $CONDOR_DIR_INPUT.
#
# 2.  Skipping of events is controlled by two options --nskip and --nskip_process.
#     If argument of --nskip_process is nonzero, the number of events skipped
#     is obtained by multiplying the argument by process number $PROCESS.
#     Both options may be specified, in which case the total number of events
#     skipped is the sum of both.
#
# Created: 11-Jan-2022  H. Greenlee
#
#======================================================================


# Help function
function show_help {
  awk '/# Usage:/,/#======/{print $0}' $0 | head -n -3 | cut -c3-
}

# Parse arguments.

INPUT=''
OUTPUT=HEPevents.txt
NEV=20
NSKIP=0
NSKIP_PROCESS=''
verbose=0
while :; do
    case $1 in
        -h|-\?|--help)
            show_help    # Display a usage synopsis.
            exit
            ;;
        -i|--input)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                INPUT="$2"
                shift
            else
                echo "$0 ERROR: input requires a non-empty option argument."
                exit 1
            fi
            ;;
        -o|--output)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                OUTPUT="$2"
                shift
            else
                echo "$0 ERROR: output requires a non-empty option argument."
                exit 1
            fi
            ;;
        -n)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                NEV="$2"
                shift
            else
                echo "$0 ERROR: n requires a non-empty option argument."
                exit 1
            fi
            ;;
        --nskip)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                NSKIP="$2"
                shift
            else
                echo "$0 ERROR: nskip requires a non-empty option argument."
                exit 1
            fi
            ;;
        --nskip_process)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                NSKIP_PROCESS="$2"
                shift
            else
                echo "$0 ERROR: nskip_process requires a non-empty option argument."
                exit 1
            fi
            ;;
        --process)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                PROCESS="$2"
                shift
            else
                echo "$0 ERROR: process requires a non-empty option argument."
                exit 1
            fi
            ;;
        -v|--verbose)
            verbose=$((verbose + 1))  # Each -v adds 1 to verbosity.
            ;;
        --)              # End of all options.
            shift
            break
            ;;
        -?*)
            printf "$0 WARN: Unknown option (ignored): %s\n" "$1" >&2
            ;;
        *)               # Default case: No more options, so break out of the loop.
            break
    esac
    shift
done

# Validate NSKIP_PROCESS.

if [ x$NSKIP_PROCESS = x ]; then
  NSKIP_PROCESS=$NEV
fi

# Validate input.

if [ x$INPUT = x ]; then
  echo "No input specified."
  exit 1
fi
if [ ! -f $INPUT -a x$CONDOR_DIR_INPUT != x ]; then
  altinput=$CONDOR_DIR_INPUT/`basename $INPUT`
  if [ -f $altinput ]; then
    INPUT=$altinput
  fi
fi
if [ ! -f $INPUT ]; then
  echo "Input file $INPUT not found."
  exit 1
fi

# Make sure $PROCESS is defined (define as zero if undefined).

if [ x$PROCESS = x ]; then
  export PROCESS=0
fi

# Calculate total number of events to skip.

NSKIP_TOTAL=$(( $NSKIP + $NSKIP_PROCESS * $PROCESS ))

# Calculate the total number of events to read.

NEV_TOTAL=$(( $NSKIP_TOTAL + $NEV ))

# Loop over hepevt events

n=0
rm -f $OUTPUT
while read evnum npart
do
  if [ $n -ge $NSKIP_TOTAL ]; then
    echo $evnum $npart >> $OUTPUT
  fi

  # Loop over particles in event.

  while [ $npart -gt 0 ]
  do
    read line
    if [ $n -ge $NSKIP_TOTAL ]; then
      echo $line >> $OUTPUT
    fi    
    npart=$(( $npart - 1 ))
  done

  # Done with event.

  n=$(( $n + 1 ))
  if [ $n -ge $NEV_TOTAL ]; then
    exit
  fi
done < $INPUT
