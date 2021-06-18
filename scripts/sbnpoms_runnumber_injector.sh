#!/bin/bash
#======================================================================
#
# Name: sbnpoms_runnumber_injector.sh
#
# Purpose: Append run and subrun overrides to fcl file.
#          Subrun follows $PROCESS+1, and wraps by incrementing
#          the run number when the subrun exceeds the maximum.
#
# Usage: sbnpoms_runnumber_injector.sh [options]
#
# Options:
#
# -h|-?|--help          - Print help message.
# --fcl <fcl>           - Fcl file to append (default standard output).
# --subruns_per_run <n> - Number of subruns per run (default 100).
# --process <process>   - Specify process number (default $PROCESS).
# --run <run>           - Specify base run number (default 1).
#
#======================================================================

# Help function
function show_help {
  awk '/# Usage:/,/#======/{print $0}' $0 | head -n -3 | cut -c3-
}

#Subrun follows $PROCESS+1

# Parse arguments.

FCL=/dev/stdout
NSUBRUNSPERRUN=100
RUN=1
MYPROCESS=$PROCESS
verbose=0
while :; do
    case $1 in
        -h|-\?|--help)
            show_help    # Display a usage synopsis.
            exit
            ;;
        --fcl)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                FCL="$2"
                shift
            else
                echo "$0 ERROR: fcl requires a non-empty option argument."
                exit 1
            fi
            ;;
        --subruns_per_run)
            if [ "$2" ]; then
                NSUBRUNSPERRUN="$2"
                shift
            else
                echo "$0 ERROR: --subruns_per_run requires a non-empty option argument."
                exit 1
            fi
            ;;
        --run)
            if [ "$2" ]; then
                RUN="$2"
                shift
            else
                echo "$0 ERROR: --run_increment requires a non-empty option argument."
                exit 1
            fi
            ;;
        --process)
            if [ "$2" ]; then
                MYPROCESS="$2"
                shift
            else
                echo "$0 ERROR: --process requires a non-empty option argument."
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

if [ -z "$FCL" ]; then
  echo "$0 ERROR: fcl is mandatory"
  exit 2
fi

#We need to extract what the default run number is.  Let's get this from running lar and dumping the config
#DEFAULTRUN=`lar --debug-config /dev/stdout -c $FCL 2> /dev/null | grep firstRun: | awk '{print $2}'#`
#if [ x$DEFAULTRUN = x ]; then
#  DEFAULTRUN=1
#fi

# Calculate run and subrun number.
RUN=$(( $MYPROCESS / NSUBRUNSPERRUN + $RUN ))
SUBRUN=$(( $MYPROCESS % NSUBRUNSPERRUN + 1 ))

# Generate fcl overrides.
echo "#Metadata injection by $0" >> $FCL
echo "source.firstRun: $RUN" >> $FCL
echo "source.firstSubRun: $SUBRUN" >> $FCL
