#
# This program contains a function for generating a makefile from
# lists of C source files, header files and library files.
#
# State: Functional
#
# Last modified 02.02.2017 by Lars Frogner
#
import sys, os
import makemake_lib

def abort_multiple_producers(function):

    print 'Error: function \"\" implemented multiple times' % function
    sys.exit(1)

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

        if len(paran_splitted) > 0:

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

        file_path = '/'.join(filename_with_path.split('/')[:-1])

        self.filename = filename_with_path.split('/')[-1]
        self.name = '.'.join(self.filename.split('.')[:-1])
        self.object_name = self.name + '.o'

        sys.stdout.write('Parsing ...')
        sys.stdout.flush()

        f = open(filename_with_path, 'r')
        text = f.read()
        f.close()

        text = clean_file_text(text)

        self.included_headers, self.use_math, self.use_mpi, self.use_openmp, self.is_main = get_included_headers(text)

        print ' Done'

        if len(self.included_headers) > 0:
            print 'Included (non-standard) headers:\n' + '\n'.join([('-%s' % header_name) for header_name in self.included_headers])

        self.clean_text = remove_preprocessor_directives(text)

        # Compilation rule for the makefile
        self.compile_rule_declr = '\n\n%s\n%s: %s ' \
                                  % ('# Rule for compiling ' + self.filename,
                                     self.object_name, 
                                     filename_with_path.replace(' ', '\ '))

        self.compile_rule = '\n\t$(COMP) -c $(COMP_FLAGS) \"%s\"' % filename_with_path

class c_header:

    # This class parses an inputted .h file and stores information
    # about its contents.

    def __init__(self, filename_with_path):

        self.filename_with_path = filename_with_path

        file_path = '/'.join(filename_with_path.split('/')[:-1])

        self.filename = filename_with_path.split('/')[-1]

        sys.stdout.write('Parsing ...')
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

def process_files(working_dir_path, source_paths, header_paths, library_paths, source_files, header_files, library_files):

    # This function creates lists of c_source and c_header instances
    # from the given lists of filenames and paths. It also updates
    # the lists of header and library paths.

    # Process header files

    header_objects = []
    extra_header_paths = []

    for file_string in header_files:

        filename_with_path, has_specified_path, specified_path = makemake_lib.search_for_file(file_string, 
                                                                                              working_dir_path, 
                                                                                              header_paths)

        header_objects.append(c_header(filename_with_path))

        if has_specified_path:
            extra_header_paths.append(specified_path)

    header_paths = list(set(header_paths + extra_header_paths))

    # Process source files

    source_objects = []

    for file_string in source_files:

        filename_with_path = makemake_lib.search_for_file(file_string, 
                                                          working_dir_path, 
                                                          source_paths)[0]

        source_objects.append(c_source(filename_with_path))

    # Process library files

    extra_library_paths = []

    for file_string in library_files:

        has_specified_path, specified_path = makemake_lib.search_for_file(file_string, 
                                                                          working_dir_path, 
                                                                          library_paths)[1:3]

        if has_specified_path:
            extra_library_paths.append(specified_path)

    library_paths = list(set(library_paths + extra_library_paths))

    return source_objects, header_objects, header_paths, library_paths

def gather_source_information(source_objects, header_objects, force_openmp):

    # This function collects the information about the individual sources.

    use_mpi = False
    use_openmp = force_openmp
    use_math = False

    main_source = None

    # Go through all source and header objects and gather information
    # about which libraries to use and which source has the main function.

    for source in source_objects:

        use_mpi = use_mpi or source.use_mpi
        use_openmp = use_openmp or source.use_openmp
        use_math = use_math or source.use_math

        if source.is_main:

            if main_source is None:
                main_source = source
            else:
                makemake_lib.abort_multiple_something_files('main', main_source.filename, source.filename)

    for header in header_objects:

        use_mpi = use_mpi or header.use_mpi
        use_openmp = use_openmp or header.use_openmp
        use_math = use_math or header.use_math

    if main_source is None:
        makemake_lib.abort_no_something_file('main')

    return main_source, use_mpi, use_openmp, use_math

def determine_header_dependencies(source_objects, header_objects):

    # This function creates a dictionary with the c_source objects
    # as keys. The values are lists of paths to the headers that 
    # the source includes.

    header_dependencies = {}

    for source in source_objects:

        header_dependencies[source] = []

        for header_name in source.included_headers:

            found = False

            for header in header_objects:

                if header_name == header.filename:

                    header_dependencies[source].append(header.filename_with_path)
                    found = True
                    break

            if not found:
                makemake_lib.abort_missing_something('header', source.filename, header_name)

    return header_dependencies

def determine_object_dependencies(source_objects, header_objects):

    # This function creates a dictionary with the c_source objects
    # as keys. The values are lists of object names for the other
    # sources that implement functions that the source uses.

    # Create a dictionary of all headers containing the sources that
    # include each header.

    header_dependencies = {}

    for header in header_objects:

        header_dependencies[header] = []

        for source in source_objects:

            if header.filename in source.included_headers:
                header_dependencies[header].append(source)

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

            for source in header_dependencies[header]:

                # Split source text at the function name
                func_splitted = source.clean_text.split(function + '(')

                if len(func_splitted) < 1: continue

                is_producer = False
                is_consumer = False

                # Loop through all substrings following a function name
                for substring in func_splitted[1:]:

                    # Find the character following the parantheses after the 
                    # function name.

                    paran_splitted = substring.split(')')

                    if len(paran_splitted) < 1: continue

                    character_after = paran_splitted[1].strip()[0]

                    # If the next character is a curly bracket, the function is implmented
                    if character_after == '{':

                        is_producer = True
                    
                    # If the next character is a semicolon, the function is called
                    elif character_after == ';':
                    
                        is_consumer = True

                if is_producer and not is_consumer:

                    producer_consumer_dict[header][function]['producers'].append(source)

                elif is_consumer and not is_producer:

                    producer_consumer_dict[header][function]['consumers'].append(source)

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

                            object_dependencies[source]\
                            .append(producer_consumer_dict[header][function]['producers'][0])

                        break

        object_dependencies[source] = list(set(object_dependencies[source]))

    # Fix circular dependencies

    object_dependencies = makemake_lib.cycle_resolver().resolve_cycles(object_dependencies)

    # Print dependency list

    print '\nSource dependencies:'

    for source in sorted(object_dependencies, key=lambda source: len(object_dependencies[source]), reverse=True):

        if len(object_dependencies[source]) == 0:

            print '\n%s: None' % (source.filename)
        
        else:
        
            print '\n%s:\n%s' % (source.filename, '\n'.join(['-%s' % (src.filename) for src in object_dependencies[source]]))

    # Convert values from c_source instances to object names

    for source in object_dependencies:

        object_dependencies[source] = [src.object_name for src in object_dependencies[source]]

    return object_dependencies

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

def generate_makefile(working_dir_path, source_paths, header_paths, library_paths, source_files, header_files, library_files, force_openmp):

    # This function generates a makefile for compiling the given 
    # C source files.

    # Get information from files

    print '\nCollecting files...'

    source_objects, header_objects, header_paths, library_paths = process_files(working_dir_path, 
                                                                                source_paths, 
                                                                                header_paths, 
                                                                                library_paths, 
                                                                                source_files, 
                                                                                header_files, 
                                                                                library_files)

    main_source, use_mpi, use_openmp, use_math = gather_source_information(source_objects, 
                                                                           header_objects, 
                                                                           force_openmp)

    print '\nExamining dependencies...'

    header_dependencies = determine_header_dependencies(source_objects, 
                                                        header_objects)

    object_dependencies = determine_object_dependencies(source_objects, 
                                                            header_objects)

    print '\nGenerating makefile text...'

    compile_rule_string = gather_compile_rules(source_objects, 
                                               header_dependencies, 
                                               object_dependencies)

    # Collect makefile parameters

    compiler = 'mpicc' if use_mpi else 'gcc'

    executable_name = main_source.name + '.x'

    source_object_names_string = ' '.join([source.object_name for source in source_objects])

    parallel_flag = '-fopenmp' if use_openmp else ''
    math_flag = ' -lm' if use_math else ''

    compilation_flags = parallel_flag + ' '.join(['-I\"%s\"' % path for path in header_paths])

    pre_linking_flags = parallel_flag

    post_linking_flags = ' '.join(['-L\"%s\"' % path for path in library_paths]) \
                         + math_flag \
                         + ' '.join(['-l%s' % filename for filename in library_files])

    # Create makefile text

    makefile = '''
# This makefile was generated by makemake.py.
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
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -Og -W -Wall -fno-common -Wcast-align -Wredundant-decls -Wbad-function-cast -Wwrite-strings -Waggregate-return -Wstrict-prototypes -Wmissing-prototypes -Wextra -Wconversion -pedantic -fbounds-check)

# Defines appropriate compiler flags for high performance
set_fast_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -O3 -ffast-math)

# Defines appropriate compiler flags for profiling
set_profile_flags:
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -pg)
\t$(eval LINK_FLAGS = $(LINK_FLAGS) -pg)

# Rule for linking object files
$(EXECNAME): $(OBJECTS)
\t$(COMP) $(LINK_FLAGS) -o $(EXECNAME) $(OBJECTS)%s%s

# Action for removing all auxiliary files
clean:
\trm -f $(OBJECTS)

# Action for reading profiling results
gprof:
\tgprof $(EXECNAME)''' \
    % (compiler,
       executable_name,
       source_object_names_string,
       compilation_flags,
       pre_linking_flags,
       post_linking_flags,
       compile_rule_string)

    makemake_lib.save_makefile(makefile, working_dir_path)