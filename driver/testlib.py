# 
# (c) Simon Marlow 2002
#

import sys
import os
import string
import re
import traceback
import copy

from string import join
from testutil import *

# -----------------------------------------------------------------------------
# Configuration info

# There is a single global instance of this structure, stored in the
# variable config below.  The fields of the structure are filled in by
# the appropriate config script(s) for this compiler/platform, in
# ../config.
# 
# Bits of the structure may also be filled in from the command line,
# via the build system, using the '-e' option to runtests.

class TestConfig:
    def __init__(self):

        # Directory below which to look for test description files (foo.T)
        self.rootdir = '.'

        # Run these tests only (run all tests if empty)
        self.only = []

        # Accept new output which differs from the sample?
        self.accept = 0

        # File in which to save the summary
        self.output_summary = ''

        # What platform are we running on?
        self.platform = ''

        # What is the wordsize (in bits) of this platform?
        self.wordsize = ''

        # Verbosity level
        self.verbose = 1

        # Compiler type (ghc, hugs, nhc, etc.)
        self.compiler_type = ''

        # Path to the compiler
        self.compiler = ''

        # Flags we always give to this compiler
        self.compiler_always_flags = []
        
        # Which ways to run tests (when compiling and running respectively)
        # Other ways are added from the command line if we have the appropriate
        # libraries.
        self.compile_ways = []
        self.run_ways     = []

        # Lists of flags for each way
        self.way_flags = {}

global config
config = TestConfig()

def getConfig():
    return config

# -----------------------------------------------------------------------------
# Information about the current test run

class TestRun:
   def __init__(self):
       self.start_time = ''
       self.total_tests = 0
       self.total_test_cases = 0
       self.n_framework_failures = 0
       self.framework_failures = []
       self.n_tests_skipped = 0
       self.tests_skipped = []
       self.n_expected_passes = 0
       self.expected_passes = []
       self.n_expected_failures = 0
       self.expected_failures = []
       self.n_unexpected_passes = 0
       self.unexpected_passes = []
       self.n_unexpected_failures = 0
       self.unexpected_failures = []

global t
t = TestRun()

def getTestRun():
    return t

# -----------------------------------------------------------------------------
# Information about the current test

class TestOptions:
   def __init__(self):

       # skip this test?
       self.skip = 0;

       # skip these ways
       self.omit_ways = []

       # skip all ways except these ([] == do all ways)
       self.only_ways = []
       
       # the result we normally expect for this test
       self.expect = 'pass';

       # override the expected result for certain ways
       self.expect_fail_for = [];

       # the stdin file that this test will use (empty for <name>.stdin)
       self.stdin = ''

       # compile this test to .hc only
       self.compile_to_hc = 0

       # extra compiler opts for this test
       self.extra_hc_opts = ''

       # extra run opts for this test
       self.extra_run_opts = ''

       # expected exit code
       self.exit_code = 0


# The default set of options
global default_testopts
default_testopts = TestOptions()

# Options valid for all the tests in the current "directory".  After
# each test, we reset the options to these.  To change the options for
# multiple tests, the function setTestOpts() below can be used to alter
# these options.
global thisdir_testopts
thisdir_testopts = TestOptions()

def getThisDirTestOpts():
    return thisdir_testopts

# Options valid for the current test only (these get reset to
# testdir_testopts after each test).
global testopts
testopts = TestOptions()

def getTestOpts():
    return testopts

def resetTestOpts():
    global testopts
    testopts = copy.copy(thisdir_testopts)

# This can be called at the top of a file of tests, to set default test options
# for the following tests.
def setTestOpts( f ):
    f( thisdir_testopts );

# -----------------------------------------------------------------------------
# Canned setup functions for common cases.  eg. for a test you might say
#
#      test('test001', normal, compile, [''])
#
# to run it without any options, but change it to
#
#      test('test001', expect_fail, compile, [''])
#
# to expect failure for this test.

def normal( opts ):
    return;

def skip( opts ):
    opts.skip = 1

def expect_fail( opts ):
    opts.expect = 'fail';

# -----

def expect_fail_for( ways ):
    return lambda opts, w=ways: _expect_fail_for( opts, w )

def _expect_fail_for( opts, ways ):
    opts.expect_fail_for = ways

# -----

def omit_ways( ways ):
    return lambda opts, w=ways: _omit_ways( opts, w )

def _omit_ways( opts, ways ):
    opts.omit_ways = ways

# -----

def only_ways( ways ):
    return lambda opts, w=ways: _only_ways( opts, w )

def _only_ways( opts, ways ):
    opts.only_ways = ways

# -----

def expect_fail_if_platform( plat ):
   return lambda opts, p=plat: _expect_fail_if_platform(opts, p)

def _expect_fail_if_platform( opts, plat ):
    if config.platform == plat:
	opts.expect = 'fail'
	
# -----

def set_stdin( file ):
   return lambda opts, f=file: _set_stdin(opts, f);

def _set_stdin( opts, f ):
   opts.stdin = f

# -----

def exit_code( val ):
    return lambda opts, v=val: _exit_code(opts, v);

def _exit_code( opts, v ):
    opts.exit_code = v

# -----

def extra_run_opts( val ):
    return lambda opts, v=val: _extra_run_opts(opts, v);

def _extra_run_opts( opts, v ):
    opts.extra_run_opts = v

# ----
# Function for composing two opt-fns together

def compose( f, g ):
    return lambda opts, f=f, g=g: _compose(opts,f,g)

def _compose( opts, f, g ):    
    f(opts)
    g(opts)

# -----------------------------------------------------------------------------
# The current directory of tests

global testdir
testdir = '.'

def newTestDir( dir ):
    global testdir, thisdir_testopts
    testdir = dir
    # reset the options for this test directory
    thisdir_testopts = copy.copy(default_testopts)

def getTestDir():
    return testdir

# -----------------------------------------------------------------------------
# Actually doing tests

# name  :: String
# setup :: TestOpts -> IO ()  
def test( name, setup, func, args ):
    t.total_tests = t.total_tests + 1

    if func == compile or func == multimod_compile:
        ways = config.compile_ways
    elif func == compile_and_run or func == multimod_compile_and_run:
        ways = config.run_ways
    elif func == ghci_script:
        if 'ghci' in config.run_ways:
            ways = ['ghci']
        else:
            ways = []
    else:
        ways = ['normal']

    for way in ways:
        do_test( name, way, setup, func, args )


def do_test(name, way, setup, func, args):
    full_name = name + '(' + way + ')'
    t.total_test_cases = t.total_test_cases + 1

    try:
        # Reset the test-local options to the options for this "set"
        resetTestOpts()

        # Set our test-local options
        setup(testopts)

        if testopts.skip \
           or (config.only != [] and name not in config.only) \
           or (testopts.only_ways != [] and way not in testopts.only_ways) \
           or way in testopts.omit_ways:
            skiptest(name)
            return

        print '=====>', full_name
        
        result = apply(func, [name,way] + args)
        
        if testopts.expect != 'pass' and testopts.expect != 'fail' or \
           result != 'pass' and result != 'fail':
            framework_fail(full_name)

        if result == 'pass':
            if testopts.expect == 'pass' \
               and way not in testopts.expect_fail_for:
                t.n_expected_passes = t.n_expected_passes + 1
                t.expected_passes.append(full_name)
            else:
                print '*** unexpected pass for', full_name
                t.n_unexpected_passes = t.n_unexpected_passes + 1
                t.unexpected_passes.append(full_name)
        else:
            if testopts.expect == 'pass' \
               and way not in testopts.expect_fail_for:
                print '*** unexpected failure for', full_name
                t.n_unexpected_failures = t.n_unexpected_failures + 1
                t.unexpected_failures.append(full_name)
            else:
                t.n_expected_failures = t.n_expected_failures + 1
                t.expected_failures.append(full_name)

    except:
        print '*** framework failure for', full_name, ':'
        traceback.print_exc()
        framework_fail(full_name)

def skiptest( name ):
    # print 'Skipping test \"', name, '\"'
    t.n_tests_skipped = t.n_tests_skipped + 1
    t.tests_skipped.append(name)

def framework_fail( name ):
    t.n_framework_failures = t.n_framework_failures + 1
    t.framework_failures.append(name)

# -----------------------------------------------------------------------------
# Generic command tests

# A generic command test is expected to run and exit successfully.
#
# The expected exit code can be changed via exit_code() as normal, and
# the expected stdout/stderr are stored in <testname>.stdout and
# <testname>.stderr.  The output of the command can be ignored
# altogether by using run_command_ignore_output instead of
# run_command.

def run_command( name, way, cmd ):
    return simple_run( name, cmd, '', 0 )

def run_command_ignore_output( name, way, cmd ):
    return simple_run( name, cmd, '', 1 )

# -----------------------------------------------------------------------------
# GHCi tests

def ghci_script( name, way, script ):
    # filter out -no-recomp from compiler_always_flags, becuase we're
    # actually testing the recompilation behaviour in the GHCi tests.
    flags = filter(lambda f: f != '-no-recomp', config.compiler_always_flags)

    # We pass HC and HC_OPTS as environment variables, so that the
    # script can invoke the correct compiler by using ':! $HC $HC_OPTS'
    cmd = "HC='" + config.compiler + "' " + \
          "HC_OPTS='" + join(flags,' ') + "' " + \
          "'" + config.compiler + "'" + \
          ' --interactive -v0 ' + \
          join(flags,' ')

    testopts.stdin = script
    return simple_run( name, cmd, '', 0 )

# -----------------------------------------------------------------------------
# Compile-only tests

def compile( name, way, extra_hc_opts ):
    return do_compile( name, way, 0, '', extra_hc_opts )

def compile_fail( name, way, extra_hc_opts ):
    return do_compile( name, way, 1, '', extra_hc_opts )

def multimod_compile( name, way, top_mod, extra_hc_opts ):
    return do_compile( name, way, 0, top_mod, extra_hc_opts )

def multimod_compile_fail( name, way, top_mod, extra_hc_opts ):
    return do_compile( name, way, 1, top_mod, extra_hc_opts )

def do_compile( name, way, should_fail, top_mod, extra_hc_opts ):
    # print 'Compile only, extra args = ', extra_hc_opts
    pretest_cleanup(name)
    result = simple_build( name, way, extra_hc_opts, should_fail, top_mod, 0 )
    
    if should_fail:
        if result == 0:
            return 'fail'
    else:
        if result != 0:
            return 'fail'

    # the actual stderr should always match the expected, regardless
    # of whether we expected the compilation to fail or not (successful
    # compilations may generate warnings).

    expected_stderr_file = platform_wordsize_qualify(name, 'stderr')
    actual_stderr_file = qualify(name, 'comp.stderr')
    actual_stderr = normalise_errmsg(open(actual_stderr_file).read())

    if os.path.exists(expected_stderr_file):
        expected_stderr = normalise_errmsg(open(expected_stderr_file).read())
    else:
        expected_stderr = ''
        expected_stderr_file = ''

    if expected_stderr != actual_stderr:
        # print stderr_e, '\n', stderr_a
        if not outputs_differ('stderr', expected_stderr_file, actual_stderr_file):
            return 'fail'

    # no problems found, this test passed
    return 'pass'

# -----------------------------------------------------------------------------
# Compile-and-run tests

def compile_and_run( name, way, extra_hc_opts ):
    # print 'Compile and run, extra args = ', extra_hc_opts
    pretest_cleanup(name)

    if way == 'ghci': # interpreted...
        return interpreter_run( name, way, extra_hc_opts, 0, '' )
    elif way == 'extcore' or way == 'optextcore' :
        return extcore_run( name, way, extra_hc_opts, 0, '' )
    else: # compiled...
        result = simple_build( name, way, extra_hc_opts, 0, '', 1 )

        if result != 0:
            return 'fail'

        # we don't check the compiler's stderr for a compile-and-run test
        return simple_run( name, './'+name, testopts.extra_run_opts, 0 )


def multimod_compile_and_run( name, way, top_mod, extra_hc_opts ):
    pretest_cleanup(name)

    if way == 'ghci': # interpreted...
        return interpreter_run( name, way, extra_hc_opts, 0, top_mod )
    elif way == 'extcore' or way == 'optextcore' :
        return extcore_run( name, way, extra_hc_opts, 0, top_mod )
    else: # compiled...
        result = simple_build( name, way, extra_hc_opts, 0, top_mod, 1 )

    if result != 0:
        return 'fail'

    # we don't check the compiler's stderr for a compile-and-run test
    return simple_run( name, './'+name, testopts.extra_run_opts, 0 )

# -----------------------------------------------------------------------------
# Build a single-module program

def simple_build( name, way, extra_hc_opts, should_fail, top_mod, link ):
    errname = add_suffix(name, 'comp.stderr')
    rm_no_fail( errname )
    rm_no_fail( name )
    
    if top_mod != '':
        srcname = top_mod
    else:
        srcname = add_suffix(name, 'hs')

    to_do = ''
    if top_mod != '':
        to_do = '--make -o ' + name
    elif link:
        to_do = '-o ' + name
    elif testopts.compile_to_hc:
        to_do = '-C'
    else:
        to_do = '-c' # just compile


    cmd = 'cd ' + testdir + " && '" \
          + config.compiler + "' " \
          + join(config.compiler_always_flags,' ') + ' ' \
          + to_do + ' ' + srcname + ' ' \
          + join(config.way_flags[way],' ') + ' ' \
          + extra_hc_opts + ' ' \
          + testopts.extra_hc_opts + ' ' \
          + '>' + errname + ' 2>&1'

    result = runCmd(cmd)

    if result != 0 and not should_fail:
        actual_stderr = qualify(name, 'comp.stderr')
        if_verbose(1,'Compile failed (status ' + `result` + ') errors were:')
        if_verbose(1,open(actual_stderr).read())

    # ToDo: if the sub-shell was killed by ^C, then exit

    return result

# -----------------------------------------------------------------------------
# Run a program and check its output
#
# If testname.stdin exists, route input from that, else
# from /dev/null.  Route output to testname.run.stdout and 
# testname.run.stderr.  Returns the exit code of the run.

def simple_run( name, prog, args, ignore_output_files ):
   # figure out what to use for stdin
   if testopts.stdin != '':
       use_stdin = testopts.stdin
   else:
       stdin_file = add_suffix(name, 'stdin')
       if os.path.exists(in_testdir(stdin_file)):
           use_stdin = stdin_file
       else:
           use_stdin = '/dev/null'

   run_stdout = add_suffix(name,'run.stdout')
   run_stderr = add_suffix(name,'run.stderr')

   rm_no_fail(qualify(name,'run.stdout'))
   rm_no_fail(qualify(name,'run.stderr'))

   cmd = 'cd ' + testdir + ' && ' \
	  + prog + ' ' + args + ' ' \
          + ' < ' + use_stdin \
          + ' > ' + run_stdout \
          + ' 2> ' + run_stderr

   # run the command
   result = runCmd(cmd)

   exit_code = result >> 8
   signal    = result & 0xff

   # check the exit code
   if exit_code != testopts.exit_code:
       print 'Wrong exit code (expected', testopts.exit_code, ', actual', exit_code, ')'
       return 'fail'

   if ignore_output_files or (check_stdout_ok(name) and check_stderr_ok(name)):
       return 'pass'
   else:
       return 'fail'

# -----------------------------------------------------------------------------
# Run a program in the interpreter and check its output

def interpreter_run( name, way, extra_hc_opts, compile_only, top_mod ):
    outname = add_suffix(name, 'interp.stdout')
    errname = add_suffix(name, 'interp.stderr')
    rm_no_fail(outname)
    rm_no_fail(errname)
    rm_no_fail(name)
    
    if (top_mod == ''):
        srcname = add_suffix(name, 'hs')
    else:
        srcname = top_mod
        
    scriptname = add_suffix(name, 'genscript')
    qscriptname = in_testdir(scriptname)
    rm_no_fail(qscriptname)

    delimiter = '===== program output begins here\n'

    script = open(qscriptname, 'w')
    if not compile_only:
        # set the prog name and command-line args to match the compiled
        # environment.
        script.write(':set prog ' + name + '\n')
        script.write(':set args ' + testopts.extra_run_opts + '\n')
        # Add marker lines to the stdout and stderr output files, so we
        # can separate GHCi's output from the program's.
        script.write(':! echo ' + delimiter)
        script.write(':! echo 1>&2 ' + delimiter)
        # Set stdout to be line-buffered to match the compiled environment.
        script.write('System.IO.hSetBuffering System.IO.stdout System.IO.LineBuffering\n')
        # wrapping in GHC.TopHandler.runIO ensures we get the same output
        # in the event of an exception as for the compiled program.
        script.write('GHC.TopHandler.runIO Main.main\n')
    script.close()

    # figure out what to use for stdin
    if testopts.stdin != '':
        stdin_file = in_testdir(testopts.stdin)
    else:
        stdin_file = qualify(name, 'stdin')

    if os.path.exists(stdin_file):
        stdin = open(stdin_file, 'r')
        os.system('cat ' + stdin_file + ' >>' + qscriptname)
        
    script.close()

    cmd = 'cd ' + testdir + " && '" \
          + config.compiler + "' " \
          + join(config.compiler_always_flags,' ') + ' ' \
          + srcname + ' ' \
          + join(config.way_flags[way],' ') + ' ' \
          + extra_hc_opts + ' ' \
          + testopts.extra_hc_opts + ' ' \
          + '<' + scriptname +  ' 1>' + outname + ' 2>' + errname

    result = runCmd(cmd)

    exit_code = result >> 8
    signal    = result & 0xff

    # check the exit code
    if exit_code != testopts.exit_code:
        print 'Wrong exit code (expected', testopts.exit_code, ', actual', exit_code, ')'
        return 'fail'

    # split the stdout into compilation/program output
    split_file(in_testdir(outname), delimiter,
               qualify(name, 'comp.stdout'),
               qualify(name, 'run.stdout'))
    split_file(in_testdir(errname), delimiter,
               qualify(name, 'comp.stderr'),
               qualify(name, 'run.stderr'))

    # ToDo: if the sub-shell was killed by ^C, then exit

    if check_stdout_ok(name) and check_stderr_ok(name):
        return 'pass'
    else:
        return 'fail'


def split_file(in_fn, delimiter, out1_fn, out2_fn):
    infile = open(in_fn)
    out1 = open(out1_fn, 'w')
    out2 = open(out2_fn, 'w')

    line = infile.readline()
    line = re.sub('\r', '', line) # ignore Windows EOL
    while (re.sub('^\s*','',line) != delimiter and line != ''):
        out1.write(line)
        line = infile.readline()

    line = infile.readline()
    while (line != ''):
        out2.write(line)
        line = infile.readline()
    
# -----------------------------------------------------------------------------
# Generate External Core for the given program, then compile the resulting Core
# and compare its output to the expected output

def extcore_run( name, way, extra_hc_opts, compile_only, top_mod ):
 
    depsfilename = qualify(name, 'deps')
    errname = add_suffix(name, 'comp.stderr')
    qerrname = qualify(errname,'')
    
    hcname = qualify(name, 'hc')
    oname = qualify(name, 'o')
    
    rm_no_fail( qerrname )
    rm_no_fail( qualify(name, '') )

    if (top_mod == ''):
        srcname = add_suffix(name, 'hs')
    else:
        srcname = top_mod

    qcorefilename = qualify(name, 'hcr')
    corefilename = add_suffix(name, 'hcr')
    rm_no_fail(qcorefilename)

    # Generate External Core
    
    if (top_mod == ''):
        to_do = ' ' + srcname + ' '
    else:
        to_do = ' --make ' + top_mod + ' ' 

    cmd = 'cd ' + testdir + " && '" \
          + config.compiler + "' " \
          + join(config.compiler_always_flags,' ') + ' ' \
          + join(config.way_flags[way],' ') + ' ' \
          + extra_hc_opts + ' ' \
          + testopts.extra_hc_opts \
          + to_do \
          + '>' + errname + ' 2>&1'
    result = runCmd(cmd)

    exit_code = result >> 8

    if exit_code != 0:
         if_verbose(1,'Compiling to External Core failed (status ' + `result` + ') errors were:')
         if_verbose(1,open(qerrname).read())
         return 'fail'

     # Compile the resulting files -- if there's more than one module, we need to read the output
     # of the previous compilation in order to find the dependencies
    if (top_mod == ''):
        to_compile = corefilename
    else:
        result = runCmd('grep Compiling ' + qerrname + ' |  awk \'{print $4}\' > ' + depsfilename)
        deps = open(depsfilename).read()
        deplist = string.replace(deps, '\n',' ');
        deplist2 = string.replace(deplist,'.lhs,', '.hcr');
        to_compile = string.replace(deplist2,'.hs,', '.hcr');
        
    flags = join(filter(lambda f: f != '-fext-core',config.way_flags[way]),' ')
    
    cmd = 'cd ' + testdir + " && '" \
          + config.compiler + "' " \
          + join(config.compiler_always_flags,' ') + ' ' \
          + to_compile + ' ' \
          + extra_hc_opts + ' ' \
          + testopts.extra_hc_opts + ' ' \
          + flags                   \
          + ' -fglasgow-exts -o ' + name \
          + '>' + errname + ' 2>&1'
          
    result = runCmd(cmd)
    exit_code = result >> 8

    if exit_code != 0:
        if_verbose(1,'Compiling External Core file(s) failed (status ' + `result` + ') errors were:')
        if_verbose(1,open(qerrname).read())
        return 'fail'

    # Clean up
    rm_no_fail ( oname )
    rm_no_fail ( hcname )
    rm_no_fail ( qcorefilename )
    rm_no_fail ( depsfilename )
    
    return simple_run ( name, './'+name, testopts.extra_run_opts, 0 )

# -----------------------------------------------------------------------------
# Utils

def check_stdout_ok( name ):
   actual_stdout_file   = qualify(name, 'run.stdout')
   expected_stdout_file = platform_wordsize_qualify(name, 'stdout')

   if os.path.exists(expected_stdout_file):
       expected_stdout = open(expected_stdout_file).read()
   else:
       expected_stdout = ''
       expected_stdout_file = ''

   if os.path.exists(actual_stdout_file):
       actual_stdout = open(actual_stdout_file).read()
   else:
       actual_stdout = ''
       actual_stdout_file = ''

   # On Windows, remove '\r' characters from the output
   if config.platform == 'i386-unknown-mingw32':
       actual_stdout = re.sub('\r', '', actual_stdout)
       expected_stdout = re.sub('\r', '', expected_stdout)

   if actual_stdout != expected_stdout:
       return outputs_differ( 'stdout', expected_stdout_file, actual_stdout_file )
   else:
       return 1

def check_stderr_ok( name ):
   actual_stderr_file   = qualify(name, 'run.stderr')
   expected_stderr_file = platform_wordsize_qualify(name, 'stderr')

   if os.path.exists(expected_stderr_file):
       expected_stderr = open(expected_stderr_file).read()
   else:
       expected_stderr = ''
       expected_stderr_file = ''

   if os.path.exists(actual_stderr_file):
       actual_stderr = open(actual_stderr_file).read()
   else:
       actual_stderr = ''
       actual_stderr_file = ''

   # On Windows, remove '\r' characters from the output
   if config.platform == 'i386-unknown-mingw32':
       actual_stderr = re.sub('\r', '', actual_stderr)
       expected_stderr = re.sub('\r', '', expected_stderr)

   if actual_stderr != expected_stderr:
       return outputs_differ( 'stderr', expected_stderr_file, actual_stderr_file )
   else:
       return 1


# Output a message indicating that an expected output differed from the
# actual output, and optionally accept the new output.  Returns true
# if the output was accepted, or false otherwise.
def outputs_differ( kind, expected, actual ):
    print 'Actual ' + kind + ' output differs from expected:'

    if expected == '':
        expected1 = '/dev/null'
    else:
        expected1 = expected
        
    if actual == '':
        actual1 = '/dev/null'
    else:
        actual1 = actual
        
    os.system( 'diff -c ' + expected1 + ' ' + actual1 )

    if config.accept:
        if expected == '':
            print '*** cannot accept new output: ' + kind + \
                  ' file does not exist.'
            return 0
        else:
            print 'Accepting new output.'
            os.system( 'cp ' + actual + ' ' + expected )
            return 1


def normalise_errmsg( str ):
    # Merge contiguous whitespace characters into a single space.
    str = re.sub('[ \t\n]+', ' ', str)
    # Look for file names and zap the directory part:
    #    foo/var/xyzzy/somefile  -->  somefile
    str = re.sub('([^\\s/]+/)*([^\\s/])', '\\2', str)
    # If somefile ends in ".exe" or ".exe:", zap ".exe" (for Windows)
    #    the colon is there because it appears in error messages; this
    #    hacky solution is used in place of more sophisticated filename
    #    mangling
    str = re.sub('([^\\s]+)\\.exe', '\\1', str)
    return str

def if_verbose( n, str ):
    if config.verbose >= n:
        print str

# Guess flags suitable for the compiler.
def guess_compiler_flags():
   if config.compiler_type == 'ghc':
       return ['-no-recomp', '-dcore-lint']
   elif config.compiler_type == 'nhc':
       return ['-an-nhc-specific-flag']
   else:
        return []

def runCmd( cmd ):
    if_verbose( 1, cmd )
    return os.system( cmd )

def runCmdNoFail( cmd ):
    if_verbose( 1, cmd )
    return os.system( cmd )

def rm_no_fail( file ):
   try:
       os.remove( file )    
   finally:
       return

def add_suffix( name, suffix ):
    if suffix == '':
        return name
    else:
        return name + '.' + suffix    

def in_testdir( name ):
    return os.path.join(testdir, name)

def qualify( name, suff ):
    return in_testdir(add_suffix(name, suff))

# "foo" -> qualify("foo-platform") if it exists, otherwise
# try qualify("foo-ws-wordsize") or finally qualify("foo")
def platform_wordsize_qualify( name, suff ):
    path = qualify(name, suff)
    platform_path = path + '-' + config.platform
    wordsize_path = path + '-ws-' + config.wordsize
    if os.path.exists(platform_path):
        return platform_path
    elif os.path.exists(wordsize_path):
        return wordsize_path
    else:
        return path

# Clean up prior to the test, so that we can't spuriously conclude
# that it passed on the basis of old run outputs.
def pretest_cleanup(name):
   rm_no_fail(qualify(name,'comp.stderr'))
   rm_no_fail(qualify(name,'run.stderr'))
   rm_no_fail(qualify(name,'run.stdout'))
   # simple_build zaps the following:
   # rm_nofail(qualify("o"))
   # rm_nofail(qualify(""))
   # not interested in the return code

# -----------------------------------------------------------------------------
# Return a list of all the files ending in '.T' below the directory dir.

def findTFiles(path):
    if os.path.isdir(path):
        paths = map(lambda x, p=path: p + '/' + x, os.listdir(path))
        return concat(map(findTFiles, paths))
    elif path[-2:] == '.T':
        return [path]
    else:
        return []

# -----------------------------------------------------------------------------
# Output a test summary to the specified file object

def summary(t, file):

    file.write('\n')
    file.write('OVERALL SUMMARY for test run started at ' \
               + t.start_time + '\n'\
               + string.rjust(`t.total_tests`, 8) \
               + ' total tests, which gave rise to\n' \
               + string.rjust(`t.total_test_cases`, 8) \
               + ' test cases, of which\n' \
               + string.rjust(`t.n_framework_failures`, 8) \
               + ' caused framework failures\n' \
               + string.rjust(`t.n_tests_skipped`, 8)
               + ' were skipped\n\n' \
               + string.rjust(`t.n_expected_passes`, 8)
               + ' expected passes\n' \
               + string.rjust(`t.n_expected_failures`, 8) \
               + ' expected failures\n' \
               + string.rjust(`t.n_unexpected_passes`, 8) \
               + ' unexpected passes\n'
               + string.rjust(`t.n_unexpected_failures`, 8) \
               + ' unexpected failures\n'
               + '\n')

    if t.n_unexpected_passes > 0:
        file.write('Unexpected passes:\n')
        for test in t.unexpected_passes:
            file.write('   ' + test + '\n')
        file.write('\n')
            
    if t.n_unexpected_failures > 0:
        file.write('Unexpected failures:\n')
        for test in t.unexpected_failures:
            file.write('   ' + test + '\n')
        file.write('\n')
           
 
