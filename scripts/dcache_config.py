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
try:
    import urllib.request as urlrequest
except ImportError:
    import urllib as urlrequest

files_in_transition = None

# Mapping from storage_group.file_family to dCache pool.

poolmap = {'uboone.scratch': 'PublicScratchPools',
           'uboone.persistent': 'UbooneAnalysisPools',
           'uboone.resilient': '',
           'uboone.data_raw': 'UbooneReadWritePools (write)',
           'sbnd.scratch': 'PublicScratchPools',
           'sbnd.persistent': 'SbndAnalysisPools',
           'sbnd.resilient': '',
           'sbnd.raw': 'SbndReadWritePools (write)',
           'icarus.scratch': 'PublicScratchPools',
           'icarus.persistent': 'IcarusAnalysisPools',
           'icarus.resilient': '',
           'icarus.raw': 'IcarusReadWritePools (write)',
           'sbn.scratch': 'PublicScratchPools',
           'sbn.persistent': 'SbnAnalysisPools',
           'sbn.resilient': '',
           'sbn.raw': 'SbnReadWritePools (write)'}


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


# Convert bytes or unicode string to default python str type.
# Works on python 2 and python 3.

def convert_str(s):

    result = ''

    if type(s) == type(''):

        # Already a default str.
        # Just return the original.

        result = s

    elif type(s) == type(u''):

        # Unicode and not str.
        # Convert to bytes.

        result = s.encode()

    elif type(s) == type(b''):

        # Bytes and not str.
        # Convert to unicode.

        result = s.decode()

    else:

        # Last resort, use standard str conversion.

        result = str(s)

    return result


# Print config.

def print_config(config, markdown):

    # Calculate format and header separator line.

    fmt = ''
    headsep = ''
    if markdown:
        fmt = '| %s | %s | %s | %s | %s | %s | %s | %s |'
        headsep = '| --- | --- | --- | --- | --- | --- | --- | --- |'
    else:
        maxlens = []
        for tup in config:
            for i in range(len(tup)):
                while len(maxlens) < len(tup):
                    maxlens.append(0)
                if maxlens[i] < len(tup[i]):
                    maxlens[i] = len(tup[i])
        for maxlen in maxlens:
            fmt += '%%-%ds' % (maxlen+3)

    # Print config data, including header.        

    for tup in config:
        print(fmt % tup)
        if headsep != '':
            print(headsep)
        headsep = ''

    # Done.

    return


# Get dCache tags for a directory.
# Return value is a dictionary of {tag: value}

def get_tags(dir):
    result = {}
    all_tags = ('storage_group', 'file_family', 'file_family_width', 'file_family_wrapper', 'library')
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


def get_pool(experiment, tags):

    # Default pool group is readWritePools.

    tags['pool'] = 'readWritePools'

    if 'file_family' in tags:
        file_family = tags['file_family']
        if file_family != '':
            key = '%s.%s' % (experiment, file_family)
            if key in poolmap:
                tags['pool'] = poolmap[key]
        

# Check SFA status of file family.

def get_sfa(experiment, tags):

    global files_in_transition

    tags['sfa'] = 'No'

    if 'file_family' in tags:
        file_family = tags['file_family']
        if file_family != '':
            if files_in_transition == None:
                files_in_transition = []

                # Download "Files in Transition" web page.

                url = 'https://www-stken.fnal.gov/cgi-bin/enstore_sfa_files_in_transition_cgi.py'
                result = urlrequest.urlopen(url)
                for line in result.readlines():
                    files_in_transition.append(convert_str(line))
            tag = '%s.%s' % (experiment, file_family)
            for line in files_in_transition:
                if line.find(tag) >= 0:
                    tags['sfa'] = 'Yes'


# Analyze directory.

def check_dir(config, experiment, dir, depth, min_depth, max_depth, parent_tags):

    tags = get_tags(dir)
    get_sfa(experiment, tags)
    get_pool(experiment, tags)
    if depth <= min_depth or tags != parent_tags:
        storage_group = tags['storage_group']
        file_family = tags['file_family']
        file_family_width = tags['file_family_width']
        file_family_wrapper = tags['file_family_wrapper']
        library = tags['library']
        sfa = tags['sfa']
        pool = tags['pool']

        # Update config.

        config.append((dir,
                       storage_group,
                       file_family,
                       file_family_width,
                       file_family_wrapper,
                       library,
                       sfa,
                       pool))

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
                check_dir(config, experiment, subpath, depth+1, min_depth, max_depth, tags)
    return


# Main program.

def main(argv):

    # Parse arguments.

    experiment = ''
    min_depth = 3
    max_depth = 7
    markdown = False
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

    config = [('Directory', 'Storage Group', 'File family', 'Width', 'Wrapper',
               'Library', 'SFA', 'Pool')]
    check_dir(config, experiment, rootdir, 2, min_depth, max_depth, {})
    print_config(config, markdown)

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
