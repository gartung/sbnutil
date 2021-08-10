#! /usr/bin/env python
########################################################################
#
# Name: clean_sam_scratch_locations.py
#
# Purpose: Clean dead scratch locations.  Update parameter loc.scratch.
#
# Usage:
#
# clean_sam_scratch_locations.py [options]
#
# Options:
#
# -h|--help             - Print help.
# -e|--experiment <exp> - Experiment (default $SAM_EXPERIMENT).
# -n|--nfiles <n>       - Number of files to query per iteration (default no limit).
# --def <defname>       - Parent definition (optional, default none).
# --file <filename>     - File name (optional, default none).
# --niter <niter>       - Number of iterations (default 1).
#
# Usage notes:
#
#
# 1.  This script can be invoked without any options.  In that case, every
#     file in the sam database will be checked.
#
# 2.  Use options -n|--nfiles, --def, and/or --file to limit the files being
#     checked at one time.  With optin --file, only one file is checked.
#     It is generally a good idea to specify at least one of these options,
#     to limit the number of files returned by the initial sam query.
#
# 3.  The maximum number of files checked is <n>*<niter>.
#
# 4.  The initial sam query always includes clause "minus loc.scratch 0."
#
# 5.  After checking, parameter loc.scratch is updated to be one of the 
#     following values.
#
#     0 - File does not have a scratch location.
#     1 - File has a valid scratch location (file still exists).
#
########################################################################
#
# Created: 10-Aug-2021  H. Greenlee
#
########################################################################

from __future__ import print_function
import sys, os
import samweb_cli

# Statistics.

nqueried = 0
nremoved = 0
nscratch = 0
nupdated = 0

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line[2:32] == 'clean_sam_scratch_locations.py':
            doprint = 1
        elif (line.startswith('######') or line.startswith('# Usage notes:')) and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


# Check, and maybe update, parameter loc.scratch

def check_flag(samweb, f, flag):

    global nupdated

    # Get metadata for this file.

    md = samweb.getMetadata(f)
    mdflag = None
    if 'loc.scratch' in md:
        mdflag = md['loc.scratch']

    # Check whether metadata needs to be updated.

    if flag != mdflag:
        nupdated += 1
        print('Setting loc.scratch to %d for file %s' % (flag, f))
        md_update = {'loc.scratch': flag}
        samweb.modifyFileMetadata(f, md_update)

    # Done.

    return

# Check a particular location for a file.
# Returns true if the locations is valid, false if not.

def check_location(samweb, f, loc):

    global nremoved

    # Construct the full path of this file.

    dir = loc['full_path']
    ncolon = dir.find(':')
    if ncolon >= 0:
        dir = dir[ncolon+1:]
    fp = os.path.join(dir, f)
    print('Checking location %s' % fp)

    # Check whether this file actually exists.

    valid = os.path.exists(fp)

    # Remove invalid locations.

    if not valid:
        nremoved += 1
        print('Removing bad location %s' % fp)
        samweb.removeFileLocation(f, loc['location'])

    # Done

    return valid


# Check scratch locations for file.
# Return value of (possibly updated) loc.scratch parameter.

def check_file(samweb, f):

    global nscratch

    print('Checking file %s' % f)

    # Get locations.

    locs = samweb.locateFile(f)
    flag = 0
    for loc in locs:

        # Is this a scratch location?

        locloc = loc['location']
        if locloc.find('/scratch/') > 0 and locloc.find(':/pnfs/') > 0:
            valid = check_location(samweb, f, loc)
            if valid:
                nscratch += 1
                flag = 1

    # Maybe update parameter loc.scratch.

    check_flag(samweb, f, flag)

    # Done.

    return flag


# Main procedure.

def main(argv):

    global nqueried
    global nremoved
    global nscratch
    global nupdated

    # Parse arguments.

    experiment = ''
    nfiles = 0
    defname = ''
    filename = ''
    niter = 1
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
        else:
            print('Unknown option %s' % args[0])
            sys.exit(1)

    # Prepare sam query.

    samweb = samweb_cli.SAMWebClient(experiment=experiment)
    dim = ''
    if filename != '':
        dim = 'file_name %s' % filename
    elif defname != '':
        dim = 'defname: %s' % defname
    else:
        dim = 'file_id > 0'
    dim += ' minus loc.scratch 0 with availability physical,anystatus'
    if nfiles > 0:
        dim += ' with limit %d' % nfiles

    # Iteration loop.

    nremoved0 = -1
    nupdated0 = -1
    while niter > 0 and (nremoved0 != nremoved or nupdated0 != nupdated):
        nremoved0 = nremoved
        nupdated0 = nupdated
        niter -= 1
        files = samweb.listFiles(dimensions=dim)
        if len(files) == 0:
            print('No more files.')
            break
        nqueried += len(files)
        for f in files:
            check_file(samweb, f)

    # Print statistical summary.

    print('\n%d files queried.' % nqueried)
    print('%d locations removed.' % nremoved)
    print('%d valid scratch locations.' % nscratch)
    print('%d files updated metadata.' % nupdated)

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
