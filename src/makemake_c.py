#
# This program contains a function for generating a makefile from
# lists of C source files, header files and library files.
#
# State: Functional
#
# Last modified 19.02.2017 by Lars Frogner
#
import sys, os
import datetime
import makemake_lib

def abort_multiple_producers(function):

    print 'Error: function \"\" implemented multiple times' % function
    sys.exit(1)

def abort_invalid_lib(library):

    print 'Error: invalid name for library \"%s\". Name must start with \"lib\"' % library

def clean_file_text(text):

    # This function removes non-executable code like comments and strings
    # from the given text.

    lines = text.split('\n')

    # Go through text and make sure all included header file names are
    # surrounded by angled brackets, so they are not confused with strings.

    new_lines = []

    for i in xrange(len(lines)):

        words = lines[i].split()

        for j in xrange(len(words)-1):

            if words[j] == '#include' and '"' in words[j+1]:

                words[j+1] = '<' + words[j+1][1:-1] + '>'

        if len(words) > 0: new_lines.append(' '.join(words))

    text = '\n'.join(new_lines)
    
    clean_text = [text[0]]

    # Go through text again and remove all strings and comments

    in_comm = False
    in_block_comm = False
    in_str = False

    for i in xrange(1, len(text)):

        add_now = True

        if text[i] == '"' and not (in_comm or in_block_comm):

            if in_str:

                in_str = False
                add_now = False
            
            else:
                in_str = True

        if text[i-1] == '/' and text[i] == '/' and not (in_str or in_block_comm or in_comm):

            in_comm = True
            clean_text = clean_text[:-1]

        if text[i] == '\n' and in_comm:

            in_comm = False

        if text[i-1] == '/' and text[i] == '*' and not (in_str or in_block_comm or in_comm):

            in_block_comm = True
            clean_text = clean_text[:-1]

        if text[i-1] == '*' and text[i] == '/' and in_block_comm:

            in_block_comm = False
            add_now = False

        if not (in_comm or in_block_comm or in_str) and add_now:

            clean_text.append(text[i])

    return ''.join(clean_text)

def get_included_headers(text):

    # This function checks the include statements of the given text
    # to determine its header dependencies.

    std_headers = ['assert.h', 
                   'ctype.h', 
                   'errno.h', 
                   'float.h', 
                   'limits.h', 
                   'locale.h', 
                   'math.h', 
                   'setjmp.h', 
                   'signal.h', 
                   'stdarg.h', 
                   'stddef.h', 
                   'stdio.h', 
                   'stdlib.h', 
                   'string.h', 
                   'time.h',
                   'complex.h', 
                   'fenv.h', 
                   'inttypes.h', 
                   'iso646.h', 
                   'stdbool.h', 
                   'stdint.h', 
                   'tgmath.h', 
                   'wchar.h', 
                   'wctype.h']

    use_math = False
    use_mpi = False
    use_openmp = False
    is_main = False

    lines = text.split('\n')

    included_headers = []

    # Parse file
    for line in lines:

        words = line.split()

        # Skip blank lines
        if len(words) == 0:
            continue

        n_words = len(words)

        first_word = words[0]
        second_word = '' if n_words < 2 else words[1]
        third_word = '' if n_words < 3 else words[2]

        # Check for an include statement
        if first_word == '#include':

            # Add included header file as a dependency if it isn't one
            # of the standard headers.

            dep = second_word[1:-1]

            if dep == 'mpi.h':
                use_mpi = True
            elif dep == 'omp.h':
                use_openmp = True
            elif dep == 'math.h':
                use_math = True
            elif dep not in std_headers:
                included_headers.append(dep)

        # Check for main function
        elif first_word == 'int' and \
             '(' in second_word and \
             second_word.split('(')[0] == 'main':

            is_main = True

    return included_headers, use_math, use_mpi, use_openmp, is_main

def remove_preprocessor_directives(text):

    # This function removes all preprocessor directives from the 
    # given text.

    new_lines = []

    for line in text.split('\n'):

        stripped_line = line.strip()

        if len(stripped_line) > 0 and stripped_line[0] == '#':
            continue

        new_lines.append(line)

    return '\n'.join(new_lines)

def get_declared_functions(text):

    # This function returns a list of functions that are declared
    # in the given text.

    statements = text.split(';')

    functions = []

    for statement in statements:

        paran_splitted = statement.split('(')

        if len(paran_splitted) > 1:

            pre_paran = paran_splitted[0]

            if not ('=' in pre_paran or '}' in pre_paran):

                words = pre_paran.split()

                if len(words) > 1 and words[-2] != 'return':
                    functions.append(words[-1].replace('*', ''))

    return functions

class c_source:

    # This class parses an inputted .c file and stores information
    # about its contents.

    def __init__(self, filename_with_path):

        self.filename_with_path = filename_with_path

        file_path = os.sep.join(filename_with_path.split(os.sep)[:-1])

        self.filename = filename_with_path.split(os.sep)[-1]
        self.name = '.'.join(self.filename.split('.')[:-1])
        self.object_name = self.name + '.o'

        sys.stdout.write('Parsing...')
        sys.stdout.flush()

        f = open(filename_with_path, 'r')
        text = f.read()
        f.close()

        text = clean_file_text(text)

        self.included_headers, self.use_math, self.use_mpi, self.use_openmp, self.is_main = get_included_headers(text)

        self.dependency_descripts = {}

        for header_name in self.included_headers:
            self.dependency_descripts[header_name] = 'included directly'

        print ' Done'

        if len(self.included_headers) > 0:
            print 'Included (non-standard) headers:\n' + '\n'.join([('-%s' % header_name) for header_name in self.included_headers])

        if self.use_math:
            print 'Uses math library'

        if self.use_mpi:
            print 'Uses MPI'

        if self.use_openmp:
            print 'Uses OpenMP'

        self.clean_text = remove_preprocessor_directives(text)

        # Compilation rule for the makefile
        self.compile_rule_declr = '\n\n%s\n%s: %s ' \
                                  % ('# Rule for compiling ' + self.filename,
                                     self.object_name, 
                                     filename_with_path.replace(' ', '\ '))

        self.compile_rule = '\n\t$(COMP) -c $(COMP_FLAGS) $(FLAGS) \"%s\"' % filename_with_path

class c_header:

    # This class parses an inputted .h file and stores information
    # about its contents.

    def __init__(self, filename_with_path):

        self.filename_with_path = filename_with_path

        file_path = os.sep.join(filename_with_path.split(os.sep)[:-1])

        self.filename = filename_with_path.split(os.sep)[-1]

        sys.stdout.write('Parsing...')
        sys.stdout.flush()

        f = open(filename_with_path, 'r')
        text = f.read()
        f.close()

        text = clean_file_text(text)

        self.included_headers, self.use_math, self.use_mpi, self.use_openmp = get_included_headers(text)[:4]

        text = remove_preprocessor_directives(text)

        self.declared_functions = get_declared_functions(text)

        print ' Done'

        if len(self.included_headers) > 0:
            print 'Included (non-standard) headers:\n' + '\n'.join([('-%s' % header_name) for header_name in self.included_headers])

        if len(self.declared_functions) > 0:
            print 'Declared functions:\n' + '\n'.join([('-%s' % function_name) for function_name in self.declared_functions])

        if self.use_math:
            print 'Uses math library'

        if self.use_mpi:
            print 'Uses MPI'

        if self.use_openmp:
            print 'Uses OpenMP'

def process_headers(working_dir_path, header_paths, header_files, abort_on_fail=True):

    # This function creates a list of fortran_header instances from the given 
    # lists of filenames and paths.

    header_objects = []
    extra_header_paths = []

    for file_string in header_files:

        found, filename_with_path, has_determined_path, determined_path = makemake_lib.search_for_file(file_string, 
                                                                                                       working_dir_path, 
                                                                                                       header_paths,
                                                                                                       abort_on_fail=abort_on_fail)[:4]
        if found:

            header_objects.append(c_header(filename_with_path))

            if has_determined_path:
                extra_header_paths.append(determined_path)

    extra_header_paths = list(set(extra_header_paths))

    return header_objects, extra_header_paths

def find_missing_headers(working_dir_path, header_paths, source_objects, header_objects):

    # Find all headers included by any source or header file

    iter_list = source_objects + header_objects

    while len(iter_list) > 0:

        missing_headers = []

        for source in iter_list:

            for header_name in source.included_headers:

                found = False

                for header in header_objects:

                    if header_name == header.filename:

                        found = True
                        break

                if not found:

                    missing_headers.append(header_name)

        missing_headers = list(set(missing_headers))

        if len(missing_headers) > 0:
            print '\nFound unspecified header dependencies\nStarting search for missing headers...'

        extra_header_objects, extra_header_paths = process_headers(working_dir_path, 
                                                                   header_paths, 
                                                                   missing_headers, 
                                                                   abort_on_fail=False)

        header_objects = list(set(header_objects + extra_header_objects))
        header_paths = list(set(header_paths + extra_header_paths))

        iter_list = extra_header_objects

    return header_paths, header_objects

def process_files(working_dir_path, source_paths, header_paths, library_paths, source_files, header_files, library_files):

    # This function creates a list of c_source instances from the given 
    # lists of filenames and paths, and also returns a list of c_header
    # instances produced by the process_headers() function.

    # Process header files

    header_objects, extra_header_paths = process_headers(working_dir_path, header_paths, header_files)

    # Process source files

    source_objects = []

    for file_string in source_files:

        filename_with_path = makemake_lib.search_for_file(file_string, 
                                                          working_dir_path, 
                                                          source_paths)[1]

        source_objects.append(c_source(filename_with_path))

    # Add missing headers

    header_paths, header_objects = find_missing_headers(working_dir_path, header_paths, source_objects, header_objects)

    header_paths = list(set(header_paths + extra_header_paths))

    # Process library files

    extra_library_paths = []

    for i in xrange(len(library_files)):

        has_determined_path, determined_path, filename = makemake_lib.search_for_file(library_files[i], 
                                                                                      working_dir_path, 
                                                                                      library_paths)[2:]

        if len(filename) < 3 or filename[:3] != 'lib':
            abort_invalid_lib(filename)

        filename = '.'.join(filename.split('.')[:-1])

        library_files[i] = filename[3:]

        if has_determined_path:
            extra_library_paths.append(determined_path)

    library_paths = list(set(library_paths + extra_library_paths))

    return source_objects, header_paths, header_objects, library_paths

def determine_header_dependencies(source_objects, header_objects):

    # This function creates a dictionary with the c_source objects
    # as keys. The values are lists of paths to the headers that 
    # the source depends on.

    sys.stdout.write('Finding header dependencies...')
    sys.stdout.flush()

    # Find all headers that each header includes

    header_header_dependencies = {}

    for header in header_objects:

        header_header_dependencies[header] = []

        for header_name in header.included_headers:

            for other_header in header_objects:

                if not (header is other_header) and header_name == other_header.filename:

                    header_header_dependencies[header].append(other_header)
                    break

    # Find all headers that each header dependes on, directly or 
    # indirectly

    def add_header_dependencies(original_parent, parent):

        for child in header_header_dependencies[parent]:

            if not (child is original_parent or child in header_header_dependencies[original_parent]):

                header_header_dependencies[original_parent].append(child)

                add_header_dependencies(original_parent, child)

    for header in header_objects:

        for child in header_header_dependencies[header]:

            add_header_dependencies(header, child)

    # Find all headers that each source depends on, directly or 
    # indirectly. Also transfer any dependencies the headers have 
    # to the sources that depend on them

    source_header_dependencies = {}

    for source in source_objects:

        source_header_dependencies[source] = []

        for header_name in source.included_headers:

            for header in header_objects:

                if header_name == header.filename:

                    for other_header in [header] + header_header_dependencies[header]:

                        if not other_header.filename_with_path in source_header_dependencies[source]:

                            source_header_dependencies[source].append(other_header.filename_with_path)

                            for included_header in other_header.included_headers:

                                if not included_header in source.included_headers:

                                    source.included_headers.append(included_header)
                                    source.dependency_descripts[included_header] = 'included indirectly through %s' % (other_header.filename)

                    break

    print ' Done'

    return source_header_dependencies

def determine_object_dependencies(source_objects, header_objects, header_dependencies):

    # This function creates a dictionary with the c_source objects
    # as keys. The values are lists of object names for the other
    # sources that implement functions that the source uses.

    sys.stdout.write('Determining object dependencies...')
    sys.stdout.flush()

    # Create a dictionary of all headers containing the sources that
    # include each header.

    header_source_dependencies = {}

    for header in header_objects:

        header_source_dependencies[header] = []

        for source in source_objects:

            if header.filename in source.included_headers:
                header_source_dependencies[header].append(source)

    # Create a dictionary of headers containing the functions that each
    # header declares. Each function is a key to a dictionary containing
    # a list of the sources that implement the function ("producers")
    # and a list of the sources that call the function ("consumers").

    producer_consumer_dict = {}

    for header in header_objects:

        producer_consumer_dict[header] = {}

        for function in header.declared_functions:

            producer_consumer_dict[header][function] = {}
            producer_consumer_dict[header][function]['producers'] = []
            producer_consumer_dict[header][function]['consumers'] = []

            for source in header_source_dependencies[header]:

                # Split source text at the function name
                func_splitted = source.clean_text.split(function + '(')

                if len(func_splitted) < 2: continue

                is_producer = False
                is_consumer = False

                # Loop through all substrings following a function name
                for substring in func_splitted[1:]:

                    # Find the character following the parantheses after the 
                    # function name.

                    paran_splitted = substring.split(')')

                    if len(paran_splitted) < 2: continue

                    idx = 0

                    for element in paran_splitted:

                        if '(' in element:
                            idx += 1
                        else:
                            break

                    character_after = paran_splitted[idx+1].strip()
                    if len(character_after) > 0: character_after = character_after[0]

                    # If the next character is a curly bracket, the function is implmented
                    if character_after == '{':

                        is_producer = True
                    
                    # Otherwise, the function is called
                    else:
                    
                        is_consumer = True

                if is_producer and not is_consumer:

                    producer_consumer_dict[header][function]['producers'].append(source)

                elif is_consumer and not is_producer:

                    producer_consumer_dict[header][function]['consumers'].append(source)


        #print '-' + header.filename
        #for function in producer_consumer_dict[header]:
        #    print function, [src.filename for src in producer_consumer_dict[header][function]['consumers']]

    # Make sure that no function was implemented multiple times
    for header in header_objects:

        for function in producer_consumer_dict[header]:

            n_producers = len(producer_consumer_dict[header][function]['producers'])

            if n_producers > 1:
                abort_multiple_producers(function)

    # Convert the dictionary of producers and consumers into a dictionary
    # of sources, where the values are the object names of the producers 
    # for the functions that the source uses.

    object_dependencies = {}

    for source in source_objects:

        object_dependencies[source] = []

        for header in header_objects:

            for function in producer_consumer_dict[header]:

                for consumer in producer_consumer_dict[header][function]['consumers']:

                    if source is consumer:

                        if len(producer_consumer_dict[header][function]['producers']) > 0:

                            producer_source = producer_consumer_dict[header][function]['producers'][0]
                            object_dependencies[source].append(producer_source)

                            if producer_source.filename in source.dependency_descripts:
                                source.dependency_descripts[producer_source.filename] += ', %s()' % function
                            else:
                                source.dependency_descripts[producer_source.filename] = 'through %s()' % function

                        break

        object_dependencies[source] = list(set(object_dependencies[source]))

    print ' Done'

    # Remove unnecessary sources

    sys.stdout.write('Removing independent sources...')
    sys.stdout.flush()

    not_needed = []

    for source in source_objects:

        if not source.is_main:

            is_needed = False

            for other_source in source_objects:

                if not (other_source is source):

                    for source_dependency in object_dependencies[other_source]:

                        if source_dependency is source:
                            is_needed = True

            if not is_needed:
                not_needed.append(source)

    for remove_src in not_needed:

        source_objects.remove(remove_src)
        object_dependencies.pop(remove_src)

    print ' Done'

    # Fix circular dependencies

    sys.stdout.write('Checking for circular dependencies... ')
    sys.stdout.flush()

    object_dependencies = makemake_lib.cycle_resolver().resolve_cycles(object_dependencies)

    print 'Done'

    # Print dependency list

    dependency_text = '\nList of detected dependencies:'

    for source in sorted(object_dependencies, key=lambda source: len(object_dependencies[source] + header_dependencies[source]), reverse=True):

        if len(object_dependencies[source] + header_dependencies[source]) == 0:

            dependency_text += '\n' + '\n%s: None' % (source.filename)
        
        else:

            dependency_text += '\n' + '\n%s:' % (source.filename)
        
            if len(header_dependencies[source]) > 0:
                dependency_text += '\n' + '\n'.join(['-%s [%s]' % (hdr.split(os.sep)[-1], source.dependency_descripts[hdr.split(os.sep)[-1]]) for hdr in header_dependencies[source]])

            if len(object_dependencies[source]) > 0:
                dependency_text += '\n' + '\n'.join(['-%s [%s]' % (src.filename, source.dependency_descripts[src.filename]) for src in object_dependencies[source]])

    # Convert values from c_source instances to object names

    for source in object_dependencies:

        object_dependencies[source] = [src.object_name for src in object_dependencies[source]]

    return source_objects, object_dependencies, dependency_text

def determine_library_usage(source_objects, header_objects):

    # This function collects the information about the individual sources.

    use_mpi = False
    use_openmp = False
    use_math = False

    # Go through all source and header objects and gather information
    # about which libraries to use and which source has the main function.

    for source in source_objects:

        use_mpi = use_mpi or source.use_mpi
        use_openmp = use_openmp or source.use_openmp
        use_math = use_math or source.use_math

    for header in header_objects:

        use_mpi = use_mpi or header.use_mpi
        use_openmp = use_openmp or header.use_openmp
        use_math = use_math or header.use_math

    return use_mpi, use_openmp, use_math

def gather_compile_rules(source_objects, header_dependencies, object_dependencies):

    # This function creates a list of compile rules for all the sources,
    # making sure that all the dependencies of the sources are taken
    # into account.

    compile_rules = []

    # For each source
    for source in source_objects:

        dependencies = [header_path.replace(' ', '\ ') for header_path in header_dependencies[source]] \
                       + object_dependencies[source]

        # Update prerequisites section of the main compile rule and add to the list
        compile_rules.append(source.compile_rule_declr + ' '.join(dependencies) + source.compile_rule)

    return ''.join(compile_rules)

def generate_c_makefile_from_files(working_dir_path, source_paths, header_paths, library_paths, source_files, header_files, library_files, compiler):

    # This function generates makefiles for compiling the programs 
    # in the given C source files.

    # Get information from files

    is_win = sys.platform == 'win32'
    delete_cmd = 'del 2>nul /F' if is_win else 'rm -f'
    exec_ending = '.exe' if is_win else '.x'

    print '\nCollecting files...'

    source_objects, header_paths, header_objects, library_paths = process_files(working_dir_path, 
                                                                                source_paths, 
                                                                                header_paths, 
                                                                                library_paths, 
                                                                                source_files, 
                                                                                header_files, 
                                                                                library_files)

    program_sources = []

    filtered_source_objects = list(source_objects)

    for source in source_objects:

        if source.is_main:

            program_sources.append(source)
            filtered_source_objects.remove(source)

    if len(program_sources) == 0:
        makemake_lib.abort_no_something_file('main')

    print '\nPrograms to generate makefiles for:\n%s' % ('\n'.join(['-%s' % (src.name + exec_ending) for src in program_sources]))

    for program_source in program_sources:

        new_source_objects = [program_source] + filtered_source_objects
        executable_name = program_source.name + exec_ending

        generate_c_makefile_from_objects(working_dir_path, new_source_objects, header_paths, library_paths, header_objects, library_files, executable_name, compiler, is_win, delete_cmd)

def generate_c_makefile_from_objects(working_dir_path, source_objects, header_paths, library_paths, header_objects, library_files, executable_name, compiler, is_win, delete_cmd):

    # This function generates a makefile for compiling the program 
    # given by the supplied c_source objects.

    print '\nGenerating makefile for executable \"%s\"...\n' % executable_name

    # Get information from files

    header_dependencies = determine_header_dependencies(source_objects, 
                                                        header_objects)

    source_objects, object_dependencies, dependency_text = determine_object_dependencies(source_objects, 
                                                                                         header_objects,
                                                                                         header_dependencies)

    sys.stdout.write('\nGenerating makefile text... ')
    sys.stdout.flush()

    use_mpi, use_openmp, use_math = determine_library_usage(source_objects, 
                                                            header_objects)

    compile_rule_string = gather_compile_rules(source_objects, 
                                               header_dependencies, 
                                               object_dependencies)

    # Collect makefile parameters

    default_compiler = 'gcc'
    compiler = default_compiler if (compiler is None) else compiler

    debug_flags, fast_flags = makemake_lib.read_flag_groups(compiler)

    source_object_names_string = ' '.join([source.object_name for source in source_objects])

    openmp_flag = '-fopenmp' if use_openmp else ''
    math_flag = ' -lm' if use_math else ''

    compilation_flags = openmp_flag + ' '.join(['-I\"%s\"' % path for path in header_paths])

    linking_flags = openmp_flag

    library_flags = ''.join([' -L\"%s\"' % path for path in library_paths]) \
                    + math_flag \
                    + ''.join([' -l%s' % filename for filename in library_files])

    if is_win:
        help_text = 'Usage: & echo make ^<argument 1^> ^<argument 2^> ... & echo. & echo Arguments: & echo ^<none^>:  Compiles with no compiler flags. & echo debug:   Compiles with flags useful for debugging. & echo fast:    Compiles with flags for high performance. & echo profile: Compiles with flags for profiling. & echo gprof:   Displays the profiling results with gprof. & echo clean:   Deletes auxiliary files. & echo help:    Displays this help text. & echo. & echo To compile with additional flags, add the argument & echo FLAGS="<flags>"'
    else:
        help_text = '"Usage:\\nmake <argument 1> <argument 2> ...\\n\\nArguments:\\n<none>:    Compiles with no compiler flags.\\ndebug:   Compiles with flags useful for debugging.\\nfast:    Compiles with flags for high performance.\\nprofile: Compiles with flags for profiling.\\ngprof:   Displays the profiling results with gprof.\\nclean:   Deletes auxiliary files.\\nhelp:    Displays this help text.\\n\\nTo compile with additional flags, add the argument\\nFLAGS=\\"<flags>\\""'

    # Create makefile text

    makefile = '''#@%s
# This makefile was generated by makemake.py (%s).
# GitHub repository: https://github.com/lars-frogner/makemake.py
#
# Usage:
# make <argument 1> <argument 2> ...
#
# Arguments:
# <none>:  Compiles with no compiler flags.
# debug:   Compiles with flags useful for debugging.
# fast:    Compiles with flags for high performance.
# profile: Compiles with flags for profiling.
# gprof:   Displays the profiling results with gprof.
# clean:   Deletes auxiliary files.
# help:    Displays this help text.
#
# To compile with additional flags, add the argument
# FLAGS="<flags>"

# Define variables
COMP = %s
EXECNAME = %s
OBJECTS = %s
COMP_FLAGS = %s
LINK_FLAGS = %s

# Make sure certain rules are not activated by the presence of files
.PHONY: all debug fast profile set_debug_flags set_fast_flags set_profile_flags clean gprof help

# Define default target group
all: $(EXECNAME)

# Define optional target groups
debug: set_debug_flags $(EXECNAME)
fast: set_fast_flags $(EXECNAME)
profile: set_profile_flags $(EXECNAME)

# Defines appropriate compiler flags for debugging
set_debug_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) %s)

# Defines appropriate compiler flags for high performance
set_fast_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) %s)

# Defines appropriate compiler flags for profiling
set_profile_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -pg)
\t$(eval LINK_FLAGS = $(LINK_FLAGS) -pg)

# Rule for linking object files
$(EXECNAME): $(OBJECTS)
\t$(COMP) $(LINK_FLAGS) $(FLAGS) -o $(EXECNAME) $(OBJECTS)%s%s

# Action for removing all auxiliary files
clean:
\t%s $(OBJECTS)

# Action for reading profiling results
gprof:
\tgprof $(EXECNAME)

# Action for printing help text
help:
\t@echo %s''' \
    % (executable_name[:-2],
       datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
       'mpicc' if use_mpi else compiler,
       executable_name,
       source_object_names_string,
       compilation_flags,
       linking_flags,
       debug_flags,
       fast_flags,
       library_flags,
       compile_rule_string,
       delete_cmd,
       help_text)

    print 'Done'

    print dependency_text

    makemake_lib.save_makefile(makefile, working_dir_path, executable_name[:-2])