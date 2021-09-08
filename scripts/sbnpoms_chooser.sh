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
# -h|--help        - Print help message.
# -S <list>        - Specify list file to receive chosen files (default none).
# -d <directory>   - Specify directory to search for root files (default ".").
# -n <n>           - Number of artroot files to choose (default 1).
# --metadata       - Extract metadata (using sbnpoms_metadata_extractor.py) 
#                    for any artroot file in the input directory into a matching 
#                    .json file, if the .json file doesn't already exist.
# --delete <list>  - Delete files in the specified list file.
# --match          - Match unpaired non-artroot root files and unpaired json files.  
#                    Rename json file to match root file.
# --max_length <n> - Maximum file name length (default 200, 0 = no limit)
# --unique         - Ensure that .root file names are unique (rename). 
#
#======================================================================
#
# Usage notes.
#
# 1.  Actions are performed in the following order:
#     a) Rename files to ensure unique name (option --unique) or because of 
#        maximum file name length (option --max_length).
#     b) Metadata extraction for artroot files (--metadata option).
#     c) Delete specified files (--delete option).
#     d) Match json and plain root files (--match option).
#     e) Clean up external json metadata (add or update file_name, file_size,
#        and parentage).
#     f) Select artroot files for next executable (-S option).
#
# 2.  The recommended way to invoke this script is with all action
#     options following each batch job executable.
#
#     # sbnpoms_chooser.sh -S input.list --delete input.list --metadata --match
#
#     Note the following.
#
#     a) Input list (-S option) and delete list (--delete option) can be the
#        same file.
#     b) Always specify option --metadata if you use option --delete, unless you
#        don't care about metadata (otherwise metadata extraction will fail).
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
deletelist=''
metadata=0
match=0
max_length=200
unique=0

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
      if [ $# -gt 1 ]; then
        deletelist="$2"
        shift
      fi
      ;;
	    
    --match)
      match=1
      ;;
	    
    --max_length)
      if [ $# -gt 1 ]; then
        max_length="$2"
        shift
      fi
      ;;
	    
    --unique)
      unique=1
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

# Do renaming actions (--unique and --max_length).

if [ $unique -ne 0 -o $max_length -gt 0 ]; then

  # Loop over root files.

  while read root; do
    if [ x${root: -5} = x.root ]; then
      json=${root}.json

      # Check whether this file appears to end with a uuid.
      # A normal uuid has 32 hex digits and 4 hyphens arranged in groups
      # of 8-4-4-4-12.

      has_uuid=0
      if basename $root .root | grep -q '^.*[0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z]-[0-9a-z][0-9a-z][0-9a-z][0-9a-z]-[0-9a-z][0-9a-z][0-9a-z][0-9a-z]-[0-9a-z][0-9a-z][0-9a-z][0-9a-z]-[0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z]$'; then
	has_uuid=1
      fi

      # Check whether this file name is too long.
      # Note that "wc -c" counts terminating null character.

      too_long=0
      nchar=`echo $root | wc -c`
      if [ $max_length -gt 0 -a $nchar -gt $max_length ]; then
        too_long=1
      fi

      # Do we want to rename this file?

      rename=0
      if [ $too_long -ne 0 ]; then
        echo "Renaming $root because name is too long."
        rename=1
      fi

      if [ $unique -ne 0 -a $has_uuid -eq 0 ]; then
        echo "Renaming $root because name does not end in a uuid."
        rename=1
      fi

      if [ $rename -ne 0 ]; then

        # Calculate the stem part of the renamed file (the part before appended uuid).
        # A uuid has 36 characters.  Therefore, the uuid and file type (.root)
        # will have 41 characters.
        # Make the stem part of the file name 42 less than max_length.  This way
        # the renamed file will have a maximum length of one less than max_length.
	# if max_length is less than 42, the renamed file will consist of only
        # a uuid and file type.

	stem=''
        if [ $max_length -eq 0 ]; then

          # No length limit.  Use the entire file name as stem.

          stem=`basename $root .root`

        elif [ $max_length -gt 42 ]; then

          # Truncate stem have at most max_length - 42 characters.

	  nch=$(( $max_length - 42 ))
          stem=`basename $root .root | cut -c1-$nch`

        fi

        # Calculate new name and new json file name.

	uuid=`uuidgen`
        newroot="${stem}${uuid}.root"
        newjson=${newroot}.json

        # Do the actual rename.

	echo "Renaming file."
        echo "From: $inputdir/$root"
        echo "To:   $inputdir/$newroot"
        mv $inputdir/$root $inputdir/$newroot

        # If json file exists, rename it too.
        # File_name field, if any will be fixed up during metadata checks below.

        if [ -f $inputdir/$json ]; then
          mv $inputdir/$json $inputdir/$newjson
        fi
      fi
    fi
  done < <(ls $inputdir )

fi

# Do artroot metadata extraction (--metadata option).
# This needs to be done before deleting any .root files.

if [ $metadata -ne 0 ]; then
  while read root; do
    if [ x${root: -5} = x.root ]; then
      json=${root}.json
      if isartroot.py $inputdir/$root; then

        # This is an artroot file.
        # Check whether we should extract metadata for this artroot file.

        if [ ! -f $inputdir/$json ]; then
          echo "Generating metadata for ${root}."
          sbnpoms_metadata_extractor.py $inputdir/$root > $inputdir/$json
        fi
      fi
    fi
  done < <(ls -t1 $inputdir )
fi

# Do delete action.
# This needs to be done before generating next input list in case
# delete list and input list are the same.

if [ x$deletelist != x ]; then
  if [ -f $deletelist ]; then
    while read f; do
      echo "Deleting $f"
      rm -f $f
    done < $deletelist
  else
    echo "Delete list $deletelist does not exist."
  fi
fi

# Do matching function.

declare -a unmatched_json
declare -a unmatched_root
if [ $match -ne 0 ]; then

  # Identify unmatched json files in input dirctory.
  # Loop over json files in input directory, newest first.

  while read json; do
    if [ x${json: -5} = x.json ]; then

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

  # Identify ummatched plain root files.
  # Loop over root files in input directory, newest first.

  while read root; do
    if [ x${root: -5} = x.root ]; then
      json=${root}.json
      if isartroot.py -n $inputdir/$root; then

        # This is a plain root file.
        # Maybe add this root file to unmatched plain root array.

        if [ ! -f $inputdir/$json ]; then
	  echo "Found unmatched plain root file $inputdir/$root"
          unmatched_root[${#unmatched_root[@]}]=$inputdir/$root
        fi
      fi
    fi
  done < <(ls -t1 $inputdir )

  # Do actual matching.

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

# Do metadata cleanups for root files with matching json files.
# Do this unconditionally.

# Loop over files.

while read root; do
  if [ x${root: -5} = x.root ]; then
    json=${root}.json
    if [ -f $inputdir/$json ]; then
      echo "Checking metadata for file $root"
      newjson=${json}.new

      # Re-extract metadata

      rm -f $newjson
      sbnpoms_metadata_extractor.py $inputdir/$root > $newjson
      if ! diff -q $inputdir/$json $newjson; then
        echo "Updating metadata."
	rm -f $inputdir/$json
        cp $newjson $inputdir/$json
        rm -f $newjson
      else
        echo "Metadata is OK."
      fi
    fi
  fi
done < <( ls $inputdir )

# Do input selection for next stage.

if [ x$inputlist != x -a $n -gt 0 ]; then

  # Make sure $inputlist exists, and is empty.

  rm -f $inputlist
  touch $inputlist

  # Loop over artroot files in input directory, newest first.

  while read root; do
    if [ x${root: -5} = x.root ]; then
      if isartroot.py $inputdir/$root; then

        # This is an artroot file.

        if [ $n -gt 0 ]; then

	  # Add this file to input list.

          echo "Adding $inputdir/$root to input list."
          echo $inputdir/$root >> $inputlist

          # Decrement choose count.

          n=$(( $n - 1 ))
        fi
      fi
    fi
  done < <(ls -t1 $inputdir )
  ni=`cat $inputlist | wc -l`
  echo "$ni files added to input list."
fi
