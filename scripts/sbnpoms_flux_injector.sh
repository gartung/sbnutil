#!/bin/bash
#======================================================================
#
# Name: sbnpoms_flux_injector.sh
#
# Purpose: Add genie flux-related overrides to fcl file.
#
# Usage: sbnpoms_flux_injector.sh [options]
#
# Options:
#
# -h|-?|--help                - Print help message.
# --fcl <fcl>                 - Fcl file to append (default standard output).
# --flux_copy_method <method> - Flux copy method (default "IFDH").
# --max_flux_file_mb <n>      - Maximum size of flux files to copy (default GENIEGen decides).
#
#======================================================================

# Help function
function show_help {
  awk '/# Usage:/,/#======/{print $0}' $0 | head -n -3 | cut -c3-
}

# Parse arguments.

FCL=/dev/stdout
FLUX_COPY_METHOD=IFDH
MAX_FLUX_FILE_MB=''
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
        --flux_copy_method)
            if [ "$2" ]; then
                FLUX_COPY_METHOD="$2"
                shift
            else
                echo "$0 ERROR: --flux_copy_method requires a non-empty option argument."
                exit 1
            fi
            ;;
        --max_flux_file_mb)
            if [ "$2" ]; then
                MAX_FLUX_FILE_MB="$2"
                shift
            else
                echo "$0 ERROR: --max_flux_file_mb requires a non-empty option argument."
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

# Generate fcl overrides.
echo "#Metadata injection by $0" >> $FCL
echo "physics.producers.generator.FluxCopyMethod: $FLUX_COPY_METHOD" >> $FCL
if [ x$MAX_FLUX_FILE_MB != x ]; then
  echo "physics.producers.generator.MaxFluxFileMB: $MAX_FLUX_FILE_MB" >> $FCL
fi
