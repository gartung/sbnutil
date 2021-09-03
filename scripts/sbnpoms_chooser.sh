#!/bin/bash
#======================================================================
#
# Name: sbnpoms_chooser.sh
#
# Purpose: Select artroot file(s), and perform various other operations.
#
# Usage: sbnpoms_chooser.sh [options]
#
# Options:
#
# -h|--help      - Print help message.
# -S <file-list> - Specify file to receive chosen files (default stdout).
# -d <directory> - Specify directory to search for root files (default ".").
# -n <n>         - Number of files to choose (default 1).
# --metadata     - Extract metadata (using sbnpoms_metadata_extractor.py) 
#                  for any artroot file in the input directory into a matching 
#                  .json file, provided .json file doesn't already exist.
# --delete       - Delete non-chosen artroot files in input directory.
#
#======================================================================
#
# Created: 2-Sep-2021  H. Greenlee
#
#======================================================================

# Help function
function show_help {
  awk '/# Usage:/,/#======/{print $0}' $0 | head -n -3 | cut -c3-
}

# Parse options.

inputdir='.'
inputlist=''
n=1
delete=0
metadata=0

while [ $# -gt 0 ]; do
  case $1 in
    -h|--help)
      show_help    # Display a usage synopsis.
      exit
      ;;

    -S)
      if [ $# -gt 1 ]; then
        inputlist="$2"
        shift
      fi
      ;;
	    
    -d)
      if [ $# -gt 1 ]; then
        inputdir="$2"
        shift
      fi
      ;;
	    
    -n)
      if [ $# -gt 1 ]; then
        n="$2"
        shift
      fi
      ;;
	    
    --metadata)
      metadata=1
      ;;
	    
    --delete)
      delete=1
      ;;
	    
    *)
      printf "$0 ERROR: Unknown option or argument: %s\n" "$1" >&2
      exit 1
      ;;
  esac
  shift
done

if [ ! -d $inputdir ]; then
  echo "No such directory $inputdir"
  exit 1
fi

# Make sure $inputlist exists, and is empty, if specified.

if [ x$inputlist != x ]; then
  rm -f $inputlist
  touch $inputlist
fi

# Loop over root files in input directory, newest first.

ls -t1 $inputdir | while read file
do
  if [ ${file: -5} = ".root" ]; then
    if isartroot.py $inputdir/$file; then

      # Found an artroot file.

      # Check whether we should extract metadata for this artroot file.

      json=$inputdir/${file}.json
      if [ $metadata -ne 0 -a ! -f $json ]; then
        echo "Generating metadata for ${file}." >&2
        sbnpoms_metadata_extractor.py $inputdir/$file > $json
      fi

      if [ $n -gt 0 ]; then
        if [ x$inputlist != x ]; then
          echo $inputdir/$file >> $inputlist
        else
          echo $inputdir/$file
        fi
      else

        # Delete this unchosen artroot file?

	if [ $delete -ne 0 ]; then
          echo "Deleting ${file}." >&2
	  rm -f $inputdir/$file
        fi
      fi

      n=$(( $n - 1 ))

      # Break out if loop of maximum number of files reached.

      #if [ $n -eq 0 ]; then
      #  break
      #fi
    fi
  fi
done

