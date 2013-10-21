#!/usr/bin/python

import os
import sys
import datetime
import subprocess
import ConfigParser

EXAMPLE_CONF = """
# name used to format the output directory, ie dest/<name>_timestamp/
# this example section will create incremental backups like: /mnt/backup/auto/example_21000505000000/
[example]

# source directory (should include trailing slash)
src         = /mnt/test/

# destination directory, but without the name component
dest        = /mnt/backup/auto/

# number of copies to keep
copies      = 15

# "rsync_args": comma-separated arguments to pass to rsync, should include "-a"
rsync_args  = -av,--exclude=torrents/
"""

def read_config(options):
    fn = "/etc/rsync-incremental.conf"
    config = ConfigParser.ConfigParser()
    config.read(fn)

    if not len(config.sections()):
        print "Configuration missing:", fn
        sys.exit(-1)

    backups = []
    for section in config.sections():
        backup = {
            'name': section,
            'src': config.get(section, 'src'),
            'dest': config.get(section, 'dest'),
            'copies': config.getint(section, 'copies'),
            'rsync_args': config.get(section, 'rsync_args').split(","),
        }
        backups.append(backup)

    options.backups = backups
    options.date_fmt = "%Y%m%d_%H%M%S" # this must be sortable

def system(args, opts):
    print args

    if opts.dry_run:
        return 0

    #args = ["echo"] + args
    return subprocess.call(args)

def find_old(dest_dir, name):
    """ Find old directories, to be used in --link-dest.
        Sort by timestamp, get the highest one.
    """

    def mapt(fn):
        # empty last part inserts a separator
        real_fn = os.path.join(dest_dir, fn, "")

        if not os.path.isdir(real_fn): return None
        if not fn.startswith(name + "_"):
            return None

        return real_fn

    lst = os.listdir(dest_dir)
    olds = filter(lambda x: bool(x), map(mapt, lst))
    olds.sort()

    return olds

def find_tmp(dest_dir, name):
    """ Find temporary directories, left due to unfinished backup.
    """

    def mapt(fn):
        real_fn = os.path.join(dest_dir, fn, "")
        if not os.path.isdir(real_fn): return None
        if not fn.startswith(".tmp." + name + "_"):
            return None

        return real_fn

    lst = os.listdir(dest_dir)
    return  filter(lambda x: bool(x), map(mapt, lst))

def format_dest(dest_dir, name, options):
    """ Build and return the full path of this backup.
        Outputs two paths: one is the final destination, second - temporary location.
    """

    date = datetime.datetime.now().strftime(options.date_fmt)
    name = "%s_%s" % (name, date)

    # empty last part inserts a separator
    final = os.path.join(dest_dir, name, "")
    tmp = os.path.join(dest_dir, ".tmp." + name, "")
    return final, tmp

def do_backup(options):
    for bkp in options.backups:
        b_name, b_src, b_dest = bkp["name"], bkp["src"], bkp["dest"]
        b_copies, b_rsync_args = bkp["copies"], bkp["rsync_args"]

        # check source
        if not os.path.isdir(b_src):
            print "skipping missing directory:", b_src
            continue

        if not len(os.listdir(b_src)):
            print "skipping empty directory:", b_src
            continue

        oldies = find_old(b_dest, b_name)
        dest_final, dest_tmp = format_dest(b_dest, b_name, options)
        system(["mkdir", dest_tmp], options)

        # rsync args are either tuple or string
        # make list of strings
        rsync_args = ["rsync"]
        if isinstance(bkp["rsync_args"], basestring):
            rsync_args.append(bkp["rsync_args"])
        else:
            rsync_args += bkp["rsync_args"]

        rsync_args.append(b_src)
        # do the backup
        if oldies:
            rsync_args.append("--link-dest=%s" % oldies[-1])

        rsync_args.append(dest_tmp)

        # now execute
        system(rsync_args, options)

        # now rename it into the final name
        # this is necessary, so empty backups are not created (in case of ctrl+c)
        system(["mv", dest_tmp, dest_final], options)

def do_cleanup(options):
    for bkp in options.backups:
        b_name, b_src, b_dest = bkp["name"], bkp["src"], bkp["dest"]
        b_copies, b_rsync_args = bkp["copies"], bkp["rsync_args"]

        tmps = find_tmp(b_dest, b_name)
        oldies = find_old(b_dest, b_name)
        if not oldies and not tmps: return

        if options.cleanup:
            cn = 1
        else:
            cn = int(bkp["copies"])

        to_erase = tmps + oldies[:-cn]
        for target in to_erase:
            system(["rm", "-fr", target], options)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Make incremental backups for entries in /etc/rsync-incremental.conf.")
    parser.add_argument("-l", "--cleanup", help="do not backup anything, but leave only the latest backup", action="store_true")
    parser.add_argument("-n", "--dry-run", help="do not do anything, just output the shell commands", action="store_true")
    parser.add_argument("-e", "--example", help="output example configuration file and quit", action="store_true")

    # add options and config file
    options = parser.parse_args()
    read_config(options)

    if options.example:
        print EXAMPLE_CONF
        sys.exit(0)
    elif options.cleanup:
        do_cleanup(options)
    else:
        do_backup(options)
        do_cleanup(options)
