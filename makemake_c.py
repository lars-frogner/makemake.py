#!/usr/bin/env python
#
# This program takes a list of C files from the command line, 
# and generates a makefile for building the corresponding executable.
#
# State: WIP
#
# Last modified 14.01.2017 by Lars Frogner
#
import sys, os

std_headers = ['ctype.h', 'stdio.h', 'math.h', 'stdlib.h', 'string.h', 'time.h', 'stdarg.h']

class Source:

    # This class parses an inputted .c file and stores information
    # about which functions and dependencies it contains.

    def __init__(self, path, filename):

        filename_with_path = filename

        file_path = '/'.join(filename_with_path.split('/')[:-1])
        has_abs_path = len(file_path.strip()) > 0

        self.filename = filename_with_path.split('/')[-1]

        name_parts = self.filename.split('.')

        self.use_mpi = False
        self.use_openmp = False

        self.name = '.'.join(name_parts[:-1])
        self.object_name = self.name + '.o'
        self.is_header = name_parts[-1] == 'h'
        self.is_main = False

        # -- Validate filename
        if name_parts[-1] != 'c' and name_parts[-1] != 'h':

            print '(makemake_c.py) Invalid file extension for \"%s\".' % filename_with_path \
                  + ' Must be \".c\" or \".h\".'
            sys.exit(1)

        try:
            if has_abs_path:
                print os.path.join(file_path, self.filename)
                f = open(os.path.join(file_path, self.filename), 'r')
            else:
                f = open(os.path.join(path, self.filename), 'r')

        except IOError:

            print '(makemake_c.py) Couldn\'t open file \"%s\".' % filename_with_path
            sys.exit(1)
        # --

        text = f.read()
        f.close()

        lines = text.split('\n')

        for i in xrange(len(lines)):

            words = lines[i].split()

            for j in xrange(len(words)-1):

                if words[j] == '#include' and '"' in words[j+1]:

                    words[j+1] = '<' + words[j+1][1:-1] + '>'

            lines[i] = ' '.join(words)

        text = '\n'.join(lines)
        
        clean_text = [text[0]]

        in_comm = False
        in_block_comm = False
        in_str = False

        for i in xrange(1, len(text)):

            add_now = True

            if text[i] == '"' and not in_comm and not in_block_comm:

                if in_str:

                    in_str = False
                    add_now = False
                
                else:
                    in_str = True

            if text[i-1] == '/' and text[i] == '/' and not in_str and not in_block_comm and not in_comm:

                in_comm = True
                clean_text = clean_text[:-1]

            if text[i] == '\n' and in_comm:

                in_comm = False

            if text[i-1] == '/' and text[i] == '*' and not in_str and not in_block_comm and not in_comm:

                in_block_comm = True
                clean_text = clean_text[:-1]

            if text[i-1] == '*' and text[i] == '/' and in_block_comm:

                in_block_comm = False
                add_now = False

            if not in_comm and not in_block_comm and not in_str and add_now:

                clean_text.append(text[i])

        text = ''.join(clean_text)

        lines = text.split('\n')

        self.header_deps = []

        # Parse source file
        for line in lines:

            words = line.split()

            # Skip blank lines
            if len(words) == 0: continue

            n_words = len(words)

            first_word = words[0]
            second_word = '' if n_words < 2 else words[1]
            third_word = '' if n_words < 3 else words[2]

            if first_word == '#include':

                dep = second_word[1:-1]

                if dep == 'mpi.h':
                    self.use_mpi = True
                elif dep == 'omp.h':
                    self.use_openmp = True
                elif dep not in std_headers:
                    self.header_deps.append(dep)

            elif first_word == 'int' and '(' in second_word and second_word.split('(')[0] == 'main' and not self.is_header:
                self.is_main = True

        # Compilation rule for the makefile
        self.compile_rule_declr = '\n\n%s\n%s: %s ' \
                                  % ('# Rule for compiling ' + self.filename,
                                     self.object_name, 
                                     filename_with_path.replace(' ', '\ '))
        self.compile_rule = '\n\t$(COMP) -c $(COMP_FLAGS) \"%s\"' % filename_with_path

def abort():

    print '(makemake_c.py) Usage: makemake_c.py [-openmp] [path1/]source1.c [path2/]source2.c ...'
    sys.exit(1)

if len(sys.argv) < 2: abort()

use_mpi = False
use_openmp = False

# Get path to the directory this script was run from
source_path = os.getcwd()

command_args = sys.argv[1:]

# Check if user says to use OpenMP
if '-openmp' in command_args:

    use_openmp = True
    command_args.remove('-openmp')

# Read filenames from command line and turn them into Source instances
sources = [Source(source_path, filename) for filename in command_args]

# -- Collect all program, module, procedure and dependency names
all_headers = []
all_header_deps = []

main_source = None

old_sources = list(sources)

for src in old_sources:

    use_mpi = use_mpi or src.use_mpi
    use_openmp = use_openmp or src.use_openmp

    if src.is_main:
        main_source = src

    all_header_deps += src.header_deps

    if src.is_header:

        all_headers.append(src.filename)
        sources.remove(src)
# --

# Only one executable can be built
if main_source is None:
    print '(makemake_c.py) There must be exactly one main program in all the sources combined.'
    sys.exit()

# -- Check for missing dependencies
missing_header_deps = []
for dep in all_header_deps:
    if not dep in all_headers: missing_header_deps.append(dep)

if len(missing_header_deps) != 0:

    print '(makemake_c.py) Missing header dependencies: %s' % ' '.join(list(set(missing_header_deps)))
    sys.exit(1)
# --

# -- Determine which objects the main source depends on
compile_rules = []

# For each source
for src in sources:

    dep_obects = []

    if src is main_source:

        # For each header dependency the source has
        for dep in src.header_deps:

            # Loop through all the other sources
            for src2 in sources:

                if not (src2 is src):

                    # Add object name if it also has the same dependency
                    if dep in src2.header_deps:
                        dep_obects.append(src2.object_name)

        # Get rid of duplicate object names
        dep_obects = list(set(dep_obects))

    # Update prerequisites section of compile rule and store in list
    compile_rules.append(src.compile_rule_declr + ' '.join(dep_obects) + src.compile_rule)
# --

compiler = 'mpicc' if use_mpi else 'gcc'
parallel_flag = '-fopenmp' if use_openmp else ''

# Create makefile
makefile = '''
# This makefile was generated by makemake_c.py.
# GitHub repository: https://github.com/lars-frogner/makemake.py
# 
# Usage:
# 'make':         Compiles with no compiler flags.
# 'make debug':   Compiles with flags useful for debugging.
# 'make fast':    Compiles with flags for high performance.
# 'make profile': Compiles with flags for profiling.
# 'make gprof':   Displays the profiling results with gprof.
# 'make clean':   Deletes auxiliary files.

# Define variables
COMP = %s
EXECNAME = %s
OBJECTS = %s
COMP_FLAGS = %s
LINK_FLAGS = %s

# Make sure certain rules are not activated by the presence of files
.PHONY: all debug fast profile set_debug_flags set_fast_flags set_profile_flags gprof clean

# Define default target group
all: $(EXECNAME)

# Define optional target groups
debug: set_debug_flags $(EXECNAME)
fast: set_fast_flags $(EXECNAME)
profile: set_profile_flags $(EXECNAME)

# Defines appropriate compiler flags for debugging
set_debug_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -Og -Wall -Wextra -Wconversion -pedantic -fbounds-check)

# Defines appropriate compiler flags for high performance
set_fast_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -O3)

# Defines appropriate compiler flags for profiling
set_profile_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -pg)
\t$(eval LINK_FLAGS = $(LINK_FLAGS) -pg)

# Rule for linking object files
$(EXECNAME): $(OBJECTS)
\t$(COMP) $(LINK_FLAGS) -o $(EXECNAME) $(OBJECTS)%s

# Action for removing all auxiliary files
clean:
\trm -f $(OBJECTS)

# Action for reading profiling results
gprof:
\tgprof $(EXECNAME)''' \
% (compiler,
   main_source.name + '.x',
   ' '.join([src.object_name for src in sources]),
   parallel_flag,
   parallel_flag,
   ''.join(compile_rules))

# -- Save makefile
makefilepath = os.path.join(source_path, 'makefile')
writeFile = True

if os.path.exists(makefilepath):

    # Ask user before overwriting any existing makefiles
    yn = ''
    while not yn in ['y', 'n']:
        yn = raw_input('(makemake_c.py) A makefile already exists. Overwrite? [y/n]\n').lower()

    if yn == 'n':

        writeFile = False
        print '(makemake_c.py) Makefile generation cancelled.'

if writeFile:

    f = open(makefilepath, 'w')
    f.write(makefile)
    f.close()
    print '(makemake_c.py) New makefile generated (%s).' % makefilepath
# --