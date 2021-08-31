#! /usr/bin/env python
########################################################################
#
# Name: metadata_estractor.py
#
# Purpose: Metadata extractor for artroot files, based on sam_metadata_dumper.
#          Metadata is output so standard output in json format.
#
# Usage:
#
# metadata_extractor.py [options] <file>
#
# Arguments:
#
# <file> - Path of artroot file.
#
# Options:
#
# -h|--help       - Print help.
#
########################################################################
#
# Created: 31-Aug-2021  H. Greenlee
#
########################################################################

from __future__ import print_function
import sys, os, subprocess, json

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line.startswith('# metadata_extractor.py'):
            doprint = 1
        elif (line.startswith('######') or line.startswith('# Usage notes:')) and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


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

    # Done.

    return md


# Main procedure.

def main(argv):

    # Parse arguments.

    artroot = ''

    args = argv[1:]
    while len(args) > 0:
        if args[0] == '-h' or args[0] == '--help' :
            help()
            return 0
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

    # Here is where we do any desired udpates on metadata.

    mdnew = {}

    # Loop over one key to extract file name.

    for k in md:
        file_name = k
        mdnew = md[file_name]
        mdnew['file_name'] = file_name
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

    # Print metadata as pretty json string.

    json.dump(mdnew, sys.stdout, sort_keys=True, indent=2)    

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
