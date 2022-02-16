#! /usr/bin/env python
########################################################################
#
# Name: sbnoms_metadata_extractor.py
#
# Purpose: SAM metadata extractor for artroot and non-artroot files.
#          Use sam_metadata_dumper to extract internal sam metadata from
#          artroot files.  Otherwise, read metadata from associated .json
#          file.  Json format metadata written to standard output.
#
# Usage:
#
# sbnpoms_metadata_extractor.py [options] <file>
#
# Arguments:
#
# <file> - Path of file.
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

import sys, os, subprocess, json, string
import samweb_cli

samweb = None
experiment = ''
registered_data_streams = None

data_stream_conversions = {'outBNB': 'bnb',
                           'outNUMI': 'numi'}

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


# Return true of the argument is a uuid.

def is_uuid(s):
    result = False
    if len(s) == 37:
        result = True
        for i in range(len(s)):
            if i==0 or i==9 or i==14 or i==19 or i==24:
                if s[i] != '-':
                    result = False
                    break
            else:
                if s[i] not in string.hexdigits:
                    result = False
                    break

    # Done.

    return result


# Return matching json file for specified data file (usually root file).
# Return empty string if no matching json file is found.
# This function understands that data files may have been renamed unique
# by "ifdh renameOutput".  

def matching_json_file(data_file):
    result = ''
    data_path = os.path.abspath(data_file)
    dir = os.path.dirname(data_path)
    fname = os.path.basename(data_path)

    # fname_noext is the root file name without directory and extension.

    fname_noext = os.path.splitext(fname)[0]

    # fname_trunc is the same as fname_noext minus a potential uuid that might
    # have been added by ifdh renameOutput.
    # A uuid has 37 characters following pattern "-hex(8)-hex(4)-hex(4)-hex(4)-hex(12)"

    fname_trunc = fname_noext
    if len(fname_noext) > 37:
        uuid = fname_noext[-37:]
        if is_uuid(uuid):
            fname_trunc = fname_noext[:-37]

    # Hunt for matching json files.

    for f in os.listdir(dir):
        if f.endswith('.json'):
            f_noext = os.path.splitext(f[:-5])[0]
            if f_noext == fname_noext or f_noext == fname_trunc:
                result = os.path.join(dir, f)
                break

    # Done.

    return result


# Check the validity of a single parent.
# Return value is a guaranteed valid list of parents (may be empty list)
# Fcl list also updated to include fcls associated with virtual parents.
# Update mc event_count if a parent file contains parameter 
# mc.generated_event_count.

def check_parent(parentarg, dir, fcllist, mc_event_count):

    result = []

    # Parent arg can be passed in different ways depending on the source.

    parent = ''
    if type(parentarg) == type(''):
        parent = parentarg
    elif type(parentarg) == type(b''):
        parent = parentarg.decode('utf8')
    elif type(parentarg) == type({}):
        if 'file_name' in parentarg:
            parent = parentarg['file_name']
        elif 'file_id' in parentarg:
            parent = parentarg['file_id']
    if parent == '' or type(parent) != type(''):
        raise FileNotFoundError


    # Check whether this parent file has metadata already.

    samweb = get_samweb()
    has_metadata = False
    mdparent = {}
    try:
        mdparent = samweb.getMetadata(parent)
        has_metadata = True
    except samweb_cli.FileNotFound:
        has_metadata = False

    if has_metadata:

        # If this parent has metadata, return this one file in the form of a list.
        # Don't add anything to fcl list.

        result = [parent]

        # Maybe update mc event_count.

        if 'mc.generated_event_count' in mdparent:
            mc_event_count[0] = mdparent['mc.generated_event_count']
        elif (not 'parents' in mdparent or len(mdparent['parents']) == 0) and 'event_count' in mdparent:
            mc_event_count[0]  = mdparent['event_count']

    else:

        # If this parent doesn't have metadata, try to locate file.

        local_file = os.path.join(dir, parent)
        if os.path.exists(local_file) or matching_json_file(local_file) != '':

            # Found local file.  Extract parent information from file.

            md = get_metadata(local_file)

            if 'parents' in md:
                for prnt in md['parents']:
                    result.extend(check_parent(prnt, dir, fcllist, mc_event_count))

            # Append fcl file to front of fcl list.

            if 'fcl.name' in md and not md['fcl.name'] in fcllist:
                fcllist.insert(1, md['fcl.name'])

            # Maybe update mc event_count.

            if 'mc.generated_event_count' in md:
                mc_event_count[0] = md['mc.generated_event_count']
            elif (not 'parents' in md or len(md['parents']) == 0) and 'event_count' in md:
                mc_event_count[0] = md['event_count']

        else:

            # Couldn't find file.  Raise exception.

            print('Couldn\'t find file %s' % local_file)
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
#
# 4.  If no parents, set parameter mc.generated_event_count equal to 
#     event_count.

def validate_parents(md, dir):
    if 'parents' in md and len(md['parents']) > 0:

        # Metadata contains a nonempty list of parents.

        parents = md['parents']
        new_parents = []
        fcllist = []
        mc_event_count = [-1]
        for parent in parents:
            new_parents.extend(check_parent(parent, dir, fcllist, mc_event_count))
        if len(new_parents) == 0:

            # If updated parent list is empty, delete 'parents' from metadata.

            del md['parents']

        else:

            # Insert updated parent list into metadata.

            md['parents'] = new_parents

        # Maybe update fcl.name parameter.

        if len(fcllist) > 0:
            if 'fcl.name' in md and not md['fcl.name'] in fcllist:
                fcllist.append(md['fcl.name'])
            md['fcl.name'] = '/'.join(fcllist)

        # Maybe update mc event_count.

        if mc_event_count[0] >= 0:
            md['mc.generated_event_count'] = mc_event_count[0]

    else:

        # Metadata parents is missing or empty.
        # if mc event_count is missing, treat this as a generator job.

        if not 'mc.generated_event_count' in md and 'event_count' in md:
            md['mc.generated_event_count'] = md['event_count']

    # Done.

    return


# Validate ane maybe update data_stream metadata.

def validate_data_stream(md):

    global registered_data_streams
    global data_stream_conversions

    # Don't do anything if metadata doesn't include data_stream.

    if 'data_stream' in md:
        data_stream = md['data_stream']

        # Make sure registered data streams are initialized.

        if registered_data_streams == None:
            samweb = get_samweb()
            registered_data_streams = samweb.listValues('data_streams')

        # Check whether this data_stream is registered.

        if not data_stream in registered_data_streams:

            # Metadata has an unregistered data stream.
            # Look for a conversion,

            if data_stream in data_stream_conversions:
                new_data_stream = data_stream_conversions[data_stream]
                data_stream = new_data_stream
                md['data_stream'] = new_data_stream

    # Done.

    return


# Function to extract metadata as python dictionary.

def get_metadata(artroot):

    # Run sam_metadata_dumper.

    md = {}
    cmd = ['sam_metadata_dumper', artroot]
    proc = subprocess.run(cmd, capture_output=True, encoding='utf8')
    if proc.returncode == 0:

        # Sam_metadata_dumper succeeded.
        # Parse json output into python dictionary.

        md0 = json.loads(proc.stdout)

        # Loop over one key to extract file name.

        for k in md0:
            md = md0[k]
            md['file_name'] = k
            break

    else:

        # Sam_metadata_dumper failed.
        # Try to read metadata for corrsponding json file.

        jsonfile = matching_json_file(artroot)
        if jsonfile != '':
            f = open(jsonfile)
            md = json.load(f)
        else:
            print('sam_metadata_dumper returned status %d' % proc.returncode)
            print('No corresponding json file found, giving up.')
            sys.exit(proc.returncode)

    # Do metadata checks and updates here.
    # Make sure metadata contains file name.
    # Preexisting file_name in metadata, if any, is ignored.

    md['file_name'] = os.path.basename(artroot)
            
    # Make sure metadata contains file size, if we have access to the original file.
    # Preexisting file_size in metadata, if any, is ignored.

    if os.path.exists(artroot):
        stat = os.stat(artroot)
        md['file_size'] = stat.st_size

    # Make sure application family/name/version is its own dictionary

    if not 'application' in md:
        md['application'] = {}
        if 'application.family' in md:
            md['application']['family'] = md['application.family']
            del md['application.family']
        if 'art.process_name' in md:
            md['application']['name'] = md['art.process_name']
        if 'application.version' in md:
            md['application']['version'] = md['application.version']
            del md['application.version']

    # Handle first/last event.

    if 'art.first_event' in md:
        md['first_event'] = md['art.first_event'][2]
        del md['art.first_event']
    if 'art.last_event' in md:
        md['last_event'] = md['art.last_event'][2]
        del md['art.last_event']

    # Handle data_stream.

    validate_data_stream(md)

    # Ignore 'art.run_type' (run_type is also contained in 'runs' metadata).

    if 'art.run_type' in md:
        del md['art.run_type']

    # Done.

    return md


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

    if not os.path.exists(artroot) and matching_json_file(artroot) == '':
        print('Artroot file %s does not exist and there is no corresponding json file.' % artroot)
        sys.exit(1)

    # Extract metadata as python dictionary.

    md = get_metadata(artroot)

    # Validate parent metadata.

    dir = os.path.dirname(os.path.abspath(artroot))
    validate_parents(md, dir)

    # Pretty print json metadata.

    json.dump(md, sys.stdout, sort_keys=True, indent=2)
    print()   # Json dump misses final newline.

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
