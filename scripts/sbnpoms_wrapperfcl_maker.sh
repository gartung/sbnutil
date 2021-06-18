#!/bin/bash
#======================================================================
#
# Name: sbnpoms_wrapperfcl_maker.sh
#
# Purpose: Make an empty wrapper fcl file.
#
# Usage: sbnpoms_wrapperfcl_maker.sh [options]
#
# Options:
#
# -h|-?|--help        - Print help message.
# --fclname <fcl>     - Wrapped fcl file.
# --wrappername <fcl> - Wrapper fcl file.
#
#======================================================================
 
# Help function
function show_help {
  awk '/# Usage:/,/#======/{print $0}' $0 | head -n -3 | cut -c3-
}

#Take in all of the arguments
verbose=0
while :; do
    case $1 in
        -h|-\?|--help)
            show_help    # Display a usage synopsis.
            exit
            ;;
        --fclname)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                FCLNAME="$2"
                shift
            else
                echo "$0 ERROR: fclname requires a non-empty option argument."
                exit 1
            fi
            ;;
        --wrappername)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                WRAPPERNAME="$2"
                shift
            else
                echo "$0 ERROR: wrappername requires a non-empty option argument."
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

if [ -z "$FCLNAME" ]; then
  echo "$0 ERROR: fclname is mandatory"
  exit 2
fi
echo "$0: FCLNAME is $FCLNAME"

if [ -z "$WRAPPERNAME" ]; then
  echo "$0 ERROR: wrappername is mandatory"
  exit 2
fi
echo "$0: WRAPPERNAME is $WRAPPERNAME"


#Start the injection
rm -f $WRAPPERNAME
echo "#Wrapper fcl created by $0" > $WRAPPERNAME
echo -e "#include \"$FCLNAME\"" >> $WRAPPERNAME
