#!/bin/bash

# Define the output directories
# These will be appended with metadata info
WORKDIR="/pnfs/sbnd/scratch/sbndpro/mcp"
OUTDIR="/pnfs/sbnd/persistent/sbndpro/mcp"
# Concatenate files together up to 1GB
MAXSIZE=1000000000

while :; do
  case $1 in
    -h|-\?|--help)
      show_help    # Display a usage synopsis.
      return
      ;;
    --defname)       # Takes an option argument; ensure it has been specified.
      if [ "$2" ]
      then
        DEFNAME="$2"
        shift 2
      else
        echo "$0 ERROR: defname requires a non-empty option argument."
        return 1
      fi
      ;;
    --workdir)       # Takes an option argument; ensure it has been specified.
      if [ "$2" ]
      then
        WORKDIR="$2"
        shift 2
      else
        echo "$0 ERROR: workdir requires a non-empty option argument."
        return 1
      fi
      ;;
    --outdir)       # Takes an option argument; ensure it has been specified.
      if [ "$2" ]
      then
        OUTDIR="$2"
        shift 2
      else
        echo "$0 ERROR: outdir requires a non-empty option argument."
        return 1
      fi
      ;;
    --size)       # Takes an option argument; ensure it has been specified.
      if [ "$2" ]
      then
        MAXSIZE="$2"
        shift 2
      else
        echo "$0 ERROR: size requires a non-empty option argument."
        return 1
      fi
      ;;
    --flatten)       # Takes an option argument; ensure it has been specified.
      FLATTEN=true
      shift
      ;;
    *) break
  esac
done

if  [ -z "$DEFNAME" ]
then
  echo "$0 ERROR: defname is mandatory"
  return 2
fi

if  [ -z "$WORKDIR" ]
then
  echo "$0 ERROR: workdir is mandatory"
  return 2
fi

if  [ -z "$OUTDIR" ]
then
  echo "$0 ERROR: outdir is mandatory"
  return 2
fi

if  [ -z "$MAXSIZE" ]
then
  echo "$0 ERROR: size is mandatory"
  return 2
fi

echo
echo "Running with settings:"
echo "  Definition: $DEFNAME"
echo "  Workdir: $WORKDIR"
echo "  Outdir: $OUTDIR"
echo "  Max Size: $(numfmt --to=si $MAXSIZE)"
if [ ! -z "$FLATTEN" ]
then
  echo "  Making Flat CAFS"
fi
echo

prepare()
{
  # Assume that the metadata is roughly the same in all files, so take the first
  FILENAME=$(samweb -e sbnd list-files "defname: $DEFNAME with limit 1")
  samweb -e sbnd get-metadata $FILENAME --json > base.json

  # Lets change "caf" to "concat_caf" for the stage and defname
  MDPRODUCTIONDEFNAME=${DEFNAME/caf/concat_caf}

  # Now we want to set some global vars to define the ouput path
  MDFILETYPE=$(jq -r '."file_type"' base.json)
  MDPRODUCTIONTYPE=$(jq -r '."production.type"' base.json)
  MDPRODUCTIONNAME=$(jq -r '."production.name"' base.json)
  MDSBNDPROJECTNAME=$(jq -r '."sbnd_project.name"' base.json)
  MDSBNDPROJECTVERSION=$(jq -r '."sbnd_project.version"' base.json)
  MDSBNDPROJECTSTAGE=$(jq -r '."sbnd_project.stage"' base.json)

  OUTDIR="$OUTDIR/$MDFILETYPE/$MDPRODUCTIONTYPE/$MDPRODUCTIONNAME/$MDSBNDPROJECTNAME/$MDSBNDPROJECTVERSION/$MDSBNDPROJECTSTAGE"
  WORKDIR="$WORKDIR/$MDFILETYPE/$MDPRODUCTIONTYPE/$MDPRODUCTIONNAME/$MDSBNDPROJECTNAME/$MDSBNDPROJECTVERSION/$MDSBNDPROJECTSTAGE"

  mkdir -p $OUTDIR
  mkdir -p $WORKDIR

  if [ -z "$(ls -A $WORKDIR)" ]
  then
    echo "WORKDIR: $WORKDIR"
  else
    echo "Not Empty: $WORKDIR"
    return 3
  fi

  if [ -z "$(ls -A $OUTDIR)" ]
  then
    echo "OUTDIR: $OUTDIR"
  else
    echo "Not Empty: $OUTDIR"
    return 3
  fi

  if [ $(samweb -e sbnd list-definitions | grep "$MDPRODUCTIONDEFNAME") ]
  then
    echo "SAM Definition $MDPRODUCTIONDEFNAME already present"
    return 3
  else
    echo "Creating SAM Definition $MDPRODUCTIONDEFNAME"
  fi

  if [ ! -z "$FLATTEN" ]
  then
    FLATMDPRODUCTIONDEFNAME=${MDPRODUCTIONDEFNAME/concat_caf/flat_caf}
    if [ $(samweb -e sbnd list-definitions | grep "$FLATMDPRODUCTIONDEFNAME") ]
    then
      echo "SAM Definition $FLATMDPRODUCTIONDEFNAME already present"
      return 3
    else
      echo "Creating flat caf SAM Definition $FLATMDPRODUCTIONDEFNAME"
    fi
  fi
}

# TODO put this into a proper script and pass arguments rather than rely on global variables
# This would allow us to run this in a background process and multithread the process
# Or submit a grid job etc.
doConcat()
{
  # Create the output
  CONCATNAME="concat_caf_${SLICENUM}.root"
  CONCATFILE="$WORKDIR/$CONCATNAME"
  JSONFILE="${CONCATFILE}.json"

  echo
  echo "Creating $CONCATNAME"

  # Let ROOT run its magic
  concat_cafs $SLICEDEFNAME $WORKDIR/$CONCATNAME

  echo "Extracting metadata"
  extractCAFMetadata "$CONCATFILE" > $JSONFILE

  # Steal the ifdh and sam commands from sbndpoms_genfclwithrunnumber_maker.sh (Thanks Dom)
  # SAM needs the file to have a unique name
  ifdh addOutputFile $CONCATFILE
  ifdh renameOutput unique

  # Bit annoying but we now need to find the fcl file again as ifdh doesn't tell us what the unique name is
  if [[ `find $WORKDIR -name "${CONCATNAME%.*}*.root" | wc -l` -ne 1 ]]
  then
    echo
    echo "Found incorrect number of matching files for pattern: ${CONCATNAME%.*}*.root"
    find $WORKDIR -name "${CONCATNAME%.*}*.root"
    echo "Exiting"
    return 3
  else
    UNIQUEOUTCONCATNAME=`find $WORKDIR -name "${CONCATNAME%.*}*.root"`
    UNIQUEOUTCONCATNAME=`basename $UNIQUEOUTCONCATNAME`
    echo
    echo "$CONCATNAME renamed to $UNIQUEOUTCONCATNAME"
    UNIQUEJSONFILE=$WORKDIR/$UNIQUEOUTCONCATNAME.json
    cp $JSONFILE $UNIQUEJSONFILE
  fi

  # OK so it looks like there is exactly one pattern match, so assume that is the correct one
  #Copy the file to the output directory (most likely dcache)
  ifdh copyBackOutput $OUTDIR
  #Clear up
  ifdh cleanup

  JSONSTORE=$WORKDIR/json_store.txt
  sbnpoms_metadata_extractor.py -e sbnd "$WORKDIR/$UNIQUEOUTCONCATNAME" > $JSONSTORE
  echo "Metadata extracted"
  rm $UNIQUEJSONFILE
  mv $JSONSTORE $UNIQUEJSONFILE

  samweb -e sbnd declare-file $UNIQUEJSONFILE
  echo
  echo "$UNIQUEOUTCONCATNAME declared by SAM"
  samweb -e sbnd add-file-location ${UNIQUEOUTCONCATNAME} $OUTDIR
  echo "$UNIQUEOUTCONCATNAME located by SAM"

  if [ ! -z "$FLATTEN" ]
  then
    echo
    echo "Flattening $UNIQUEOUTCONCATNAME"

    FLATNAME="flat_caf_${SLICENUM}.root"
    FLATFILE="$WORKDIR/$FLATNAME"
    FLATJSONFILE="${FLATFILE}.json"
    flatten_caf $OUTDIR/$UNIQUEOUTCONCATNAME $FLATFILE

    extractCAFMetadata "$FLATFILE" > "$FLATJSONFILE"

    # Steal the ifdh and sam commands from sbndpoms_genfclwithrunnumber_maker.sh (Thanks Dom)
    # SAM needs the file to have a unique name
    ifdh addOutputFile $FLATFILE
    ifdh renameOutput unique

    # Bit annoying but we now need to find the fcl file again as ifdh doesn't tell us what the unique name is
    if [[ `find $WORKDIR -name "${FLATNAME%.*}*.root" | wc -l` -ne 1 ]]
    then
      echo
      echo "Found incorrect number of matching files for pattern: ${FLATNAME%.*}*.root"
      find $WORKDIR -name "${FLATNAME%.*}*.root"
      echo "Exiting"
      return 3
    else
      UNIQUEOUTFLATNAME=`find $WORKDIR -name "${FLATNAME%.*}*.root"`
      UNIQUEOUTFLATNAME=`basename $UNIQUEOUTFLATNAME`
      echo
      echo "$FLATNAME renamed to $UNIQUEOUTFLATNAME"
      UNIQUEFLATJSONFILE=$WORKDIR/$UNIQUEOUTFLATNAME.json
      cp $FLATJSONFILE $UNIQUEFLATJSONFILE
    fi

    # OK so it looks like there it exactly one pattern match, so assume that is the correct one
    #Copy the file to the output directory (most likely dcache)
    ifdh copyBackOutput $OUTDIR
    #Clear up
    ifdh cleanup

    sbnpoms_metadata_extractor.py -e sbnd "$WORKDIR/$UNIQUEOUTFLATNAME" > $JSONSTORE
    echo "Metadata extracted"
    rm $UNIQUEFLATJSONFILE
    mv $JSONSTORE $UNIQUEFLATJSONFILE

    samweb -e sbnd declare-file "$UNIQUEFLATJSONFILE"
    echo
    echo "$UNIQUEOUTFLATNAME declared by SAM"
    samweb -e sbnd add-file-location ${UNIQUEOUTFLATNAME} $OUTDIR
    echo "$UNIQUEOUTFLATNAME located by SAM"
  fi
}

prepare

if [ $? -ne 0 ]; then
    return
fi

declare -i CONCATCOUNT=0
declare -i SLICENUM=0
declare -i FILECOUNTER=0

# Loop over all of the files in the dataset
DEFSIZE=$(samweb -e sbnd list-definition-files --summary $DEFNAME | grep "Total size" | tr -dc '0-9')
FILECOUNT=$(samweb -e sbnd count-definition-files $DEFNAME)

echo -e "\nDEFSIZE: $DEFSIZE" 
echo "FILECOUNT: $FILECOUNT"
echo "MAXSIZE: $MAXSIZE"

# Work out the size of each file
FILESIZE=$(( $DEFSIZE / $FILECOUNT ))
echo -e "\nFILESIZE: $FILESIZE"
# Work out the max number of file to concat together
SLICELIMIT=$(( $MAXSIZE / $FILESIZE ))
echo -e "\nSLICELIMIT: $SLICELIMIT"
# Work out the number of concats this will result in
CONCATCOUNT=$(( $FILECOUNT / $SLICELIMIT ))
CONCATCOUNT=$(( CONCATCOUNT + 1 ))
# Spread the files evenly between the CONCATS
FILELIMIT=$(( $FILECOUNT / $CONCATCOUNT ))
FILELIMIT=$(( FILELIMIT + 1 ))
echo -e "\nFILELIMIT: $FILELIMIT"

echo "DefSize: $DEFSIZE and FileCount: $FILECOUNT"
echo "FileSize: $FILESIZE and FileLimit: $FILELIMIT"
echo "ConcatCount: $CONCATCOUNT"

while [[ $SLICENUM -lt $CONCATCOUNT ]]
do
  FILECOUNTER=$(( $SLICENUM * $FILELIMIT ))
  echo
  echo "Creating Slice: $SLICENUM, starting from file: $FILECOUNTER"

  SLICEDEFNAME=${DEFNAME}_Slice${SLICENUM}
  samweb -e sbnd create-definition "$SLICEDEFNAME" "defname: $DEFNAME with limit $FILELIMIT with offset $FILECOUNTER"

  doConcat

  if [ $? -ne 0 ]; then
      return
  fi

  SLICENUM+=1
done

# Create a definition with the output files
samweb -e sbnd create-definition $MDPRODUCTIONDEFNAME "file_name like concat_caf_%.root and file_type $MDFILETYPE and production.type $MDPRODUCTIONTYPE and production.name $MDPRODUCTIONNAME and sbnd_project.name $MDSBNDPROJECTNAME and sbnd_project.version $MDSBNDPROJECTVERSION and sbnd_project.stage $MDSBNDPROJECTSTAGE and ischildof: ( defname: $DEFNAME ) and file_format concat_caf"
echo
echo "Created Concat SAM definition: $MDPRODUCTIONDEFNAME"
echo "$(samweb -e sbnd list-definition-files --summary $MDPRODUCTIONDEFNAME)"

if [ ! -z "$FLATTEN" ]
then
  samweb -e sbnd create-definition $FLATMDPRODUCTIONDEFNAME "file_name like flat_caf_%.root and file_type $MDFILETYPE and production.type $MDPRODUCTIONTYPE and production.name $MDPRODUCTIONNAME and sbnd_project.name $MDSBNDPROJECTNAME and sbnd_project.version $MDSBNDPROJECTVERSION and sbnd_project.stage $MDSBNDPROJECTSTAGE and ischildof: ( defname: $DEFNAME ) and file_format flat_caf"
  echo
  echo "Created Flat SAM definition: $FLATMDPRODUCTIONDEFNAME"
  echo "$(samweb -e sbnd list-definition-files --summary $FLATMDPRODUCTIONDEFNAME)"
fi
