#! /usr/bin/env python
########################################################################
#
# Name: dcache_config.py
#
# Purpose: Analysis dCache configuraiton.
#
# Usage:
#
# dcache_config.py [options]
#
# Options:
#
# -h|--help       - Print help.
# -e|--experiment - Experiment (default $EXPERIMENT).
# --min_depth <n> - Minimum depth to print out (default 3).
# --max_deptn <n> - Maximum depth to analyze (default 7).
# --md            - Output in markdown format (default plain text).
#
########################################################################
#
# Created: 21-Jun-2021  H. Greenlee
#
########################################################################

from __future__ import print_function
import sys, os

markdown = False

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line[2:18] == 'dcache_config.py':
            doprint = 1
        elif line[0:6] == '######' and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


# Get dCache tags for a directory.
# Return value is a dictionary of {tag: value}

def get_tags(dir):
    result = {}
    all_tags = ('file_family', 'file_family_width', 'file_family_wrapper', 'library')
    for tag in all_tags:
        result[tag] = ''
    ftags = os.path.join(dir, '.(tags)()')
    for line in open(ftags):
        n = line.rfind('(')
        l = line.rfind(')')
        tag = line[n+1:l]
        if tag in all_tags:
            ftag = os.path.join(dir, '.(tag)(%s)' % tag)
            value = open(ftag).readlines()[0].strip()
            result[tag] = value
    return result
        


# Analyze directory.

def check_dir(dir, depth, min_depth, max_depth, parent_tags):
    tags = get_tags(dir)
    if depth <= min_depth or tags != parent_tags:
        file_family = tags['file_family']
        file_family_width = tags['file_family_width']
        file_family_wrapper = tags['file_family_wrapper']
        library = tags['library']
        if markdown:
            print('| %s | %s | %s | %s | %s |' % (dir,
                                                  file_family,
                                                  file_family_width,
                                                  file_family_wrapper,
                                                  library))
        else:
            print('%-55s   %-27s   %-8s   %-11s   %-10s' % (dir,
                                                            file_family,
                                                            file_family_width,
                                                            file_family_wrapper,
                                                            library))
        #print(parent_tags)
        #print(tags)
    descend = True
    if depth >= max_depth:
        descend = False
    if descend and os.path.basename(dir) == 'users':
        descend = False
    if descend and os.path.basename(dir) == 'scratch':
        descend = False
    if descend and os.path.basename(dir) == 'persistent':
        descend = False
    if descend and os.path.basename(dir) == 'resilient':
        descend = False
    if descend:
        contents = []
        try:
            contents = os.listdir(dir)
        except:
            contents = []
        for ele in contents:
            subpath = os.path.join(dir, ele)
            if os.path.isdir(subpath) and not ele.startswith('.Trash'):
                check_dir(subpath, depth+1, min_depth, max_depth, tags)
    return


# Main program.

def main(argv):

    # Parse arguments.

    global markdown
    experiment = ''
    min_depth = 3
    max_depth = 7
    if 'EXPERIMENT' in os.environ:
        experiment = os.environ['EXPERIMENT']

    args = argv[1:]
    while len(args) > 0:
        if args[0] == '-h' or args[0] == '--help' :
            help()
            return 0
        elif (args[0] == '-e' or args[0] == '--experiment') and len(args) > 1:
            experiment = args[1]
            del args[0:2]
        elif (args[0] == '--min_depth') and len(args) > 1:
            min_depth = int(args[1])
            del args[0:2]
        elif (args[0] == '--max_depth') and len(args) > 1:
            max_depth = int(args[1])
            del args[0:2]
        elif args[0] == '--md':
            markdown = True
            del args[0]
        else:
            print('Unknown option %s' % args[0])
            sys.exit(1)

    rootdir = '/pnfs/%s' % experiment
    if not os.path.exists(rootdir):
        print('Directory %s does not exist.' % rootdir)
        sys.exit(1)

    if max_depth < min_depth:
        max_depth = min_depth

    # Done parsing.

    if markdown:        
        print('| %s | %s | %s | %s | %s |' % ('Directory',
                                              'File family',
                                              'Width',
                                              'Wrapper',
                                              'Library'))
        print('| --- | --- | --- | --- | --- |')
    else:
        print('%-55s   %-27s   %-8s   %-11s   %-10s' % ('Directory',
                                                        'File family',
                                                        'Width',
                                                        'Wrapper',
                                                        'Library'))
    check_dir(rootdir, 2, min_depth, max_depth, {})

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
