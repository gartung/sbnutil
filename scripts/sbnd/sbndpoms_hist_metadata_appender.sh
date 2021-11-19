#!/bin/bash


#The metadata creation scheme makes a json file as part of the job running.  We can't pass the name of the json to the extractor so we will need to assume a json name
#The assumed json name is hist_STAGE.root.json
#The input file has been uniquely renamed by the time this script is called so we need to use some regex magic (thanks Marc!) to reconstruct the original json name

INPUTFILE="$1"
JSONFILE=`echo $INPUTFILE | sed -re 's/-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}//'`
JSONFILE="${JSONFILE}.json"


#We need to remove the braces at the end of the file as we are going to append more information
sed -i '$ d' $JSONFILE
#We also need to add a comma to the end of the last line now that we are going to add more line
sed -i '$ s/$/\,/g' $JSONFILE

#Add the filename back in
sed -i "\$a \"file_name\": \"$(basename $INPUTFILE)\"," $JSONFILE
#Add the file size
FILESIZE=`wc -c < $INPUTFILE`
sed -i "\$a \"file_size\": \"$FILESIZE\"," $JSONFILE


#calculate checksum
CHECKSUM=`samweb -e sbnd file-checksum $INPUTFILE`
sed -i "\$a \"checksum\": $CHECKSUM," $JSONFILE


#Make sure that the last entry does not have a comma at the end of its line
sed -i '$ s/,//g' $JSONFILE
#
##re-add the closing brace
sed -i '$a }' $JSONFILE

#Dump the json to std::out, needed for metadata_extractor
cat $JSONFILE
