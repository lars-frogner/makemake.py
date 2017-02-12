#
# This program contains a function for generating a makefile from a
# list of Fortran source files.
#
# State: Functional
#
# Last modified 10.02.2017 by Lars Frogner
#
import sys, os
import makemake_lib

def abort_multiple_programs(filename, programs):

    print '\nError: multiple programs in \"%s\" (%s)' % (filename, ', '.join(programs))
    sys.exit(1)

def parse_lines(lines, is_header=False, functions_to_detect=[], subroutines_to_detect=[]):

    # This function parses the given list of source code lines and
    # returns information about the content of the source files.

    programs = []
    modules = []
    external_functions = []
    external_subroutines = []
    module_dependencies = []
    included_headers = []
    procedure_dependencies = []

    detected_procedure_calls = []

    use_mpi = False
    use_openmp = False

    prev_line = ''
    inside = False
    unknown_in_or_out = is_header

    # Parse source file
    for line in lines:

        words = (prev_line + line).split('!')[0] # Ignore everything after "!"

        # Skip blank lines
        if len(words.split()) == 0: continue

        # Skip commented lines
        if words[0][0] in ['c', 'C', '*']: continue

        # If line is continued
        if words.strip()[-1] == '&': 

            # Save this line and continue to next one
            prev_line = words.split('&')[0] + ' '
            continue

        else:
            prev_line = ''

        words = words.replace(',', ' ')                    # Treat "," as word separator
        words = words.replace('::', ' :: ')                # Ensure separation at "::"
        words_with_case = words.split()
        words = [word.lower() for word in words_with_case] # List of words in lowercase

        n_words = len(words)

        first_word = words[0]
        second_word = '' if n_words < 2 else words[1]
        third_word = '' if n_words < 3 else words[2]

        # External scope declarations
        if not inside or unknown_in_or_out:

            # Check for program declaration
            if first_word == 'program':

                programs.append(second_word)
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
                    use_mpi = True
                elif dep == 'omp_lib.h':
                    use_openmp = True
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
                        use_mpi = True
                    elif dep == 'omp_lib':
                        use_openmp = True
                    else:
                        module_dependencies.append(dep + '.mod')

                unknown_in_or_out = False

            # Check for include statement
            elif first_word == 'include' or first_word == '#include':

                dep = words_with_case[1][1:-1]

                if dep == 'mpif.h':
                    use_mpi = True
                elif dep == 'omp_lib.h':
                    use_openmp = True
                else:
                    included_headers.append(dep)

            # Check for end of external scope
            elif first_word == 'end' and (second_word == inside or second_word == ''):

                inside = False
                unknown_in_or_out = False

            else:

                # Check for declaration of external procedure
                if 'external' in words:

                    ext_idx = words.index('external')

                    if '::' in words:

                        sep_idx = words.index('::')
                        procedure_dependencies += words[sep_idx+1:]

                    else:
                        procedure_dependencies += words[ext_idx+1:]

                    unknown_in_or_out = False

                elif len(functions_to_detect) > 0 or len(subroutines_to_detect) > 0:

                    joined_words = ' '.join(words).replace('\'', '\"')
                    joined_words = ''.join(joined_words.split('\"')[::2])

                    found_procedure_call = False

                    for function in list(functions_to_detect):

                        function_splitted = joined_words.split(function)

                        if len(function_splitted) > 1:

                            before = subroutine_splitted[0]
                            stripped = function_splitted[1].strip()

                            if len(stripped) > 0 and stripped[0] == '(' and (len(before) == 0 or not (before[-1] in ['abcdefghijklmnopqrstuvwxyz_'])):

                                detected_procedure_calls.append(function)
                                functions_to_detect.remove(function)
                                found_procedure_call = True

                    if not found_procedure_call:

                        for subroutine in list(subroutines_to_detect):

                            subroutine_splitted = joined_words.split(subroutine)

                            if len(subroutine_splitted) > 1:

                                splitted = subroutine_splitted[0].split()
                                stripped = subroutine_splitted[1].strip()

                                if len(stripped) > 0 and stripped[0] == '(' and len(splitted) > 0 and splitted[-1] == 'call':

                                    detected_procedure_calls.append(subroutine)
                                    subroutines_to_detect.remove(subroutine)

    # Ignore dependencies on modules and procedures in the same file

    for dep in list(module_dependencies):
        if dep in modules: module_dependencies.remove(dep)

    for dep in list(procedure_dependencies):
        if dep in external_functions + external_subroutines: procedure_dependencies.remove(dep)

    module_dependencies = list(set(module_dependencies))
    procedure_dependencies = list(set(procedure_dependencies))
    included_headers = list(set(included_headers))

    return programs, modules, external_functions, external_subroutines, module_dependencies, procedure_dependencies, included_headers, use_mpi, use_openmp, detected_procedure_calls

class fortran_source:

    # This class parses an inputted Fortran file and stores information
    # about which programs, modules, external procedures and 
    # dependencies it contains.

    def __init__(self, filename_with_path, is_header=False):

        self.filename_with_path = filename_with_path

        file_path = '/'.join(filename_with_path.split('/')[:-1])

        self.filename = filename_with_path.split('/')[-1]
        self.name = '.'.join(self.filename.split('.')[:-1])
        self.object_name = self.name + '.o'

        sys.stdout.write('Parsing ...')
        sys.stdout.flush()

        f = open(filename_with_path, 'r')
        self.lines = f.readlines()
        f.close()

        programs, self.modules, self.external_functions, self.external_subroutines, self.module_dependencies, self.procedure_dependencies, self.included_headers, self.use_mpi, self.use_openmp = parse_lines(self.lines, is_header=is_header)[:-1]

        self.main_program = False if len(programs) == 0 else programs[0]
        if len(programs) > 1: abort_multiple_programs(self.filename, programs)

        print ' Done'

        if self.main_program:
            print 'Contained programs:\n-' + self.main_program

        if len(self.modules) > 0:
            print 'Contained modules:\n' + '\n'.join([('-%s' % module_name.split('.')[0]) for module_name in self.modules])

        if len(self.external_functions) > 0:
            print 'Contained external functions:\n' + '\n'.join([('-%s' % procedure_name) for procedure_name in self.external_functions])

        if len(self.external_subroutines) > 0:
            print 'Contained external subroutines:\n' + '\n'.join([('-%s' % procedure_name) for procedure_name in self.external_subroutines])

        if len(self.module_dependencies) > 0:
            print 'Used modules:\n' + '\n'.join([('-%s' % module_name.split('.')[0]) for module_name in self.module_dependencies])

        if len(self.procedure_dependencies) > 0:
            print 'Used external procedures:\n' + '\n'.join([('-%s' % procedure_name) for procedure_name in self.procedure_dependencies])

        if len(self.included_headers) > 0:
            print 'Included headers:\n' + '\n'.join([('-%s' % header_name) for header_name in self.included_headers])

        if self.use_mpi:
            print 'Uses MPI'

        if self.use_openmp:
            print 'Uses OpenMP'

        # Compilation rule for the makefile
        self.compile_rule_declr = '\n\n%s\n%s%s: %s%s ' \
                                  % ('# Rule for compiling ' + self.filename,
                                     self.object_name,
                                     (' ' if len(self.modules) != 0 else '') + ' '.join(self.modules), 
                                     filename_with_path.replace(' ', '\ '),
                                     (' ' if len(self.module_dependencies) != 0 else '') + ' '.join(self.module_dependencies))

        self.compile_rule = '\n%s\t$(COMP) -c $(COMP_FLAGS) $(MPI_COMP_FLAGS) $(FLAGS) \"%s\"' \
                            % (('\trm -f %s\n' % (' '.join(self.modules))) if len(self.modules) != 0 else '', 
                               filename_with_path)

def process_headers(working_dir_path, header_paths, header_files, abort_on_fail=True):

    # This function creates a list of fortran_source header instances 
    # from the given lists of filenames and paths.

    header_objects = []
    extra_header_paths = []

    for file_string in header_files:

        found, filename_with_path, has_determined_path, determined_path = makemake_lib.search_for_file(file_string, 
                                                                                                       working_dir_path, 
                                                                                                       header_paths,
                                                                                                       abort_on_fail=abort_on_fail)[:4]
        if found:

            header_objects.append(fortran_source(filename_with_path, is_header=True))

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

def process_files(working_dir_path, source_paths, header_paths, source_files, header_files):

    # This function creates a list of fortran_source instances from the given 
    # lists of filenames and paths, and also returns a list of fortran_header
    # instances produced by the process_headers() function.

    # Process header files

    header_objects, extra_header_paths = process_headers(working_dir_path, header_paths, header_files)

    # Process source files

    source_objects = []

    for file_string in source_files:

        filename_with_path = makemake_lib.search_for_file(file_string, 
                                                          working_dir_path, 
                                                          source_paths)[1]

        source_objects.append(fortran_source(filename_with_path))

    # Add missing headers

    header_paths, header_objects = find_missing_headers(working_dir_path, header_paths, source_objects, header_objects)

    header_paths = list(set(header_paths + extra_header_paths))

    return source_objects, header_paths, header_objects

def determine_header_dependencies(source_objects, header_objects):

    # This function creates a dictionary with the fortran_source 
    # objects as keys. The values are lists of paths to the headers 
    # that the source depends on.

    # Find all headers that each header includes

    sys.stdout.write('Finding header dependencies...')
    sys.stdout.flush()

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

                            if other_header.main_program:

                                if source.main_program:
                                    abort_multiple_programs(source.filename, [source.main_program, other_header.main_program])
                                else:
                                    source.main_program = other_header.main_program

                            for mod in other_header.modules:

                                if not mod in source.modules:

                                    source.modules.append(mod)

                            for func in other_header.external_functions:

                                if not func in source.external_functions:

                                    source.external_functions.append(func)

                            for sub in other_header.external_subroutines:

                                if not sub in source.external_subroutines:

                                    source.external_subroutines.append(sub)

                            for mod_dep in other_header.module_dependencies:

                                if not mod_dep in source.module_dependencies:

                                    source.module_dependencies.append(mod_dep)

                            for proc_dep in other_header.procedure_dependencies:

                                if not proc_dep in source.procedure_dependencies:

                                    source.procedure_dependencies.append(proc_dep)

                    break

    print ' Done'

    return source_header_dependencies

def check_dependencies_presence(source_objects):

    # This function makes sure that all dependencies are present,
    # and that no modules or procedures are implemented multiple
    # times.

    sys.stdout.write('Making sure required sources are present...')
    sys.stdout.flush()

    all_modules = []
    all_external_functions = []
    all_external_subroutines = []

    for source in source_objects:

        all_modules += source.modules
        all_external_functions += source.external_functions
        all_external_subroutines += source.external_subroutines

    for module in all_modules:

        source_list = []

        for source in source_objects:

            if module in source.modules:
                source_list.append(source.filename)

        if len(source_list) > 1:

            print
            makemake_lib.abort_multiple_something('modules', module.split('.')[0], name_list=source_list)

    for external_function in all_external_functions:

        source_list = []

        for source in source_objects:

            if external_function in source.external_functions:
                source_list.append(source.filename)

        if len(source_list) > 1:

            print
            makemake_lib.abort_multiple_something('external functions', module.split('.')[0], name_list=source_list)

    for external_subroutine in all_external_subroutines:

        source_list = []

        for source in source_objects:

            if external_subroutine in source.external_subroutines:
                source_list.append(source.filename)

        if len(source_list) > 1:

            print
            makemake_lib.abort_multiple_something('external subroutines', module.split('.')[0], name_list=source_list)

    for source in source_objects:

        for module_dep in source.module_dependencies:

            found = False

            for module in all_modules:

                if module_dep == module:

                    found = True
                    break

            if not found:

                print
                makemake_lib.abort_missing_something('module', source.filename, module_dep.split('.')[0])

        for procedure_dep in source.procedure_dependencies:

            found = False

            for procedure in all_external_functions + all_external_subroutines:

                if procedure_dep == procedure:

                    found = True
                    break

            if not found:

                print
                makemake_lib.abort_missing_something('procedure', source.filename, procedure_dep)

    print ' Done'

    return all_modules

def determine_object_dependencies(source_objects, header_dependencies):

    # This function creates a dictionary with the fortran_source objects
    # as keys. The values are lists of object names for the other
    # sources that implement modules and procedures that the source uses.

    sys.stdout.write('Finding external procedure dependencies...')
    sys.stdout.flush()

    for source in source_objects:

        functions_to_detect = source.external_functions
        subroutines_to_detect = source.external_subroutines

        for other_source in source_objects:

            if not (other_source is source):

                functions_to_detect_filtered = []
                subroutines_to_detect_filtered = []

                for func in functions_to_detect:

                    if not func in other_source.procedure_dependencies:

                        functions_to_detect_filtered.append(func)

                for sub in subroutines_to_detect:

                    if not sub in other_source.procedure_dependencies:

                        subroutines_to_detect_filtered.append(sub)

                detected_procedure_calls = parse_lines(other_source.lines, 
                                                       functions_to_detect=functions_to_detect_filtered, 
                                                       subroutines_to_detect=subroutines_to_detect_filtered)[-1]

                other_source.procedure_dependencies += detected_procedure_calls

    print ' Done'

    sys.stdout.write('Determining object dependencies...')
    sys.stdout.flush()

    object_dependencies = {}

    # For each source
    for source in source_objects:

        object_dependencies[source] = []

        # For each module dependency the source has
        for module in source.module_dependencies:

            # Loop through all the other sources
            for other_source in source_objects:

                if not (other_source is source):

                    # Add object name if it has the correct module
                    if module in other_source.modules:
                        object_dependencies[source].append(other_source)

        # Repeat for procedure dependencies
        for procedure in source.procedure_dependencies:

            for other_source in source_objects:

                if not (other_source is source):

                    if procedure in (other_source.external_functions + other_source.external_subroutines):
                        object_dependencies[source].append(other_source)

        # Get rid of duplicate object names
        object_dependencies[source] = list(set(object_dependencies[source]))

    print ' Done'

    # Remove unnecessary sources

    sys.stdout.write('Removing independent sources...')
    sys.stdout.flush()

    not_needed = []

    for source in source_objects:

        if not source.main_program:

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

    dependency_text = '\nList of detected dependencies:\n'

    for source in sorted(object_dependencies, key=lambda source: len(object_dependencies[source] + header_dependencies[source]), reverse=True):

        if len(object_dependencies[source] + header_dependencies[source]) == 0:

            dependency_text += '\n%s: None\n' % (source.filename)
        
        else:

            dependency_text += '\n%s:\n' % (source.filename)
        
            if len(header_dependencies[source]) > 0:
                dependency_text += '\n'.join(['-%s' % (hdr.split('/')[-1]) for hdr in header_dependencies[source]]) + '\n'

            if len(object_dependencies[source]) > 0:
                dependency_text += '\n'.join(['-%s' % (src.filename) for src in object_dependencies[source]]) + '\n'

    # Convert values from fortran_source instances to object names

    for source in object_dependencies:

        object_dependencies[source] = [src.object_name for src in object_dependencies[source]]

    return source_objects, object_dependencies, dependency_text

def determine_library_usage(source_objects, header_objects):

    # This function collects the information about the individual sources.

    use_mpi = False
    use_openmp = False

    # Go through all source and header objects and gather information
    # about which libraries to use and which source has the main function

    for header in header_objects:

        use_mpi = use_mpi or header.use_mpi
        use_openmp = use_openmp or header.use_openmp

    for source in source_objects:

        use_mpi = use_mpi or source.use_mpi
        use_openmp = use_openmp or source.use_openmp

    return use_mpi, use_openmp

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

def generate_fortran_makefile_from_files(working_dir_path, source_paths, header_paths, source_files, header_files, compiler):

    # This function generates makefiles for compiling the programs 
    # in the given Fortran source files.

    print '\nCollecting files...'

    source_objects, header_paths, header_objects = process_files(working_dir_path, 
                                                                 source_paths, 
                                                                 header_paths,
                                                                 source_files,
                                                                 header_files)

    program_sources = []

    filtered_source_objects = list(source_objects)

    for source in source_objects:

        if source.main_program:

            program_sources.append(source)
            filtered_source_objects.remove(source)

    if len(program_sources) == 0:
        makemake_lib.abort_no_something_file('program')

    print '\nPrograms to generate makefiles for:\n%s' % ('\n'.join(['-%s (%s)' % (src.main_program + '.x', src.filename) for src in program_sources]))

    for program_source in program_sources:

        new_source_objects = [program_source] + filtered_source_objects
        executable_name = program_source.main_program + '.x'

        generate_fortran_makefile_from_objects(working_dir_path, new_source_objects, header_paths, header_objects, program_source, executable_name, compiler)

def generate_fortran_makefile_from_objects(working_dir_path, source_objects, header_paths, header_objects, program_source, executable_name, compiler):

    # This function generates a makefile for compiling the program 
    # given by the supplied fortran_source objects.

    print '\nGenerating makefile for executable %s (%s)...\n' % (executable_name, program_source.filename)

    # Get information from files

    header_dependencies = determine_header_dependencies(source_objects, 
                                                        header_objects)
    
    all_modules = check_dependencies_presence(source_objects)

    source_objects, object_dependencies, dependency_text = determine_object_dependencies(source_objects, 
                                                                                         header_dependencies)

    sys.stdout.write('\nGenerating makefile text... ')
    sys.stdout.flush()

    use_mpi, use_openmp = determine_library_usage(source_objects, header_objects)

    compile_rule_string = gather_compile_rules(source_objects, 
                                               header_dependencies,
                                               object_dependencies)

    # Collect makefile parameters

    default_compiler = 'gfortran'
    compiler = default_compiler if (compiler is None) else compiler

    debug_flags, fast_flags = makemake_lib.read_flag_groups(compiler)

    source_object_names_string = ' '.join([source.object_name for source in source_objects])
    module_names_string = ' '.join(all_modules)

    openmp_flag = '-fopenmp' if use_openmp else ''

    compilation_flags = openmp_flag + ' '.join(['-I\"%s\"' % path for path in header_paths])
    linking_flags = openmp_flag

    mpi_comp_flags = '$(shell mpifort --showme:compile)' if use_mpi else ''
    mpi_link_flags = '$(shell mpifort --showme:link)' if use_mpi else ''

    # Create makefile
    makefile = '''#$%s
# This makefile was generated by makemake.py.
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
MODULES = %s
COMP_FLAGS = %s
LINK_FLAGS = %s
MPI_COMPILE_FLAGS = %s
MPI_LINK_FLAGS = %s

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
\t$(COMP) $(LINK_FLAGS) $(MPI_LINK_FLAGS) $(FLAGS) -o $(EXECNAME) $(OBJECTS)%s

# Action for removing all auxiliary files
clean:
\trm -f $(OBJECTS) $(MODULES)

# Action for reading profiling results
gprof:
\tgprof $(EXECNAME)

# Action for printing help text
help:
\t@echo "Usage:\\nmake <argument 1> <argument 2> ...\\n\\nArguments:\\n<none>:    Compiles with no compiler flags.\\ndebug:   Compiles with flags useful for debugging.\\nfast:    Compiles with flags for high performance.\\nprofile: Compiles with flags for profiling.\\ngprof:   Displays the profiling results with gprof.\\nclean:   Deletes auxiliary files.\\nhelp:    Displays this help text.\\n\\nTo compile with additional flags, add the argument\\nFLAGS=\\"<flags>\\""''' \
    % (executable_name[:-2],
       'mpifort' if use_mpi else compiler,
       executable_name,
       source_object_names_string,
       module_names_string,
       compilation_flags,
       linking_flags,
       mpi_comp_flags,
       mpi_link_flags,
       debug_flags,
       fast_flags,
       compile_rule_string)

    print 'Done'

    makemake_lib.save_makefile(makefile, working_dir_path, executable_name[:-2])

    print dependency_text