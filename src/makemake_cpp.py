#
# This program contains a function for generating a makefile from
# lists of C++ source files, header files and library files.
#
# State: Not functional
#
# Last modified 13.06.2017 by Lars Frogner
#
import sys
import os
import re
import makemake_lib


class cpp_source:

    # This class extracts relevant information from a C++ source
    # file and stores it in class attributes.

    def __init__(self, filename_with_path, is_header=False):

        self.std_headers = ['cstdlib',
                            'csignal',
                            'csetjmp',
                            'cstdarg',
                            'typeinfo',
                            'typeindex',
                            'type_traits',
                            'bitset',
                            'functional',
                            'utility',
                            'ctime',
                            'chrono',
                            'cstddef',
                            'initializer_list',
                            'tuple',
                            'any',
                            'optional',
                            'variant',
                            'new',
                            'memory',
                            'scoped_allocator',
                            'memory_resource',
                            'climits',
                            'cfloat',
                            'cstdint',
                            'cinttypes',
                            'limits',
                            'exception',
                            'stdexcept',
                            'cassert',
                            'system_error',
                            'cerrno',
                            'cctype',
                            'cwctype',
                            'cstring',
                            'cwchar',
                            'cuchar',
                            'string',
                            'string_view',
                            'array',
                            'vector',
                            'deque',
                            'list',
                            'forward_list',
                            'set',
                            'map',
                            'unordered_set',
                            'unordered_map',
                            'stack',
                            'queue',
                            'algorithm',
                            'execution',
                            'iterator',
                            'cmath',
                            'complex',
                            'valarray',
                            'random',
                            'numeric',
                            'ratio',
                            'cfenv',
                            'iosfwd',
                            'ios',
                            'istream',
                            'ostream',
                            'iostream',
                            'fstream',
                            'sstream',
                            'strstream',
                            'iomanip',
                            'streambuf',
                            'cstdio',
                            'locale',
                            'clocale',
                            'codecvt',
                            'regex',
                            'atomic',
                            'thread',
                            'mutex',
                            'shared_mutex',
                            'future',
                            'condition_variable',
                            'filesystem',
                            'experimental/algorithm',
                            'experimental/any',
                            'experimental/chrono',
                            'experimental/deque',
                            'experimental/execution_policy',
                            'experimental/exception_list',
                            'experimental/filesystem',
                            'experimental/forward_list',
                            'experimental/future',
                            'experimental/list',
                            'experimental/functional',
                            'experimental/map',
                            'experimental/memory',
                            'experimental/memory_resource',
                            'experimental/numeric',
                            'experimental/optional',
                            'experimental/ratio',
                            'experimental/regex',
                            'experimental/set',
                            'experimental/string',
                            'experimental/string_view',
                            'experimental/system_error',
                            'experimental/tuple',
                            'experimental/type_traits',
                            'experimental/unordered_map',
                            'experimental/unordered_set',
                            'experimental/utility',
                            'experimental/vector',
                            'ccomplex',
                            'complex.h',
                            'ctgmath',
                            'tgmath.h',
                            'ciso646',
                            'iso646.h',
                            'cstdalign',
                            'stdalign.h',
                            'cstdbool',
                            'stdbool.h',
                            'assert.h',
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

        self.filename_with_path = filename_with_path

        self.filename = filename_with_path.split(os.sep)[-1]
        self.name = '.'.join(self.filename.split('.')[:-1])
        self.object_name = self.name + '.o'

        print('Parsing... ', end='')

        f = open(filename_with_path, 'r')
        self.text = f.read()
        f.close()

        no_strings_text = self.clean_file_text()

        self.is_main, self.included_headers, \
            self.internal_libraries = self.get_included_headers(no_strings_text)

        self.executable_name = self.name + ('.exe' if sys.platform == 'win32' else '.x')

        self.clean_text = self.remove_preprocessor_directives(no_strings_text)

        if is_header:
            self.declared_classes, no_class_text = self.extract_declared_classes(self.clean_text)
            self.declared_functions = self.get_declared_functions(no_class_text)
            self.declared_methods = []

            for class_name in self.declared_classes:
                for method in self.declared_classes[class_name]:

                    self.declared_methods.append('%s::%s'.format(class_name, method))

        self.dependency_descripts = {}

        for header_name in self.included_headers:
            self.dependency_descripts[header_name] = 'included directly'

        print('Done')

        if len(self.included_headers) > 0:
            print('Included (non-standard) headers:\n' +
                  '\n'.join(['-{}'.format(header_name)
                             for header_name in self.included_headers]))

        if is_header and len(self.declared_classes) > 0:

            print('Declared classes and methods:')

            for class_name in self.declared_classes:

                print('-{}'.format(class_name))

                for method in self.declared_classes[class_name]:

                    print(' --{}'.format(method))

        if is_header and len(self.declared_functions) > 0:
            print('Declared functions:\n' +
                  '\n'.join(['-{}'.format(function_name)
                             for function_name in self.declared_functions]))

        if self.filename == 'PasIO.h':
            sys.exit(1)

        if self.internal_libraries['mpi']:
            print('Uses MPI')

        if self.internal_libraries['openmp']:
            print('Uses OpenMP')

        # Compilation rule for the makefile
        self.compile_rule_declr = '\n\n{}\n{}: {} '\
                                  .format('# Rule for compiling ' + self.filename,
                                          self.object_name,
                                          filename_with_path.replace(' ', '\ '))

        self.compile_rule = '\n\t$(COMPILER) -c $(EXTRA_FLAGS) $(COMPILATION_FLAGS) ' + \
            '$(HEADER_PATH_FLAGS) \"{}\"'.format(filename_with_path)

    def clean_file_text(self):

        # This function removes non-executable code like comments and strings
        # from the source text.

        lines = self.text.split('\n')

        # Go through text and make sure all included header file names are
        # surrounded by angled brackets, so they are not confused with strings.

        new_lines = []

        for i in range(len(lines)):

            words = lines[i].split()

            for j in range(len(words)-1):

                if words[j] in ['#include', '#import'] and '"' in words[j+1]:

                    words[j+1] = '<' + words[j+1][1:-1] + '>'

            if len(words) > 0:
                new_lines.append(' '.join(words))

        text = '\n'.join(new_lines)

        clean_text = [text[0]]

        # Go through text again and remove all strings and comments

        in_comm = False
        in_block_comm = False
        in_str = False

        for i in range(1, len(text)):

            add_now = True

            if text[i] == '"' and not (in_comm or in_block_comm):

                if in_str:

                    in_str = False
                    add_now = False

                else:
                    in_str = True

            if text[i-1] == '/' and text[i] == '/' and \
               not (in_str or in_block_comm or in_comm):

                in_comm = True
                clean_text = clean_text[:-1]

            if text[i] == '\n' and in_comm:

                in_comm = False

            if text[i-1] == '/' and text[i] == '*' and \
               not (in_str or in_block_comm or in_comm):

                in_block_comm = True
                clean_text = clean_text[:-1]

            if text[i-1] == '*' and text[i] == '/' and in_block_comm:

                in_block_comm = False
                add_now = False

            if not (in_comm or in_block_comm or in_str) and add_now:

                clean_text.append(text[i])

        return ''.join(clean_text)

    def get_included_headers(self, text):

        # This function checks the include statements of the given text
        # to determine its header dependencies.

        is_main = False
        internal_libraries = {'mpi': False, 'openmp': False}

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

            # Check for an include statement
            if first_word in ['#include', '#import']:

                # Add included header file as a dependency if it isn't one
                # of the standard headers.

                dep = second_word[1:-1]

                if dep == 'mpi.h':
                    internal_libraries['mpi'] = True
                elif dep == 'omp.h':
                    internal_libraries['openmp'] = True
                elif dep not in self.std_headers:
                    included_headers.append(dep)

            # Check for main function
            elif first_word == 'int' and '(' in second_word and \
                 second_word.split('(')[0] == 'main':

                is_main = True

        return is_main, included_headers, internal_libraries

    def remove_preprocessor_directives(self, text):

        # This function removes all preprocessor directives from the
        # given text.

        new_lines = []
        cont = False

        for line in text.split('\n'):

            stripped_line = line.strip()

            if len(stripped_line) > 0 and (cont or stripped_line[0] == '#'):

                cont = stripped_line[-1] == '\\'
                continue

            elif len(stripped_line) == 0:
                continue

            new_lines.append(line)

        return '\n'.join(new_lines)

    def extract_declared_classes(self, text):

        # This method finds the declared classes in a text and removes
        # the contents of the class declarations from the text.

        classes_with_text = {}

        statements = text.split('{')
        clean_text = ''

        idx = 0

        while idx < len(statements)-1:

            semi_paran_splitted = statements[idx].split(';')
            last_words = semi_paran_splitted[-1].split()

            class_type = None

            if 'class' in last_words:
                class_type = 'class'

            elif 'struct' in last_words:
                class_type = 'struct'

            if class_type is not None:

                clean_text += ''.join([s + ';' for s in semi_paran_splitted[:-1]])

                class_word_loc = last_words.index(class_type)
                class_name = last_words[class_word_loc+1]
                classes_with_text[class_name] = ''

                count = 1
                idx += 1

                while True:

                    char_idx = 0

                    for char in statements[idx]:

                        if char == '}':

                            count -= 1

                            if count == 0:
                                break

                        char_idx += 1

                    if count == 0:

                        classes_with_text[class_name] += statements[idx][:char_idx]
                        statements[idx] = statements[idx][char_idx+2:]
                        semi_paran_splitted = statements[idx].split(';')
                        last_words = semi_paran_splitted[-1].split()

                        class_type = None

                        if 'class' in last_words:
                            class_type = 'class'

                        elif 'struct' in last_words:
                            class_type = 'struct'

                        if class_type is not None:

                            clean_text += ''.join([s + ';' for s in semi_paran_splitted[:-1]])
                            statements[idx] = semi_paran_splitted[-1]

                        break

                    classes_with_text[class_name] += statements[idx] + '{'
                    count += 1
                    idx += 1

            else:
                clean_text += statements[idx] + '{'
                idx += 1

        clean_text += statements[-1]

        classes = {}

        for cl in classes_with_text:
            classes[cl] = self.get_declared_functions(classes_with_text[cl])

        return classes, clean_text

    def get_declared_functions(self, text):

        # This function returns a list of functions that are declared
        # in the given text.

        statements = text.split(';')

        functions = []

        for statement in statements:

            paran_splitted = statement.replace('\n', ' ').split('(')

            if len(paran_splitted) > 1:

                pre_paran = paran_splitted[0]

                if not ('=' in pre_paran or '}' in pre_paran):

                    words = pre_paran.split()

                    if len(words) > 1 and words[-2] != 'return':
                        functions.append(words[-1].replace('*', ''))

        return functions

    def abort_multiple_main(self):

        print('\nError: multiple main functions in \"{}\"'
              .format(self.filename))

        sys.exit(1)

    def update_source_information(self, header):

        # This function updates the source information based on the
        # information about a given included header.

        if header.is_main:

            if self.is_main:
                self.abort_multiple_main()
            else:
                self.is_main = True

        for included_header in header.included_headers:

            if included_header not in self.included_headers:

                self.included_headers.append(included_header)
                self.dependency_descripts[included_header] = \
                    'included indirectly through {}'\
                    .format(header.filename)


class cpp_header(cpp_source):

    def __init__(self, filename_with_path):

        super().__init__(filename_with_path, is_header=True)


def generate_makefile(manager, sources):

    # This function generates a makefile for compiling the program
    # given by the supplied cpp_source objects.

    if manager.executable:
        print('\nGenerating makefile for executable \"{}\"...\n'
              .format(manager.executable))
    elif manager.library:
        print('\nGenerating makefile for library \"{}\"...\n'
              .format(manager.library))
    else:
        print('\nGenerating makefile for executable \"{}\"...\n'
              .format(sources.program_source.executable_name))

    # Get information from files

    sources.determine_header_dependencies()

    object_dependencies = determine_object_dependencies(sources.source_instances,
                                                        sources.header_instances)

    dependency_text = sources.process_dependencies(object_dependencies)

    print('\nGenerating makefile text... ', end='')

    pure_output_name, current_time, compiler, \
        output_name, object_files, compilation_flags, \
        linking_flags, header_path_flags, library_link_flags, \
        library_path_flags, debug_flags, fast_flags, \
        compile_rule_string, delete_cmd, delete_trail, \
        help_text = makemake_lib.get_common_makefile_parameters(manager,
                                                                sources,
                                                                'g++',
                                                                'mpicxx')

    # Create makefile
    if manager.library and not manager.library_is_shared:

        # Static library

        makefile = '''#@{}
# This makefile was generated by makemake.py ({}).
# GitHub repository: https://github.com/lars-frogner/makemake.py
#
# Usage:
# make <argument 1> <argument 2> ...
#
# Arguments:
# <none>:  Compiles with no compiler flags.
# debug:   Compiles with flags useful for debugging.
# fast:    Compiles with flags for high performance.
# clean:   Deletes auxiliary files.
# help:    Displays this help text.
#
# To compile with additional flags, add the argument
# EXTRA_FLAGS="<flags>"

# Define variables
COMPILER = {}
LIBRARY = {}
OBJECT_FILES = {}
COMPILATION_FLAGS = {}
DEBUGGING_FLAGS = {}
PERFORMANCE_FLAGS = {}
HEADER_PATH_FLAGS = {}

# Make sure certain rules are not activated by the presence of files
.PHONY: all debug fast profile set_debug_flags set_fast_flags clean help

# Define default target group
all: $(LIBRARY)

# Define optional target groups
debug: set_debug_flags $(LIBRARY)
fast: set_fast_flags $(LIBRARY)

# Defines appropriate compiler flags for debugging
set_debug_flags:
\t$(eval COMPILATION_FLAGS = $(COMPILATION_FLAGS) $(DEBUGGING_FLAGS))

# Defines appropriate compiler flags for high performance
set_fast_flags:
\t$(eval COMPILATION_FLAGS = $(COMPILATION_FLAGS) $(PERFORMANCE_FLAGS))

# Rule for linking object files
$(LIBRARY): $(OBJECT_FILES)
\tar rcs $(LIBRARY) $(OBJECT_FILES){}

# Action for removing all auxiliary files
clean:
\t{} $(OBJECT_FILES){}

# Action for printing help text
help:
\t@echo {}''' \
    .format(pure_output_name,
            current_time,
            compiler,
            output_name,
            object_files,
            compilation_flags,
            debug_flags,
            fast_flags,
            header_path_flags,
            compile_rule_string,
            delete_cmd,
            delete_trail,
            help_text)

    elif manager.library:

        # Shared library

        makefile = '''#@{}
# This makefile was generated by makemake.py ({}).
# GitHub repository: https://github.com/lars-frogner/makemake.py
#
# Usage:
# make <argument 1> <argument 2> ...
#
# Arguments:
# <none>:  Compiles with no compiler flags.
# debug:   Compiles with flags useful for debugging.
# fast:    Compiles with flags for high performance.
# clean:   Deletes auxiliary files.
# help:    Displays this help text.
#
# To compile with additional flags, add the argument
# EXTRA_FLAGS="<flags>"

# Define variables
COMPILER = {}
LIBRARY = {}
OBJECT_FILES = {}
COMPILATION_FLAGS = {}
LINKING_FLAGS = {}
DEBUGGING_FLAGS = {}
PERFORMANCE_FLAGS = {}
HEADER_PATH_FLAGS = {}
LIBRARY_LINKING_FLAGS = {}
LIBRARY_PATH_FLAGS = {}

# Make sure certain rules are not activated by the presence of files
.PHONY: all debug fast profile set_debug_flags set_fast_flags clean help

# Define default target group
all: $(LIBRARY)

# Define optional target groups
debug: set_debug_flags $(LIBRARY)
fast: set_fast_flags $(LIBRARY)

# Defines appropriate compiler flags for debugging
set_debug_flags:
\t$(eval COMPILATION_FLAGS = $(COMPILATION_FLAGS) $(DEBUGGING_FLAGS))

# Defines appropriate compiler flags for high performance
set_fast_flags:
\t$(eval COMPILATION_FLAGS = $(COMPILATION_FLAGS) $(PERFORMANCE_FLAGS))

# Rule for linking object files
$(LIBRARY): $(OBJECT_FILES)
\t$(COMPILER) $(EXTRA_FLAGS) $(LINKING_FLAGS) $(OBJECT_FILES) $(LIBRARY_PATH_FLAGS) $(LIBRARY_LINKING_FLAGS) -o $(LIBRARY){}

# Action for removing all auxiliary files
clean:
\t{} $(OBJECT_FILES){}

# Action for printing help text
help:
\t@echo {}''' \
    .format(pure_output_name,
            current_time,
            compiler,
            output_name,
            object_files,
            compilation_flags,
            linking_flags,
            debug_flags,
            fast_flags,
            header_path_flags,
            library_link_flags,
            library_path_flags,
            compile_rule_string,
            delete_cmd,
            delete_trail,
            help_text)

    else:

        # Executable

        makefile = '''#@{}
# This makefile was generated by makemake.py ({}).
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
# EXTRA_FLAGS="<flags>"

# Define variables
COMPILER = {}
EXECUTABLE = {}
OBJECT_FILES = {}
COMPILATION_FLAGS = {}
LINKING_FLAGS = {}
DEBUGGING_FLAGS = {}
PERFORMANCE_FLAGS = {}
PROFILING_FLAGS = -pg
HEADER_PATH_FLAGS = {}
LIBRARY_LINKING_FLAGS = {}
LIBRARY_PATH_FLAGS = {}

# Make sure certain rules are not activated by the presence of files
.PHONY: all debug fast profile set_debug_flags set_fast_flags set_profile_flags clean gprof help

# Define default target group
all: $(EXECUTABLE)

# Define optional target groups
debug: set_debug_flags $(EXECUTABLE)
fast: set_fast_flags $(EXECUTABLE)
profile: set_profile_flags $(EXECUTABLE)

# Defines appropriate compiler flags for debugging
set_debug_flags:
\t$(eval COMPILATION_FLAGS = $(COMPILATION_FLAGS) $(DEBUGGING_FLAGS))

# Defines appropriate compiler flags for high performance
set_fast_flags:
\t$(eval COMPILATION_FLAGS = $(COMPILATION_FLAGS) $(PERFORMANCE_FLAGS))

# Defines appropriate compiler flags for profiling
set_profile_flags:
\t$(eval COMPILATION_FLAGS = $(COMPILATION_FLAGS) $(PROFILING_FLAGS))
\t$(eval LINKING_FLAGS = $(LINKING_FLAGS) $(PROFILING_FLAGS))

# Rule for linking object files
$(EXECUTABLE): $(OBJECT_FILES)
\t$(COMPILER) $(EXTRA_FLAGS) $(LINKING_FLAGS) $(OBJECT_FILES) $(LIBRARY_PATH_FLAGS) $(LIBRARY_LINKING_FLAGS) -o $(EXECUTABLE){}

# Action for removing all auxiliary files
clean:
\t{} $(OBJECT_FILES){}

# Action for reading profiling results
gprof:
\tgprof $(EXECUTABLE)

# Action for printing help text
help:
\t@echo {}''' \
    .format(pure_output_name,
            current_time,
            compiler,
            output_name,
            object_files,
            compilation_flags,
            linking_flags,
            debug_flags,
            fast_flags,
            header_path_flags,
            library_link_flags,
            library_path_flags,
            compile_rule_string,
            delete_cmd,
            delete_trail,
            help_text)

    print('Done')

    print(dependency_text)

    writer = makemake_lib.file_writer(manager.working_dir_path)
    writer.save_makefile(makefile, pure_output_name)


def abort_multiple_producers(function):

    print('Error: function \"{}\" implemented multiple times'.format(function))
    sys.exit(1)


def determine_object_dependencies(source_instances, header_instances):

    # This function creates a dictionary with the cpp_source instances
    # as keys. The values are lists of cpp_source instances for the other
    # sources that implement functions that the source uses.

    print('Determining object dependencies...', end='')

    # Create a dictionary of all headers containing the sources that
    # include each header.

    header_source_dependencies = {}

    for header in header_instances:

        header_source_dependencies[header] = []

        for source in source_instances:

            if header.filename in source.included_headers:
                header_source_dependencies[header].append(source)

    # Create a dictionary of headers containing the functions that each
    # header declares. Each function is a key to a dictionary containing
    # a list of the sources that implement the function ("producers")
    # and a list of the sources that call the function ("consumers").

    producer_consumer_dict = {}

    for header in header_instances:

        producer_consumer_dict[header] = {}

        for function in header.declared_functions + header.declared_methods:

            producer_consumer_dict[header][function] = {}
            producer_consumer_dict[header][function]['producers'] = []
            producer_consumer_dict[header][function]['consumers'] = []

            for source in header_source_dependencies[header]:

                text = re.sub(r'\s*::\s*', '::', source.clean_text)

                # Split source text at the function name
                func_splitted = text.split(function + '(')

                if len(func_splitted) < 2:
                    continue

                is_producer = False
                is_consumer = False

                # Loop through all substrings following a function name
                for substring in func_splitted[1:]:

                    # Find the character following the parantheses after the
                    # function name.

                    paran_splitted = substring.split(')')

                    if len(paran_splitted) < 2:
                        continue

                    idx = 0

                    for element in paran_splitted:

                        if '(' in element:
                            idx += 1
                        else:
                            break

                    character_after = paran_splitted[idx+1].strip()
                    if len(character_after) > 0:
                        character_after = character_after[0]

                    # If the next character is a curly bracket or colon, the function is implmented
                    if character_after in ['{', ':']:

                        is_producer = True

                    # Otherwise, the function is called
                    else:

                        is_consumer = True

                if is_producer and not is_consumer:

                    producer_consumer_dict[header][function]['producers']\
                        .append(source)

                elif is_consumer and not is_producer:

                    producer_consumer_dict[header][function]['consumers']\
                        .append(source)

    # Make sure that no function was implemented multiple times
    for header in header_instances:

        for function in producer_consumer_dict[header]:

            n_producers = len(producer_consumer_dict[header][function]['producers'])

            if n_producers > 1:
                abort_multiple_producers(function)

    # Convert the dictionary of producers and consumers into a dictionary
    # of sources, where the values are the source instances of the producers
    # for the functions that the source uses.

    object_dependencies = {}

    for source in source_instances:

        object_dependencies[source] = []

        for header in header_instances:

            for function in producer_consumer_dict[header]:

                for consumer in producer_consumer_dict[header][function]['consumers']:

                    if source is consumer:

                        if len(producer_consumer_dict[header][function]['producers']) > 0:

                            producer_source = producer_consumer_dict[header][function]['producers'][0]
                            object_dependencies[source].append(producer_source)

                            if producer_source.filename in source.dependency_descripts:
                                source.dependency_descripts[producer_source.filename] \
                                    += ', {}()'.format(function)
                            else:
                                source.dependency_descripts[producer_source.filename] \
                                    = 'through {}()'.format(function)

                        break

        object_dependencies[source] = makemake_lib.remove_duplicates(object_dependencies[source])

    print('Done')

    return object_dependencies
