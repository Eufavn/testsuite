# 
# (c) Simon Marlow 2002
#

# ToDo:
#   GHCi tests
#   expect failure for some ways only

import sys
import os
import string
import getopt
import threading

from testlib import *

global config
config = getConfig() # get it from testlib

global testopts_local
testopts_local.x = TestOptions()

global thisdir_testopts
thisdir_testopts = getThisDirTestOpts()

# -----------------------------------------------------------------------------
# cmd-line options

long_options = [
  "config=",  		# config file
  "rootdir=", 		# root of tree containing tests (default: .)
  "output-summary=", 	# file in which to save the (human-readable) summary
  "only=",		# just this test (can be give multiple --only= flags)
  "way=",		# just this way
  "threads=",           # threads to run simultaneously
  ]

opts, args = getopt.getopt(sys.argv[1:], "e:", long_options)
       
for opt,arg in opts:
    if opt == '--config':
        execfile(arg)

    # -e is a string to execute from the command line.  For example:
    # testframe -e 'config.compiler=ghc-5.04'
    if opt == '-e':
        exec arg

    if opt == '--rootdir':
        config.rootdir = arg

    if opt == '--output-summary':
        config.output_summary = arg

    if opt == '--only':
        config.only.append(arg)

    if opt == '--way':
        if (arg not in config.run_ways and arg not in config.compile_ways and arg not in config.other_ways):
            sys.stderr.write("ERROR: requested way \'" +
                             arg + "\' does not exist\n")
            sys.exit(1)
        config.run_ways = filter(eq(arg), config.run_ways + config.other_ways)
        config.compile_ways = filter(eq(arg), config.compile_ways + config.other_ways)

    if opt == '--threads':
        config.threads = int(arg)
# -----------------------------------------------------------------------------
# The main dude

t_files = findTFiles(config.rootdir)

print 'Found', len(t_files), '.T files...'

t = getTestRun()

t.start_time = chop(os.popen('date').read())
print 'Beginning test run at', t.start_time

# set stdout to unbuffered (is this the best way to do it?)
sys.stdout.flush()
sys.stdout = os.fdopen(sys.__stdout__.fileno(), "w", 0)

for file in t_files:
    print '====> Running', file
    newTestDir(os.path.dirname(file))
    try:
        t.running_threads=0
        execfile(file)
        t.thread_pool.acquire()
        while t.running_threads>0:
            t.thread_pool.wait()
        t.thread_pool.release()
    except:
        print '*** found an error while executing ', file, ':'
        traceback.print_exc()
        
summary(t, sys.stdout)

if config.output_summary != '':
    summary(t, open(config.output_summary, 'w'))

sys.exit(0)

