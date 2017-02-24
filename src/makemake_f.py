#
# This program contains a function for generating a makefile from a
# list of Fortran source files.
#
# State: Functional
#
# Last modified 24.02.2017 by Lars Frogner
#
import sys
import os
import makemake_lib


class fortran_source:

    # This class extracts relevant information from a Fortran source
    # file and stores it in class attributes.

    def __init__(self, filename_with_path, is_header=False):

        self.filename_with_path = filename_with_path
        self.is_header = is_header

        self.filename = filename_with_path.split(os.sep)[-1]
        self.name = '.'.join(self.filename.split('.')[:-1])
        self.object_name = self.name + '.o'

        print('Parsing... ', end='')

        f = open(filename_with_path, 'r')
        self.lines = f.readlines()
        f.close()

        self.programs, self.modules, self.external_functions, self.external_subroutines, \
            self.module_dependencies, self.included_headers, self.procedure_dependencies, \
            self.library_usage = self.parse_content()

        if len(self.programs) > 1:
            self.abort_multiple_programs()

        self.is_main = len(self.programs) > 0
        self.program_name = '' if not self.is_main else self.programs[0]
        self.executable_name = self.program_name + ('.exe' if sys.platform == 'win32' else '.x')

        self.dependency_descripts = {}

        for header_name in self.included_headers:
            self.dependency_descripts[header_name] = 'included directly'

        print('Done')

        if self.is_main:
            print('Contained programs:\n-' + self.program_name)

        if len(self.modules) > 0:
            print('Contained modules:\n' +
                  '\n'.join(['-{}'.format(module_name.split('.')[0])
                             for module_name in self.modules]))

        if len(self.external_functions) > 0:
            print('Contained external functions:\n' +
                  '\n'.join(['-{}'.format(procedure_name)
                             for procedure_name in self.external_functions]))

        if len(self.external_subroutines) > 0:
            print('Contained external subroutines:\n' +
                  '\n'.join(['-{}'.format(procedure_name)
                             for procedure_name in self.external_subroutines]))

        if len(self.module_dependencies) > 0:
            print('Used modules:\n' +
                  '\n'.join(['-{}'.format(module_name.split('.')[0])
                             for module_name in self.module_dependencies]))

        if len(self.procedure_dependencies) > 0:
            print('Used external procedures:\n' +
                  '\n'.join(['-{}'.format(procedure_name)
                             for procedure_name in self.procedure_dependencies]))

        if len(self.included_headers) > 0:
            print('Included headers:\n' +
                  '\n'.join(['-{}'.format(header_name)
                             for header_name in self.included_headers]))

        if self.library_usage['mpi']:
            print('Uses MPI')

        if self.library_usage['openmp']:
            print('Uses OpenMP')

        module_list = ' '.join(self.modules)
        module_del_list = module_list
        module_dep_list = ' '.join(self.module_dependencies)
        delete_cmd = 'del /F' if sys.platform == 'win32' else 'rm -f'
        delete_trail = ' 2>nul' if sys.platform == 'win32' else ''
        delete_text = ''

        if len(self.modules) > 0:

            module_list = ' ' + module_list
            delete_text = '\t{} {}{}\n'.format(delete_cmd, module_del_list, delete_trail)

        if len(self.module_dependencies) > 0:
            module_dep_list = ' ' + module_dep_list

        # Compilation rule for the makefile
        self.compile_rule_declr = '\n\n{}\n{}{}: {}{} '\
                                  .format('# Rule for compiling ' + self.filename,
                                          self.object_name,
                                          module_list,
                                          filename_with_path.replace(' ', '\ '),
                                          module_dep_list)

        self.compile_rule = '\n{}\t$(COMPILER) -c $(EXTRA_FLAGS) $(COMPILATION_FLAGS) \"{}\"' \
                            .format(delete_text, filename_with_path)

    def parse_content(self):

        # This function parses the source code lines and extracts
        # information about the content of the source files.

        programs = []
        modules = []
        external_functions = []
        external_subroutines = []
        module_dependencies = []
        included_headers = []
        procedure_dependencies = []

        library_usage = {'mpi': False, 'openmp': False}

        prev_line = ''
        inside = False
        unknown_in_or_out = self.is_header

        # Parse source file
        for line in self.lines:

            # Ignore everything after "!"
            words = (prev_line + line).split('!')[0]

            # Skip blank lines
            if len(words.split()) == 0:
                continue

            # Skip commented lines
            if words[0][0] in ['c', 'C', '*']:
                continue

            # If line is continued
            if words.strip()[-1] == '&':

                # Save this line and continue to next one
                prev_line = words.split('&')[0] + ' '
                continue

            else:
                prev_line = ''

            words = words.replace(',', ' ')      # Treat "," as word separator
            words = words.replace('::', ' :: ')  # Ensure separation at "::"

            words_with_case = words.split()
            words = [word.lower() for word in words_with_case]

            n_words = len(words)

            first_word = words[0]
            second_word = '' if n_words < 2 else words[1]

            # External scope declarations
            if not inside or unknown_in_or_out:

                # Check for program declaration
                if first_word == 'program':

                    programs.append(words_with_case[1])
                    inside = 'program'
                    unknown_in_or_out = False

                # Check for module declaration
                elif first_word == 'module':

                    modules.append(second_word + '.mod')
                    inside = 'module'
                    unknown_in_or_out = False

                # Check for include statement
                elif first_word == 'include' or first_word == '#include':

                    dep = words_with_case[1][1:-1]

                    if dep == 'mpif.h':
                        library_usage['mpi'] = True
                    elif dep == 'omp_lib.h':
                        library_usage['openmp'] = True
                    else:
                        included_headers.append(dep)

                # Check for external function declaration
                elif 'function' in words:

                    idx = words.index('function')

                    if n_words > idx + 1:

                        external_functions.append(words[idx + 1].split('(')[0])
                        inside = 'function'
                        unknown_in_or_out = False

                # Check for external subroutine declaration
                elif 'subroutine' in words:

                    idx = words.index('subroutine')

                    if n_words > idx + 1:

                        external_subroutines.append(words[idx + 1].split('(')[0])
                        inside = 'subroutine'
                        unknown_in_or_out = False

            # Internal scope declarations
            if inside or unknown_in_or_out:

                # Check for module import statement
                if first_word == 'use':

                    deps = words[1:]

                    for dep in deps:

                        if dep == 'mpi' or dep == 'mpi_f08':
                            library_usage['mpi'] = True
                        elif dep == 'omp_lib':
                            library_usage['openmp'] = True
                        else:
                            module_dependencies.append(dep + '.mod')

                    unknown_in_or_out = False

                # Check for include statement
                elif first_word == 'include' or first_word == '#include':

                    dep = words_with_case[1][1:-1]

                    if dep == 'mpif.h':
                        library_usage['mpi'] = True
                    elif dep == 'omp_lib.h':
                        library_usage['openmp'] = True
                    else:
                        included_headers.append(dep)

                # Check for end of external scope
                elif first_word == 'end' and \
                     (second_word == inside or second_word == ''):

                    inside = False
                    unknown_in_or_out = False

                # Check for declaration of external procedure
                elif 'external' in words:

                    ext_idx = words.index('external')

                    if '::' in words:

                        sep_idx = words.index('::')
                        procedure_dependencies += words[sep_idx+1:]

                    else:
                        procedure_dependencies += words[ext_idx+1:]

                    unknown_in_or_out = False

        # Ignore dependencies on modules and procedures in the same file

        for dep in list(module_dependencies):
            if dep in modules:
                module_dependencies.remove(dep)

        for dep in list(procedure_dependencies):
            if dep in external_functions + external_subroutines:
                procedure_dependencies.remove(dep)

        module_dependencies = list(set(module_dependencies))
        procedure_dependencies = list(set(procedure_dependencies))
        included_headers = list(set(included_headers))

        return programs, modules, external_functions, external_subroutines, \
            module_dependencies, included_headers, procedure_dependencies, library_usage

    def detect_procedure_calls(self, functions_to_detect, subroutines_to_detect):

        # This function parses the source code lines and returns which of
        # the given procedures are called.

        detected_procedure_calls = []

        prev_line = ''
        inside = False
        unknown_in_or_out = self.is_header

        # Parse source file
        for line in self.lines:

            # Ignore everything after "!"
            words = (prev_line + line).split('!')[0]

            # Skip blank lines
            if len(words.split()) == 0:
                continue

            # Skip commented lines
            if words[0][0] in ['c', 'C', '*']:
                continue

            # If line is continued
            if words.strip()[-1] == '&':

                # Save this line and continue to next one
                prev_line = words.split('&')[0] + ' '
                continue

            else:
                prev_line = ''

            words = words.replace(',', ' ')      # Treat "," as word separator
            words = words.replace('::', ' :: ')  # Ensure separation at "::"

            words = [word.lower() for word in words.split()]

            n_words = len(words)

            first_word = words[0]
            second_word = '' if n_words < 2 else words[1]

            # External scope declarations
            if not inside or unknown_in_or_out:

                # Check for program declaration
                if first_word == 'program':

                    inside = 'program'
                    unknown_in_or_out = False

                # Check for module declaration
                elif first_word == 'module':

                    inside = 'module'
                    unknown_in_or_out = False

                # Check for external function declaration
                elif 'function' in words:

                    idx = words.index('function')

                    if n_words > idx + 1:

                        inside = 'function'
                        unknown_in_or_out = False

                # Check for external subroutine declaration
                elif 'subroutine' in words:

                    idx = words.index('subroutine')

                    if n_words > idx + 1:

                        inside = 'subroutine'
                        unknown_in_or_out = False

            # Internal scope declarations
            if inside or unknown_in_or_out:

                # Check for module import statement
                if first_word == 'use':

                    unknown_in_or_out = False

                # Check for end of external scope
                elif first_word == 'end' and \
                     (second_word == inside or second_word == ''):

                    inside = False
                    unknown_in_or_out = False

                else:

                    # Check for declaration of external procedure
                    if 'external' in words:

                        unknown_in_or_out = False

                    elif len(functions_to_detect) > 0 or \
                         len(subroutines_to_detect) > 0:

                        joined_words = ' '.join(words).replace('\'', '\"')
                        joined_words = ''.join(joined_words.split('\"')[::2])

                        found_procedure_call = False

                        for function in list(functions_to_detect):

                            function_splitted = joined_words.split(function)

                            if len(function_splitted) > 1:

                                before = function_splitted[0]
                                stripped = function_splitted[1].strip()

                                if len(stripped) > 0 and \
                                   stripped[0] == '(' and \
                                   (len(before) == 0 or not (before[-1] in
                                                             ['abcdefghijklmnopqrstuvwxyz_'])):

                                    detected_procedure_calls.append(function)
                                    functions_to_detect.remove(function)
                                    found_procedure_call = True

                        if not found_procedure_call:

                            for subroutine in list(subroutines_to_detect):

                                subroutine_splitted = joined_words.split(subroutine)

                                if len(subroutine_splitted) > 1:

                                    splitted = subroutine_splitted[0].split()
                                    stripped = subroutine_splitted[1].strip()

                                    if len(stripped) > 0 and stripped[0] == '(' and \
                                       len(splitted) > 0 and splitted[-1] == 'call':

                                        detected_procedure_calls.append(subroutine)
                                        subroutines_to_detect.remove(subroutine)

        return detected_procedure_calls

    def abort_multiple_programs(self):

        print('\nError: multiple programs in \"{}\" ({})'
              .format(self.filename, ', '.join(self.programs)))

        sys.exit(1)

    def update_source_information(self, header):

        # This function updates the source information based on the
        # information about a given included header.

        if header.is_main:

            if self.is_main:

                self.programs.append(header.program_name)
                self.abort_multiple_programs()

            else:
                self.program_name = header.program_name
                self.executable_name = header.executable_name

        for included_header in header.included_headers:

            if included_header not in self.included_headers:

                self.included_headers.append(included_header)
                self.dependency_descripts[included_header] = \
                    'included indirectly through {}'\
                    .format(header.filename)

        for mod in header.modules:

            if mod not in self.modules:

                self.modules.append(mod)

        for func in header.external_functions:

            if func not in self.external_functions:

                self.external_functions.append(func)

        for sub in header.external_subroutines:

            if sub not in self.external_subroutines:

                self.external_subroutines.append(sub)

        for mod_dep in header.module_dependencies:

            if mod_dep not in self.module_dependencies:

                self.module_dependencies.append(mod_dep)

        for proc_dep in header.procedure_dependencies:

            if proc_dep not in self.procedure_dependencies:

                self.procedure_dependencies.append(proc_dep)


class fortran_header(fortran_source):

    def __init__(self, filename_with_path):

        super().__init__(filename_with_path, is_header=True)


def generate_makefile(manager, sources):

    # This function generates a makefile for compiling the program
    # given by the supplied fortran_source instances.

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

    all_modules = check_dependency_presence(sources.source_instances)
    object_dependencies = determine_object_dependencies(sources.source_instances)

    dependency_text = sources.process_dependencies(object_dependencies)

    print('\nGenerating makefile text... ', end='')

    pure_output_name, current_time, compiler, \
        output_name, object_files, compilation_flags, \
        linking_flags, header_path_flags, library_link_flags, \
        library_path_flags, debug_flags, fast_flags, \
        compile_rule_string, delete_cmd, delete_trail, \
        help_text = makemake_lib.get_common_makefile_parameters(manager,
                                                                sources,
                                                                'gfortran',
                                                                'mpifort')

    module_files = ' '.join(all_modules)

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
MODULE_FILES = {}
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
\t{} $(OBJECT_FILES) $(MODULE_FILES){}

# Action for printing help text
help:
\t@echo {}''' \
    .format(pure_output_name,
            current_time,
            compiler,
            output_name,
            object_files,
            module_files,
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
MODULE_FILES = {}
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
\t{} $(OBJECT_FILES) $(MODULE_FILES){}

# Action for printing help text
help:
\t@echo {}''' \
    .format(pure_output_name,
            current_time,
            compiler,
            output_name,
            object_files,
            module_files,
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
MODULE_FILES = {}
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
\t{} $(OBJECT_FILES) $(MODULE_FILES){}

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
            module_files,
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


def check_dependency_presence(source_instances):

    # This function makes sure that all dependencies are present,
    # and that no modules or procedures are implemented multiple
    # times. It also returns a complete list of all modules.

    print('Making sure required sources are present... ', end='')

    all_modules = []
    all_external_functions = []
    all_external_subroutines = []

    for source in source_instances:

        all_modules += source.modules
        all_external_functions += source.external_functions
        all_external_subroutines += source.external_subroutines

    for module in all_modules:

        source_list = []

        for source in source_instances:

            if module in source.modules:
                source_list.append(source.filename)

        if len(source_list) > 1:

            print()
            makemake_lib.abort_multiple_something('modules',
                                                  module.split('.')[0],
                                                  name_list=source_list)

    for external_function in all_external_functions:

        source_list = []

        for source in source_instances:

            if external_function in source.external_functions:
                source_list.append(source.filename)

        if len(source_list) > 1:

            print()
            makemake_lib.abort_multiple_something('external functions',
                                                  module.split('.')[0],
                                                  name_list=source_list)

    for external_subroutine in all_external_subroutines:

        source_list = []

        for source in source_instances:

            if external_subroutine in source.external_subroutines:
                source_list.append(source.filename)

        if len(source_list) > 1:

            print()
            makemake_lib.abort_multiple_something('external subroutines',
                                                  module.split('.')[0],
                                                  name_list=source_list)

    for source in source_instances:

        for module_dep in source.module_dependencies:

            found = False

            for module in all_modules:

                if module_dep == module:

                    found = True
                    break

            if not found:

                print()
                makemake_lib.abort_missing_something('module',
                                                     source.filename,
                                                     module_dep.split('.')[0])

        for procedure_dep in source.procedure_dependencies:

            found = False

            for procedure in all_external_functions + all_external_subroutines:

                if procedure_dep == procedure:

                    found = True
                    break

            if not found:

                print()
                makemake_lib.abort_missing_something('procedure',
                                                     source.filename,
                                                     procedure_dep)

    print('Done')

    return all_modules


def determine_object_dependencies(source_instances):

    # This function creates a dictionary with the fortran_source instances
    # as keys. The values are lists of fortran_source instances for the other
    # sources that implement modules and procedures that the source uses.

    print('Finding external procedure dependencies... ', end='')

    for source in source_instances:

        functions_to_detect = source.external_functions
        subroutines_to_detect = source.external_subroutines

        for other_source in source_instances:

            if other_source is not source:

                functions_to_detect_filtered = []
                subroutines_to_detect_filtered = []

                for func in functions_to_detect:

                    if func not in other_source.procedure_dependencies:

                        functions_to_detect_filtered.append(func)

                for sub in subroutines_to_detect:

                    if sub not in other_source.procedure_dependencies:

                        subroutines_to_detect_filtered.append(sub)

                detected_procedure_calls = other_source.detect_procedure_calls(
                                                            functions_to_detect_filtered,
                                                            subroutines_to_detect_filtered
                                                                              )

                other_source.procedure_dependencies += detected_procedure_calls

    print('Done')

    print('Determining object dependencies... ', end='')

    object_dependencies = {}

    # For each source
    for source in source_instances:

        object_dependencies[source] = []

        # For each module dependency the source has
        for module in source.module_dependencies:

            # Loop through all the other sources
            for other_source in source_instances:

                if other_source is not source:

                    # Add source instance if it has the correct module
                    if module in other_source.modules:

                        object_dependencies[source].append(other_source)

                        if other_source.filename in source.dependency_descripts:
                            source.dependency_descripts[other_source.filename] \
                                += ', ' + module
                        else:
                            source.dependency_descripts[other_source.filename] \
                                = 'through ' + module

        # Repeat for procedure dependencies
        for procedure in source.procedure_dependencies:

            for other_source in source_instances:

                if other_source is not source:

                    if procedure in (other_source.external_functions +
                                     other_source.external_subroutines):

                        object_dependencies[source].append(other_source)

                        if other_source.filename in source.dependency_descripts:
                            source.dependency_descripts[other_source.filename] \
                                += ', {}()'.format(procedure)
                        else:
                            source.dependency_descripts[other_source.filename] \
                                = 'through {}()'.format(procedure)

        # Get rid of duplicate instances
        object_dependencies[source] = list(set(object_dependencies[source]))

    print('Done')

    return object_dependencies
