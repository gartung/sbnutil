#! /usr/bin/env python
########################################################################
#
# Name: check_sam_locations.py
#
# Purpose: Check and optionall clean dead scratch locations.
#
# Usage:
#
# check_sam_locations.py [options]
#
# Options:
#
# -h|--help             - Print help.
# -e|--experiment <exp> - Experiment (default $SAM_EXPERIMENT).
# -r|--remove           - Remove bad locations.
# -n|--nfiles           - Maximum number of files to check.
# --def <defname>       - Parent definition (optional).
# --list <filelist>     - File list (optional).
# --file <filename>     - File name (optional).
# --invalid <file>      - Save bad locations in specified file.
#
# Usage notes:
#
#
# 1.  Specify files to check by specifying one of options --def, list, or --file.
#     Exactly one of these options must be specified.
#
# 2.  If option --invalid is specified, save bad file locations.
#
# 3.  Bad locations are not removed unless option -r or --remove is specified.
#     Use with caution.
#
########################################################################
#
# Created: 24-Mar-2022  H. Greenlee
#
########################################################################

from __future__ import print_function
import sys, os
import samweb_cli

# Statistics.

nchecked = 0    # Number of files checked.
nvalid = 0      # Number of files with valid locations.
ninvalid = 0    # Number of files with invalid locations.
nremoved = 0    # Number of invalid locations removed.
nerror = 0      # Number of errors.

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line[2:24] == 'check_sam_locations.py':
            doprint = 1
        elif (line.startswith('######') or line.startswith('# Usage notes:')) and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


# Check if it is OK to remove this path.
# This means that the first two directories (i.e. /pnfs/<expr>) must exist.

pathdict = {}

def check_path(path):

    global pathdict

    result = False

    # Extract head path.

    split_path = path.split('/')
    if len(split_path) >= 3:
        head_path = '/%s/%s' % tuple(split_path[1:3])

        # Check whether this head path has a known accessibility.

        if head_path in pathdict:
            result = pathdict[head_path]
        else:

            # Check accessibility of this head path.

            print('Checking accessibility of head path %s' % head_path)
            result = os.path.isdir(head_path)
            if result:
                print('%s is accessible' % head_path)
            else:
                print('%s is not accessible' % head_path)

            # Remember status of this path.

            pathdict[head_path] = result

    return result


# Main procedure.

def main(argv):

    global nchecked
    global nvalid
    global ninvalid
    global nremoved
    global nerror

    # Parse arguments.

    experiment = ''
    nfiles = 0
    defname = ''
    filelist = ''
    filename = ''
    invalid_file = ''
    remove = 0
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
        elif (args[0] == '--list') and len(args) > 1:
            filelist = args[1]
            del args[0:2]
        elif (args[0] == '--file') and len(args) > 1:
            filename = args[1]
            del args[0:2]
        elif args[0] == '--invalid' and len(args) > 1:
            invalid_file = args[1]
            del args[0:2]
        elif args[0] == '-r' or args[0] == '--remove':
            remove = 1
            del args[0]
        else:
            print('Unknown option %s' % args[0])
            sys.exit(1)

    f_invalid = None
    if invalid_file != '':
        if os.path.exists(invalid_file):
            os.remove(invalid_file)
        f_invalid = open(invalid_file, 'w')
        

    # Make sure no more than one of --def, --list, and --file has been specified.

    nopt = 0
    if defname != '':
        nopt += 1
    if filelist != '':
        nopt += 1
    if filename != '':
        nopt += 1
    if nopt > 1:
        print('More than one selection option from --def, --list, --file')
        sys.exit(1)

    # Initialize samweb.

    samweb = samweb_cli.SAMWebClient(experiment=experiment)

    # Construct list of files to check.

    files = []
    if nopt == 0:
        dim = 'file_id > 0 with availability physical,anystatus'
        if nfiles > 0:
            dim += ' with limit %d' % nfiles
        files = samweb.listFiles(dimensions=dim)
    elif defname != '':
        dim = 'defname: %s with availability physical,anystatus' % defname
        if nfiles > 0:
            dim += ' with limit %d' % nfiles
        files = samweb.listFiles(dimensions=dim)
    elif filelist != '':
        f = open(filelist)
        for line in f.readlines():
            files.append(os.path.basename(line.strip()))
            if nfiles > 0 and len(files) >= nfiles:
                break
        f.close()
    elif filename != '':
        files.append(os.path.basename(filename))

    print('Checking %d files' % len(files))

    # Loop over files.

    for f in files:
        nchecked += 1

        # Get locations from sam.

        locs = []
        try:
            locs = samweb.locateFile(f)
        except:
            locs = []
            nerror += 1

        # Loop over locations.

        for loc in locs:

            # Construct full path for this location.

            dir = loc['full_path']
            ncolon = dir.find(':')
            if ncolon >= 0:
                dir = dir[ncolon+1:]
            fp = os.path.join(dir, f)

            # Ignore paths that don't begin with '/pnfs/'

            if fp.startswith('/pnfs/'):
                print('Checking path %s' % fp)
                if os.path.exists(fp):
                    print('Path is valid')
                    nvalid += 1
                else:
                    print('Path is invalid')
                    ninvalid += 1
                    if f_invalid:
                        f_invalid.write('%s\n' % fp)

                    # Maybe remove this location.

                    if remove:
                        if check_path(fp):
                            print('Removing location.')
                            samweb.removeFileLocation(f, loc['location'])
                            nremoved += 1
                        else:
                            print('Location not removed because path is inaccessible')
                

    if f_invalid:
        f_invalid.close()

    # Print statistical summary.

    print('\n%d files checked.' % nchecked)
    print('%d files with valid locations.' % nvalid)
    print('%d files with invalid locations.' % ninvalid)
    print('%d locations removed.' % nremoved)
    print('%d files with errors.' % nerror)

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
