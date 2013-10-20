#!/usr/bin/python

import os
import datetime
import subprocess

BACKUPS=[
    # "name": key used in directory name, ie test
    # "src": source directory, ie: /mnt/test/ (with trailing slash)
    # "dest": destination directort, but without the name component, ie: /mnt/backup/
    # "copies": how many copies to keep
    # "rsync_args": arguments to pass to rsync, should include "-a"
    # the above will create -> /mnt/backup/test_21000505000000/

    #{ "name": "test", "src": "/mnt/test/", "dest": "/mnt/backup/", "copies": 15, "rsync_args": "-av" },
]

try:
    # try to import the BACKUPS configuration
    from config import BACKUPS
except ImportError:
    print "config file missing."
    pass


DATEFMT="%Y%m%d%H%M%S" # this must be sortable

def find_old(backup_dict):
    """ Find old directories, to be used in --link-dest.
        Sort by timestamp, get the highest one.
    """

    def mapt(fn):
        # empty last part inserts a separator
        real_fn = os.path.join(backup_dict["dest"], fn, "")

        if not os.path.isdir(real_fn): return None
        if not fn.startswith(backup_dict["name"] + "_"):
            return None

        return real_fn

    lst = os.listdir(backup_dict["dest"])
    olds = filter(lambda x: bool(x), map(mapt, lst))
    olds.sort()

    return olds

def format_name(backup_dict):
    """ Build and return the full path of this backup.
    """

    dest = backup_dict["dest"]
    date = datetime.datetime.now().strftime(DATEFMT)
    name = "%s_%s" % (backup_dict["name"], date)

    # empty last part inserts a separator
    return os.path.join(dest, name, "")

def unlink(target):
    print "erasing:", target
    subprocess.call(["rm", "-fr", target])

def rsync(*kargs):
    args = ["rsync"] + list(kargs)
    print "rsync:", args
    ret = subprocess.call(args)
    print "rsync_out:", ret

    return ret

def do_backup():
    for bkp in BACKUPS:
        oldies = find_old(bkp)
        dest = format_name(bkp)
        os.mkdir(dest)

        # rsync args are either tuple or string
        # make list of strings
        rsync_args = bkp["rsync_args"]
        if isinstance(rsync_args, basestring):
            rsync_args = [rsync_args]
        else:
            rsync_args = list(rsync_args)

        rsync_args.append(bkp["src"])
        # do the backup
        if oldies:
            print "found last directory:", oldies[-1]
            rsync_args.append("--link-dest=%s" % oldies[-1])

        rsync_args.append(dest)
        rsync(*rsync_args)

        # erase old backups
        if bkp.has_key("copies"):
            cn = int(bkp["copies"])
            to_erase = oldies[:-cn]
            for target in to_erase:
                unlink(target)

def do_cleanup():
    for bkp in BACKUPS:
        oldies = find_old(bkp)
        if not oldies: return

        to_erase = oldies[:-1]
        for target in to_erase:
            unlink(target)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cleanup", help="Do not backup anything, but leave only the latest backup.", action="store_true")

    args = parser.parse_args()

    if args.cleanup:
        do_cleanup()
    else:
        do_backup()
