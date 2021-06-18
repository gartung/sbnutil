#!/bin/bash
 
#Take in all of the arguments
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

#        --file=?*)
#            file=${1#*=} # Delete everything up to "=" and assign the remainder.
#            ;;
#        --file=)         # Handle the case of an empty --file=
#            echo 'ERROR: "--file" requires a non-empty option argument.'
#            ;;
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
echo "#Wrapper fcl created by $0" >> $WRAPPERNAME
echo -e "#include \"$FCLNAME\"" >> $WRAPPERNAME
