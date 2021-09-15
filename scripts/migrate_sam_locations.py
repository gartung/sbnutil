#! /usr/bin/env python
########################################################################
#
# Name: migrate_sam_locations.py
#
# Purpose: Migrate locations from source SAM database (SBND or ICARUS) to 
#          target SAM database (SBN).
#
# Usage:
#
# migrate_sam_locations.py [options]
#
# Options:
#
# -h|--help             - Print help.
# -e|--experiment <exp> - Experiment (default $SAM_EXPERIMENT).
# -n|--nfiles <n>       - Number of files to query per iteration (default no limit).
# --def <defname>       - Parent definition (optional, default none).
# --file <filename>     - File name (optional, default none).
# --niter <niter>       - Number of iterations (default 1).
# --scratch             - Migrate scratch locations (default no scratch).
#
# Usage notes.
#
# 1.  This script is a companion to migrate_sam_files.py.  Migrate_sam_files.py
#     also migrates locations, but never migrates scrartch locations.  This
#     script can be used to migrate scratch locations (if inoked with option 
#     --scratch).
#
# 2.  This script never updates any sam metadata in either the source or
#     target sam database.  This implies that in order to migrate locations.
#     metadata must exist in both databases already (e.g. by invoking 
#     migrate_sam_files.py).
#
########################################################################
#
# Created: 15-Sep-2021  H. Greenlee
#
########################################################################

from __future__ import print_function
import sys, os
import samweb_cli

# Statistics.

nqueried = 0
nlocations = 0

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line[2:26] == 'migrate_sam_locations.py':
            doprint = 1
        elif (line.startswith('######') or line.startswith('# Usage notes:')) and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


# Check file locations.
# Return True if location check was successful, False otherwise.

def check_locations(samweb1, samweb2, f, doscratch):

    global nlocations

    print('Checking locations for file %s' % f)
    locs1 = samweb1.locateFile(f)
    locs2_ok = False
    locs2 = []
    try:
        locs2 = samweb2.locateFile(f)
        locs2_ok = True
    except:
        locs2 = []
        locs2_ok = False

    # If locate-file failed in target database, that means that this file has not been
    # declared in the target database.
    # There are use cases where this can happen.
    # In these case, print an error message and quit.

    if not locs2_ok:
        print('Unable to check locations for file %s' % f)
        print('File may not be declared.')
        return False

    has_loc1 = False
    for loc1 in locs1:
        has_loc1 = True
        fp1 = loc1['full_path']
        if not doscratch and fp1.find('/scratch/') > 0:
            print('Skipping scratch location %s' % fp1)
        else:
            print('Checking location %s' % fp1)

            # Look for location with the same full_path.

            loc_match = False
            for loc2 in locs2:
                fp2 = loc2['full_path']
                if fp2 == fp1:
                    loc_match = True
                    break
            if loc_match:
                print('Location already exists in target database.')
            else:
                print('Adding location in target database.')
                samweb2.addFileLocation(f, loc1['location'])
                nlocations += 1

    if not has_loc1:
        print('No locations found.')

    # Done.

    return True


# Main procedure.

def main(argv):

    global nqueried
    global nlocations

    # Parse arguments.

    experiment = ''
    nfiles = 0
    defname = ''
    filename = ''
    niter = 1
    doscratch = False
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
        elif (args[0] == '-n' or args[0] == '--nfiles') and len(args) > 1:
            nfiles = int(args[1])
            del args[0:2]
        elif (args[0] == '--def') and len(args) > 1:
            defname = args[1]
            del args[0:2]
        elif (args[0] == '--file') and len(args) > 1:
            filename = args[1]
            del args[0:2]
        elif args[0] == '--niter' and len(args) > 1:
            niter = int(args[1])
            del args[0:2]
        elif args[0] == '--scratch':
            doscratch = True
            del args[0]
        else:
            print('Unknown option %s' % args[0])
            sys.exit(1)

    # Prepare sam query.

    samweb1 = samweb_cli.SAMWebClient(experiment=experiment)
    samweb2 = samweb_cli.SAMWebClient(experiment='sbn')
    dim = ''
    if filename != '':
        dim = 'file_name %s' % filename
    elif defname != '':
        dim = 'defname: %s' % defname
    else:
        dim = 'file_id > 0'
    dim += ' with availability physical,anystatus'
    if nfiles > 0:
        dim += ' with limit %d' % nfiles

    # Iteration loop.

    while niter > 0:
        niter -= 1
        files = samweb1.listFiles(dimensions=dim)
        if len(files) == 0:
            print('No more files.')
            break
        nqueried += len(files)
        for f in files:
            check_locations(samweb1, samweb2, f, doscratch)

    # Print statistical summary.

    print('\n%d files queried.' % nqueried)
    print('%d locations added.' % nlocations)

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
