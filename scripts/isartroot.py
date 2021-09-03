#! /usr/bin/env python
########################################################################
#
# Name: isartroot.py
#
# Purpose: Test whether file is an artroot file.  With no options, return 
#          exit status 0 if file is an artroot file, nonzero otherise.
#
# Usage:
#
# isartroot.py [options] <file>
#
# Options:
#
# -h|--help    - Print help.
# -n|--invert  - Invert selection (return status 0 for non-artroot root file).
# -a|--anyroot - Return status 0 for any valid root file.
# -v|--verbose - Print a human-readable message that matches return status.
#
# Arguments:
#
# <file> - Path of file.
#
########################################################################
#
# Use cases.
#
# 1.  File is a valid artroot file.
#
#     Return status 0.  Do not generate any output (unless -v specified).
#     Return status 1 if invoked with option -n.
#
# 2.  File is a valid root file, but not an artroot file.
#
#     Return status 1.  Do not generate any output (unless -v specified).
#     Return status 0 if invoked with option -n or -a.
#
# 3.  File is not a valid root file.
#
#     Return status 2.  Root may generate an error message.
#
# 4.  File does not exist.
#
#     Return status 3.  Print an error message.
#
# 5.  Other errors (invalid options or arguments).
#
#     Return status 4.  Print an error message.
#
# Created: 2-Sep-2021  H. Greenlee
#
########################################################################

import sys, os

# Import ROOT module.  Hide command line arguments from ROOT module.
myargv = sys.argv
sys.argv = myargv[0:1]

import ROOT
sys.argv = myargv


# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line.startswith('# Usage:'):
            doprint = 1
        elif (line.startswith('######') or line.startswith('# Usage notes:')) and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


# Main procedure.

def main(argv):

    global experiment

    # Parse arguments.

    filepath = ''
    invert = False
    anyroot = False
    verbose = False

    args = argv[1:]
    while len(args) > 0:
        if args[0] == '-h' or args[0] == '--help' :
            help()
            return 0
        if args[0] == '-n' or args[0] == '--invert' :
            invert = True
            del args[0]
            continue
        if args[0] == '-a' or args[0] == '--anyroot' :
            anyroot = True
            del args[0]
            continue
        if args[0] == '-v' or args[0] == '--verbose' :
            verbose = True
            del args[0]
            continue
        elif args[0].startswith('-'):
            print('Unknown option %s' % args[0])
            return 4
        else:

            # Positional arguments.

            if filepath == '':
                filepath = args[0]
                del args[0]
            else:
                print('More than one positional argument not allowed.')
                return 4

    # Check validity of options and arguments.

    if filepath == '':
        print('No file specified.')
        return 4

    if invert and anyroot:
        print('Both -a and -n options specified.')
        return 4

    if not os.path.exists(filepath):
        print('File %s does not exist.' % filepath)
        return 3

    # Open file using root.
    # If file can't be opened, return non-zero status (not artroot).

    input = ROOT.TFile.Open(filepath)
    if not input or not input.IsOpen():
        if verbose:
            print('%s exists but is not a valid root file.' % filepath)
        return 2

    # File was opened successfully by root.
    # If anyroot option, return status 0 immediately.

    if anyroot:
        if verbose:
            print('%s is a valid root file.' % filepath)
        return 0

    # Try to get object RootFileDB (internal artroot sqlite database).
    # If there is no such object, this is non-artroot root file.

    obj = input.Get('RootFileDB')
    if not obj:
        if verbose:
            print('%s is a valid non-artroot root file.' % filepath)
        if invert:
            return 0
        else:
            return 1

    # File is an artroot file.

    if verbose:
        print('%s is a valid artroot file.' % filepath)
    if invert:
        return 1
    else:
        return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
