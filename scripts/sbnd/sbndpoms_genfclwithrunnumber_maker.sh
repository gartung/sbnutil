#!/bin/bash

#source.firstSubRun: 1
#Subrun follows $PROCESS+1
#After every 100 subruns, a new run is started
export NSUBRUNSPERRUN=100
export WORKDIR="/sbnd/app/users/dbrailsf/generated_fcls"
export SAMDECLARE=false

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
        --outdir)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                OUTDIR="$2"
                shift
            else
                echo "$0 ERROR: outdir requires a non-empty option argument."
                exit 1
            fi
            ;;
        --samdeclare)
            SAMDECLARE=true
            ;;
        --nfiles)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                NFILES="$2"
                shift
            else
                echo "$0 ERROR: nfiles requires a non-empty option argument."
                exit 1
            fi
            ;;
        --workdir)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                WORKDIR="$2"
                shift
            else
                echo "$0 ERROR: workdir requires a non-empty option argument."
                exit 1
            fi
            ;;
        --mdprojver)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                MDSBNDPROJECTVERSION="$2"
                shift
            else
                echo "$0 ERROR: mdprojver requires a non-empty option argument."
                exit 1
            fi
            ;;
        --mdprodname)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                MDPRODUCTIONNAME="$2"
                shift
            else
                echo "$0 ERROR: mdprodname requires a non-empty option argument."
                exit 1
            fi
            ;;
        --mdprodtype)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                MDPRODUCTIONTYPE="$2"
                shift
            else
                echo "$0 ERROR: mdprodtype requires a non-empty option argument."
                exit 1
            fi
            ;;
        --mdstagename)       # Takes an option argument; ensure it has been specified.
            if [ "$2" ]; then
                MDSTAGENAME="$2"
                shift
            else
                echo "$0 ERROR: mdstagename requires a non-empty option argument."
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
if [ -z "$OUTDIR" ]; then
  echo "$0 ERROR: outdir is mandatory"
  exit 2
fi
if [ -z "$NFILES" ]; then
  echo "$0 ERROR: nfiles is mandatory"
  exit 2
fi
if [ -z "$MDSBNDPROJECTVERSION" ]; then
  echo "$0 ERROR: mdprojver is mandatory"
  exit 2
fi
if [ -z "$MDPRODUCTIONNAME" ]; then
  echo "$0 ERROR: mdprodname is mandatory"
  exit 2
fi
if [ -z "$MDPRODUCTIONTYPE" ]; then
  echo "$0 ERROR: mdprodtype is mandatory"
  exit 2
fi
if [ -z "$MDSTAGENAME" ]; then
  echo "$0 ERROR: mdstagename is mandatory"
  exit 2
fi


echo "Running with the following settings:"
echo "  fcl name: $FCL"
echo "  outdir: $OUTDIR (note this will be appended with additional directory names!)"
echo "  workdir: $WORKDIR"
echo "  nfiles: $NFILES"
echo "  sbnd project version: $MDSBNDPROJECTVERSION"
echo "  production name: $MDPRODUCTIONNAME"
echo "  production type: $MDPRODUCTIONTYPE"
echo "  stage name: $MDSTAGENAME"
echo "  Declare to SAM: $SAMDECLARE"
#Update the output path
OUTDIR=$OUTDIR/$MDPRODUCTIONTYPE/$MDPRODUCTIONNAME/$MDSBNDPROJECTVERSION/${FCL%.*}
echo "The full output path is: $OUTDIR"
#make the directories
mkdir -p $OUTDIR
mkdir -p $WORKDIR

#We need to extract what the default run number is.  Let's get this from running lar and dumping the config
lar --debug-config lar_config_dump.txt -c $FCL
DEFAULTRUN=`grep -r "firstRun" lar_config_dump.txt`
#THis line is of the form firstRun: RUN
#We need to extract RUN
#Delimit on the colon
IFS=\: read -a DEFAULTRUNARRAY <<<"$DEFAULTRUN"
#Extract the run number
DEFAULTRUN=${DEFAULTRUNARRAY[1]}

#starting making the files
NPROCESSEDFILES=0
#Needed to make subruns always start at 1
let "SUBRUNCANDIDATE= 0"
while [[ $NPROCESSEDFILES -lt $NFILES ]]
do
#Do arithmetic to modulo-ise the run number and subrun number whilst making sure subrun always starts at 1
  let "SUBRUNCANDIDATE++"
  RUNINCREMENT=$((SUBRUNCANDIDATE/NSUBRUNSPERRUN))
  let "RUNNUMBER= $DEFAULTRUN + $RUNINCREMENT"
  SUBRUNNUMBER=$((SUBRUNCANDIDATE%NSUBRUNSPERRUN))
#Never let subrun be 0
  if [[ $SUBRUNNUMBER -eq 0 ]]
  then
   continue
  fi
#We now have  run and subrun number
#make the fcl
  OUTFCL="${FCL%.*}_run${RUNNUMBER}_subrun${SUBRUNNUMBER}.fcl"
  if [ -e $WORKDIR/$OUTFCL ]
  then
    rm $WORKDIR/$OUTFCL
  fi
  echo "Producing $WORKDIR/$OUTFCL"
  echo -e "#include \"$FCL\"\n" \
          "source.firstRun: $RUNNUMBER\n" \
          "source.firstSubRun: $SUBRUNNUMBER" >> $WORKDIR/$OUTFCL
  #Append all of the other metadata needed for the job
  sbnpoms_metadata_injector.sh --inputfclname ${WORKDIR}/${OUTFCL} --mdfclname ${FCL} --mdprojectname ${FCL%.*} --mdprojectstage $MDSTAGENAME --mdprojectversion ${MDSBNDPROJECTVERSION} --mdprojectsoftware sbndcode --mdproductionname ${MDPRODUCTIONNAME} --mdproductiontype ${MDPRODUCTIONTYPE} --mdappversion ${MDSBNDPROJECTVERSION} --mdfiletype mc --mdappfamily art --mdruntype physics --tfilemdjsonname hist_${MDSTAGENAME}.root.json --mdgroupname sbnd


  #make the fcl have a unique name (needed for SAM)
  ifdh addOutputFile $WORKDIR/$OUTFCL
  ifdh renameOutput unique
  #Bit annoying but we now need to find the fcl file again as ifdh doesn't tell us what the unique name is
  if [[ `find $WORKDIR -name ${OUTFCL%.*}*.fcl | wc -l` -ne 1 ]]
  then
    echo "Found incorrect number of matching fcl files for pattern: $OUTFCL"
    find $WORKDIR -name ${OUTFCL%.*}*.fcl
    echo "Exiting"
    exit 3
  fi
  # OK so it looks like there it exactly one pattern match, so assume that is the correct one
  UNIQUEOUTFCL=`find $WORKDIR -name ${OUTFCL%.*}*.fcl`
  UNIQUEOUTFCL=`basename $UNIQUEOUTFCL`
  #Copy the fcl to the output directory (most likely dcache)
  ifdh copyBackOutput $OUTDIR
  #Clear up
  ifdh cleanup

#echo $name

  #Now make a json
  echo -e "
  {
      \"file_type\": \"mc\",
      \"group\": \"sbnd\",
      \"fcl.name\": \"$UNIQUEOUTFCL\",
      \"sbnd_project.name\": \"${FCL%.*}\",
      \"sbnd_project.stage\": \"fcl\",
      \"sbnd_project.version\": \"$MDSBNDPROJECTVERSION\",
      \"sbnd_project.software\": \"sbndcode\",
      \"production.name\": \"$MDPRODUCTIONNAME\",
      \"production.type\": \"$MDPRODUCTIONTYPE\",
      \"data_tier\": \"initial-fcl\",
      \"file_format\": \"fcl\",
      \"start_time\": \"`date +"%FT%T"`\",
      \"end_time\": \"`date +"%FT%T"`\",
      \"runs\": [ [ $RUNNUMBER, $SUBRUNNUMBER, \"physics\" ] ],
      \"event_count\": 0,
  \"first_event\":  -9999 ,
  \"last_event\":  -9999 ,
  \"group\": \"sbnd\",
    \"file_name\": \"$UNIQUEOUTFCL\",
    \"file_size\": \"`wc -c < $WORKDIR/$UNIQUEOUTFCL`\",
    \"checksum\": 
      `ifdh checksum $WORKDIR/$UNIQUEOUTFCL`

  }
  " >> $WORKDIR/${UNIQUEOUTFCL}.json
  if [ "$SAMDECLARE" = true ];
  then
    echo "Declaring ${UNIQUEOUTFCL} to SAM"
    samweb -e sbnd declare-file ${WORKDIR}/${UNIQUEOUTFCL}.json
    samweb -e sbnd add-file-location ${UNIQUEOUTFCL} $OUTDIR
  fi
  let "NPROCESSEDFILES++"
done


if [ "$SAMDECLARE" = true ];
then
  echo "Making SAM dataset"
  #Need to store the chopped up FCL name in a var as samweb has trouble parsing the %
  TRUNCFCL=${FCL%.*}
  samweb -e sbnd create-definition ${MDPRODUCTIONTYPE}_${MDPRODUCTIONNAME}_${FCL%.*}_initialfcl_sbnd "file_name like ${TRUNCFCL}%.fcl and sbnd_project.version $MDSBNDPROJECTVERSION and production.type $MDPRODUCTIONTYPE and production.name $MDPRODUCTIONNAME"

  samweb -e sbnd create-definition ${MDPRODUCTIONTYPE}_${MDPRODUCTIONNAME}_${FCL%.*}_initialfcl_sbnd "file_name like ${TRUNCFCL}%.fcl and sbnd_project.version $MDSBNDPROJECTVERSION and production.type $MDPRODUCTIONTYPE and production.name $MDPRODUCTIONNAME"
fi

##Calculate how much to increment the run by
#RUNINCREMENT=`python -c "print $SUBRUNCANDIDATE//$NSUBRUNSPERRUN"`
##Calculate the run number
#let "RUNNUMBER= $DEFAULTRUN + $RUNINCREMENT"
##Now the subrun
#SUBRUNNUMBER=`python -c "print $SUBRUNCANDIDATE % $NSUBRUNSPERRUN"`
#echo "#Metadata injection by $0" >> $FCL
#echo "source.firstRun: $RUNNUMBER" >> $FCL
#echo "source.firstSubRun: $SUBRUNNUMBER" >> $FCL
