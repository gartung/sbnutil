#!/bin/bash
#======================================================================
#
# Name: sbnpoms_chooser.sh
#
# Purpose: Select artroot file(s), and perform various other "between exe"
#          operations.
#
# Usage: sbnpoms_chooser.sh [options]
#
# Options:
#
# -h|--help      - Print help message.
# -S <file-list> - Specify file to receive chosen files (default none).
# -d <directory> - Specify directory to search for root files (default ".").
# -n <n>         - Number of artroot files to choose (default 1).
# --metadata     - Extract metadata (using sbnpoms_metadata_extractor.py) 
#                  for any artroot file in the input directory into a matching 
#                  .json file, provided .json file doesn't already exist.
# --delete       - Delete non-chosen artroot files in input directory.
# --match        - Match unpaired non-artroot root files and unpaired json files.  
#                  Rename json file to match root file.
#
#======================================================================
#
# Usage notes.
#
# 1.  Choose artroot files based on newest first.
#
# 2.  Match non-artroot root files and json files based on newest vs. newest.
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
match=0

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
	    
    --match)
      match=1
      ;;
	    
    *)
      printf "$0 ERROR: Unknown option or argument: %s\n" "$1"
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

# Arrays used by matching function.

declare -a unmatched_json
declare -a unmatched_root

# Maybe fill array of unmatched json files (newest first).
# Do this before generating any json files in this script, obviously.

if [ $match -ne 0 ]; then

  # Loop over json files in input directory, newest first.

  while read json; do
    if [ ${json: -5} = ".json" ]; then

      # Ignore any json file that contains a line like "file_format": "artroot"

      if ! grep -q 'file_format.*artroot' $inputdir/$json; then

        # Do require json file to contain a line like "file_format": "root"

        if grep -q 'file_format.*root' $inputdir/$json; then
          root=${json::-5}
          if [ ! -f $inputdir/$root ]; then
            echo "Found unmatched json file $inputdir/$json"
            unmatched_json[${#unmatched_json[@]}]=$inputdir/$json
          fi
        fi
      fi
    fi
  done < <(ls -t1 $inputdir )
fi

# Loop over root files in input directory, newest first.

while read root; do
  if [ ${root: -5} = ".root" ]; then
    json=${root}.json
    isartroot.py $inputdir/$root
    stat=$?
    if [ $stat -eq 0 ]; then

      # This is an artroot file.
      # Check whether we should extract metadata for this artroot file.

      if [ $metadata -ne 0 -a ! -f $inputdir/$json ]; then
        echo "Generating metadata for ${root}."
        sbnpoms_metadata_extractor.py $inputdir/$root > $inputdir/$json
      fi

      if [ $n -gt 0 ]; then

	# Choose this artroot file.

        if [ x$inputlist != x ]; then
          echo "Adding $inputdir/$root to input list."
          echo $inputdir/$root >> $inputlist
        fi
      else

        # Delete this unchosen artroot file?

	if [ $delete -ne 0 ]; then
          echo "Deleting ${root}."
	  rm -f $inputdir/$root
        fi
      fi

      # Decrement choose count.

      n=$(( $n - 1 ))

    elif [ $stat -eq 1 ]; then

      # This is a plain root file.
      # Maybe add this root file to unmatched plain root array.

      if [ $match -ne 0 -a ! -f $inputdir/$json ]; then
	echo "Found unmatched plain root file $inputdir/$root"
        unmatched_root[${#unmatched_root[@]}]=$inputdir/$root
      fi
    fi
  fi
done < <(ls -t1 $inputdir )

if [ x$inputlist != x ]; then
  ni=`cat $inputlist | wc -l`
  echo "$ni files added to input list."
fi

# Rest of matching function handled here.

if [ $match -ne 0 ]; then
  nmatch=${#unmatched_root[@]}
  if [ $nmatch -gt ${#unmatched_json[@]} ]; then
    nmatch=${#unmatched_json[@]}
  fi
  echo "Matched $nmatch plain root and json files."

  m=0
  while [ $m -lt $nmatch ]; do
    root=${unmatched_root[$m]}
    json=${unmatched_json[$m]}
    newjson=${root}.json
    if [ $json != $newjson -a -f $json -a ! -f $newjson ]; then
      echo "Renaming json file:"
      echo "From: $json"
      echo "To:   $newjson"
      mv $json $newjson
    fi
    m=$(( $m + 1 ))
  done
fi

