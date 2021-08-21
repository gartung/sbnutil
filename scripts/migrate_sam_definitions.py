#! /usr/bin/env python
########################################################################
#
# Name: migrate_sam_definitions.py
#
# Purpose: Migrate dataset definitions from source SAM database (SBND or 
#          ICARUS) to target SAM database (SBN).
#
# Usage:
#
# migrate_sam_definitions.py [options]
#
# Options:
#
# -h|--help             - Print help.
# -e|--experiment <exp> - Experiment (default $SAM_EXPERIMENT).
# -d|--definition <def> - Migrate a particular definition (default none).
# -n|--ndefinitions<n>  - Number of defiitions migrate (default no limit).
#
# Usage notes:
#
#
# 1.  This script queries all definitions from source and target database.
#     Definitions that exist in source database, but not in target database
#     are candidates for migration.
#
# 2.  This script assumes that any definition that exists in both databases
#     does not need to be migrated.  That is, existing definitions are not
#     checked, or in other words, this script does not handle the case of
#     modified definitions.
#
# 3.  If some particular definition is specified via option -d|--definition,
#     this definition will only be migrated if it does not already exist in the
#     target database (same as if no definition is specified).
#     
#
########################################################################
#
# Created: 20-Aug-2021  H. Greenlee
#
########################################################################

from __future__ import print_function
import sys, os
import samweb_cli

# Statistics.

nsource = 0
ntarget = 0
nadded = 0
nskipped = 0

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line[2:28] == 'migrate_sam_definitions.py':
            doprint = 1
        elif (line.startswith('######') or line.startswith('# Usage notes:')) and doprint:
            doprint = 0
        if doprint:
            if len(line) > 2:
                print(line[2:], end='')
            else:
                print()


# Print definition

def print_definition(defdict):
    for key in defdict:
        print('%s: %s' % (key, defdict[key]))
    return


# Extract dependent definitions (defname: clause) from dimension string.

def extract_definitions(dim):

    result = []
    start = 0

    # Make sure ':', ')', and '(' are separated by spaces.

    dim.replace(':', ': ')
    dim.replace(')', ' ) ')
    dim.replace('(', ' ( ')

    # Make sure there are no spaces in front of ':'

    while dim.find(' :') >= 0:
        dim.replace(' :', ':')

    while start >= 0 and start < len(dim):

        # Search for "defname:"

        n = dim[start:].find('defname:')
        if n >= 0:

            # Get first word following defname:

            subdef = dim[start+8:].split()[0]
            result.append(subdef)
            start += 8

        else:

            # No more defname:'s

            start = -1

    # Done.

    return result


# Check definition.
# Returns True/False depending on whether definition was successfully migrated.

def check_definition(samweb1, samweb2, defn):

    global nsource
    global ntarget
    global nadded
    global nskipped

    # Default result (failure).

    result = False

    # Get definition from source database (failure if doesn't exist).

    print('Checking definition %s' % defn)
    defok = False
    try:
        defdict = samweb1.descDefinitionDict(defn)
        defok = True
    except:
        defok = False
    if not defok:
        return False

    # Check whether definition alrady exists in target database.
    # If it exists, return success without any further checking.

    exists = False
    try:
        defdict2 = samweb2.descDefinition(defn)
        exists = True
    except:
        exists = False
    if exists:
        print('Defintion %s already exists in target database.' % defn)
        return True

    # Migrate definition.

    #print_definition(defdict)
    defname = defdict['defname']
    dim = defdict['dimensions']
    user = None
    group = None
    desc = None
    if 'username' in defdict:
        user = defdict['username']
    if 'group' in defdict:
        group = defdict['group']
    if 'description' in defdict:
        desc = defdict['description']

    # Check whether this definition contains any non-migratable dimensions.

    ids = ('consumer_process_id',
           'consumed_status',
           'dataset_def_id',
           'file_id',
           'project_id',
           'project_name',
           'dataset_def_name',
           'dataset_def_id',
           'dataset_def_name_newest_snapshot',
           'def_snapshot',
           'snapshot_id',
           'snapshot_file_number',
           'snapshot_for_project_id',
           'snapshot_for_project_name',
           'snapshot_version')
    dim_ok = True
    for id in ids:
        if dim.find(id) >= 0:
            dim_ok = False
            print('Skipping definition %s because it contains %s' % (defn, id))
            nskipped += 1
            break

    # Check embedded definitions.

    if dim_ok:
        subdefs = extract_definitions(dim)
        for subdef in subdefs:
            dim_ok = check_definition(samweb1, samweb2, subdef)
            if not dim_ok:
                break

    # Create definition.

    if dim_ok:
        print('Adding definition %s' % defname)
        samweb2.createDefinition(defname, dim, user=user, group=group, description=desc)
        result = True
        nadded += 1
        ntarget += 1

    # Done.

    return result


# Main procedure.

def main(argv):

    global nsource
    global ntarget
    global nadded
    global nskipped

    # Parse arguments.

    experiment = ''
    ndefs = 0
    specific_def = ''
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
        elif (args[0] == '-n' or args[0] == '--ndefinitions') and len(args) > 1:
            ndefs = int(args[1])
            del args[0:2]
        elif (args[0] == '-d' or args[0] == '--definition') and len(args) > 1:
            specific_def = args[1]
            del args[0:2]
        else:
            print('Unknown option %s' % args[0])
            sys.exit(1)

    # Initialize samweb.

    samweb1 = samweb_cli.SAMWebClient(experiment=experiment)
    samweb2 = samweb_cli.SAMWebClient(experiment='sbn')

    # Get definitions.

    if specific_def != '':
        defs1 = set([specific_def])
    else:
        defs1 = set(samweb1.listDefinitions())
    defs2 = set(samweb2.listDefinitions())

    # Calculate definitinos that need to be migrated (set difference).

    defsd = defs1 - defs2

    nsource = len(defs1)
    ntarget = len(defs2)

    print('%d definitions in source database.' % len(defs1))
    print('%d definitions in target database.' % len(defs2))
    print('%d definitions needing to be migrated.\n' % len(defsd))


    # Loop over definitions that need to be migrated.

    for defn in defsd:
        check_definition(samweb1, samweb2, defn)
        if ndefs > 0 and nadded >= ndefs:
            break


    # Print statistical summary.

    print('\n%d definitions in source database.' % nsource)
    print('%d definitions migrated.' % nadded)
    print('%d definitions skipped.' % nskipped)
    print('%d definitions in target database.' % ntarget)

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
