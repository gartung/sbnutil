#! /usr/bin/env python
########################################################################
#
# Name: metadata_estractor.py
#
# Purpose: Metadata extractor for artroot files, based on sam_metadata_dumper.
#          Metadata is output to standard output in json format.
#
# Usage:
#
# sbnpoms_metadata_extractor.py [options] <artroot-file>
#
# Arguments:
#
# <artroot-file> - Path of artroot file.
#
# Options:
#
# -h|--help - Print help.
# -e|--experiment <exp> - Experiment (default $SAM_EXPERIMENT).
#
########################################################################
#
# Created: 31-Aug-2021  H. Greenlee
#
########################################################################

import sys, os, subprocess, json
import samweb_cli

samweb = None
experiment = ''

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line.startswith('# sbnpoms_metadata_extractor.py'):
            doprint = 1
        elif (line.startswith('######') or line.startswith('# Usage notes:')) and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


# Get initialized samweb object.

def get_samweb():

    global samweb
    global experiment

    if samweb == None:
        samweb = samweb_cli.SAMWebClient(experiment=experiment)

    return samweb


# Check the validity of a single parent.
# Return value is a guaranteed valid list of parents (may be empty list)

def check_parent(parent, dir):

    result = []

    # Check whether this parent file has metadata already.

    samweb = get_samweb()
    has_metadata = False
    try:
        mdparent = samweb.getMetadata(parent)
        has_metadata = True
    except samweb_cli.FileNotFound:
        has_metadata = False

    if has_metadata:

        # If this parent has metadata, return this one file in the form of a list.

        result = [parent]

    else:

        # If this parent doesn't have metadata, try to locate file.

        local_file = os.path.join(dir, parent)
        if os.path.exists(local_file):

            # Found local file.  Extract parent information from file.

           md = get_metadata(local_file)

           if 'parents' in md:
               for prnt in md['parents']:
                   result.extend(check_parent(prnt, dir))

        else:

            # Couldn't find file.  Raise exception.

            raise FileNotFoundError

    # Done.

    return result


# Validate parents metadata according to the following method.
#
# 1.  If parent is already declared to sam, do nothing.
#
# 2.  If parent is not declared to sam, look for local file with
#     the same name in the same directory as the original file, or the
#     the current directory, and extract parents recursively from local
#     file.
#
# 3.  If parent is not declared, and there is no local file with the same
#     name can be found, raise an exception.

def validate_parents(md, dir):
    if 'parents' in md:
        parents = md['parents']
        new_parents = []
        for parent in parents:
            new_parents.extend(check_parent(parent, dir))

        if len(new_parents) == 0:

            # If updated parent list isempty, delete 'parents' from metadata.

            del md['parents']

        else:

            # Insert updated parent list into metadata.

            md['parents'] = new_parents

    # Done.

    return


# Function to extract metadata as python dictionary.

def get_metadata(artroot):

    # Run sam_metadata_dumper.

    cmd = ['sam_metadata_dumper', artroot]
    proc = subprocess.run(cmd, capture_output=True, encoding='utf8')
    if proc.returncode != 0:
        print('sam_metadata_dumper returned status %d' % proc.returncode)
        sys.exit(proc.returncode)

    # Parse json output into python dictionary.

    md = json.loads(proc.stdout)

    # Here is where we do any desired udpates on metadata.

    mdnew = {}

    # Loop over one key to extract file name.

    for k in md:
        mdnew = md[k]
        mdnew['file_name'] = k
        break

    # Add file size.

    stat = os.stat(artroot)
    mdnew['file_size'] = stat.st_size

    # Convert application family/name/version into its own dictionary

    mdnew['application'] = {}
    if 'application.family' in mdnew:
        mdnew['application']['family'] = mdnew['application.family']
        del mdnew['application.family']
    if 'art.process_name' in mdnew:
        mdnew['application']['name'] = mdnew['art.process_name']
    if 'application.version' in mdnew:
        mdnew['application']['version'] = mdnew['application.version']
        del mdnew['application.version']

    # Handle first/last event.

    if 'art.first_event' in mdnew:
        mdnew['first_event'] = mdnew['art.first_event'][2]
        del mdnew['art.first_event']
    if 'art.last_event' in mdnew:
        mdnew['last_event'] = mdnew['art.last_event'][2]
        del mdnew['art.last_event']

    # Ignore 'art.run_type' (run_type is also contained in 'runs' metadata).

    if 'art.run_type' in mdnew:
        del mdnew['art.run_type']

    # Done.

    return mdnew


# Main procedure.

def main(argv):

    global experiment

    # Parse arguments.

    artroot = ''
    experiment = ''
    if 'SAM_EXPERIMENT' in os.environ:
        experiment = os.environ['SAM_EXPERIMENT']

    args = argv[1:]
    while len(args) > 0:
        if args[0] == '-h' or args[0] == '--help' :
            help()
            return 0
        elif (args[0] == '-e' or args[0] == '--experiment') and len(args) > 1:
            experiment = args[1]
            del args[0:2]
        elif args[0].startswith('-'):
            print('Unknown option %s' % args[0])
            sys.exit(1)
        else:

            # Positional arguments.

            if artroot == '':
                artroot = args[0]
                del args[0]
            else:
                print('More than one positional argument not allowed.')
                sys.exit(1)

    # Check validity of options and arguments.

    if artroot == '':
        print('No artroot file specified.')
        sys.exit(1)

    if not os.path.exists(artroot):
        print('Artroot file %s does not exist.' % artroot)
        sys.exit(1)

    # Extract metadata as python dictionary.

    md = get_metadata(artroot)

    # Validate parent metadata.

    dir = os.path.dirname(os.path.abspath(artroot))
    validate_parents(md, dir)

    # Print metadata as pretty json string.

    json.dump(md, sys.stdout, sort_keys=True, indent=2)    

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
