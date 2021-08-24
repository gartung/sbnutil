#! /usr/bin/env python
########################################################################
#
# Name: migrate_sam_users.py
#
# Purpose: Migrate users and groups from source SAM database (SBND or
#          ICARUS) to target SAM database (SBN).
#
# Usage:
#
# migrate_sam_users.py [options]
#
# Options:
#
# -h|--help             - Print help.
# -e|--experiment <exp> - Experiment (default $SAM_EXPERIMENT).
# -u|--user <user>      - Check particular user (default all).
#
# Usage notes:
#
# 1.  This script queries all users from source and target database
#     and adds missing users in the target database.
#
# 2.  Group membership, and grid subjects are checked for each user.
#     Groups and grid subjects will generallly be the union of groups
#     and grid subjects from all source databases.
#
# 3.  Status (active/inactive) is not checked.
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

nsource_users = 0
ntarget_users = 0
nusers_added = 0
nusers_updated = 0

# Help function.

def help():

    filename = sys.argv[0]
    file = open(filename, 'r')

    doprint=0
    
    for line in file.readlines():
        if line[2:22] == 'migrate_sam_users.py':
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

    global nsource_users
    global ntarget_users
    global nusers_added
    global nusers_updated

    # Parse arguments.

    experiment = ''
    user = ''
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
        elif (args[0] == '-u' or args[0] == '--user') and len(args) > 1:
            user = args[1]
            del args[0:2]
        else:
            print('Unknown option %s' % args[0])
            sys.exit(1)

    # Initialize samweb.

    samweb1 = samweb_cli.SAMWebClient(experiment=experiment)
    samweb2 = samweb_cli.SAMWebClient(experiment='sbn')

    # Add missing users.

    users1 = set()
    if user == '':
        users1 = set(samweb1.listUsers())
    else:
        users1.add(user)
    users2 = set(samweb2.listUsers())
    usersd = users1 - users2

    nsource_users = len(users1)
    ntarget_users = len(users2)

    print('%d users in source database.' % len(users1))
    print('%d users in target database.'% len(users2))
    print('%d users missing in target datagase.' % len(usersd))

    # Add missing users.

    print('\nChecking users.')
    for user in usersd:
        print('Adding user %s' % user)
        userdict = samweb1.describeUser(user)
        firstname = userdict['first_name']
        lastname = userdict['last_name']
        email = userdict['email']
        samweb2.addUser(user, firstname=firstname, lastname=lastname, email=email)
        nusers_added += 1
        ntarget_users += 1

    # Loop over all users from source database and check groups and grid subjects.

    print('\nChecking groups and grid subjects.')
    for user in users1:
        #print('Checking groups for user %s' % user)
        userdict1 = samweb1.describeUser(user)
        userdict2 = samweb2.describeUser(user)

        # Check groups.

        groups1 = userdict1['groups']
        groups2 = userdict2['groups']
        #print(groups1)
        #print(groups2)
        add_groups = []
        for group in groups1:
            if not group in groups2:
                print('Adding group %s for user %s' % (group, user))
                update_group = True
                add_groups.append(group)
        #print(groups2)
        if len(add_groups) > 0:
            print('Updating groups for user %s' % user)
            samweb2.modifyUser(user, addgroups=add_groups)

        # Check grid subjects.

        grids1 = userdict1['grid_subjects']
        grids2 = userdict2['grid_subjects']
        #print(grids1)
        #print(grids2)
        update_grid = False
        for grid in grids1:
            if not grid in grids2:
                print('Adding grid subject %s for user %s' % (grid, user))
                try:
                    samweb2.modifyUser(user, addgridsubject=grid)
                    update_grid = True
                except:
                    print('Failed to update grid subject %s for user %s' % (grid, user))

        if len(add_groups) > 0 or update_grid:
            nusers_updated += 1

    # Print statistical summary.

    print('\n%d users in source database.' % nsource_users)
    print('%d users added in target database.' % nusers_added)
    print('%d users updated in target database.' % nusers_updated)
    print('%d users in target database.' % ntarget_users)

    # Done

    return 0

# Invoke main program.

if __name__ == "__main__":
    sys.exit(main(sys.argv))
