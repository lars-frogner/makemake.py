#
# This program contains a function for generating a makefile from a
# list of Fortran source files.
#
# State: Functional
#
# Last modified 02.02.2017 by Lars Frogner
#
import sys, os
import makemake_lib

def abort_multiple_programs(source_name, programs):

    print 'Error: found multiple programs in \"%s\": %s' \
          % (source_name, ', '.join(['\"%s\"' % program for program in programs]))
    sys.exit(1)

def parse_lines(lines):

    # This function parses the given list of source code lines and
    # returns information about the content of the source files.

    programs = []
    modules = []
    procedures = []
    module_dependencies = []
    procedure_dependencies = []

    use_mpi = False
    use_openmp = False

    prev_line = ''
    inside = False

    # Parse source file
    for line in lines:

        words = (prev_line + line).split('!')[0] # Ignore everything after "!"

        # Skip blank lines
        if len(words.split()) == 0: continue

        # If line is continued
        if words.strip()[-1] == '&': 

            # Save this line and continue to next one
            prev_line = words.split('&')[0] + ' '
            continue

        else:
            prev_line = ''

        words = words.replace(',', ' ')                  # Treat "," as word separator
        words = words.replace('::', ' :: ')              # Ensure separation at "::"
        words = [word.lower() for word in words.split()] # List of words in lowercase

        n_words = len(words)

        first_word = words[0]
        second_word = '' if n_words < 2 else words[1]
        third_word = '' if n_words < 3 else words[2]

        # External scope declarations
        if not inside:

            # Check for program declaration
            if first_word == 'program':

                programs.append(second_word)
                inside = 'program'

            # Check for module declaration
            elif first_word == 'module':

                modules.append(second_word + '.mod')
                inside = 'module'

            # Check for function declaration
            elif first_word == 'function':

                procedures.append(second_word.split('(')[0])
                inside = 'function'

            elif second_word == 'function':

                procedures.append(third_word.split('(')[0])
                inside = 'function'

            # Check for subroutine declaration
            elif first_word == 'subroutine':

                procedures.append(second_word.split('(')[0])
                inside = 'subroutine'

        # Internal scope declarations
        else:

            # Check for module import statement
            if first_word == 'use':

                deps = words[1:]

                for dep in deps:

                    if dep == 'mpi':
                        use_mpi = True
                    elif dep == 'omp_lib':
                        use_openmp = True
                    else:
                        module_dependencies.append(dep + '.mod')

            # Check for include statement
            if first_word == 'include':

                dep = second_word.split('.h')[0][1:]

                if dep == 'mpi':
                    use_mpi = True
                elif dep == 'omp_lib':
                    use_openmp = True

            # Check for declaration of external procedure
            elif 'external' in words:

                ext_idx = words.index('external')

                if '::' in words:

                    sep_idx = words.index('::')
                    procedure_dependencies += words[sep_idx+1:]

                else:
                    procedure_dependencies += words[ext_idx+1:]

            # Check for end of external scope
            elif first_word == 'end' and second_word == inside:
                inside = False

    # Ignore dependencies on modules and procedures in the same file

    for dep in list(module_dependencies):
        if dep in modules: module_dependencies.remove(dep)

    for dep in list(procedure_dependencies):
        if dep in procedures: procedure_dependencies.remove(dep)

    return programs, modules, procedures, module_dependencies, procedure_dependencies, use_mpi, use_openmp

class f90_source:

    # This class parses an inputted .f90 file and stores information
    # about which programs, modules, external procedures and 
    # dependencies it contains.

    def __init__(self, filename_with_path):

        self.filename_with_path = filename_with_path

        file_path = '/'.join(filename_with_path.split('/')[:-1])

        self.filename = filename_with_path.split('/')[-1]
        self.name = '.'.join(self.filename.split('.')[:-1])
        self.object_name = self.name + '.o'

        sys.stdout.write('Parsing ...')
        sys.stdout.flush()

        f = open(filename_with_path, 'r')
        lines = f.readlines()
        f.close()

        programs, self.modules, self.procedures, self.module_dependencies, self.procedure_dependencies, self.use_mpi, self.use_openmp = parse_lines(lines)

        self.main_program = None if len(programs) == 0 else programs[0]
        if len(programs) > 1: abort_multiple_programs(self.filename, programs)

        print ' Done'

        if not (self.main_program is None):
            print 'Contained programs:\n-' + self.main_program

        if len(self.modules) > 0:
            print 'Contained modules:\n' + '\n'.join([('-%s' % module_name.split('.')[0]) for module_name in self.modules])

        if len(self.procedures) > 0:
            print 'Contained external procedures:\n' + '\n'.join([('-%s' % procedure_name) for procedure_name in self.procedures])

        if len(self.module_dependencies) > 0:
            print 'Used modules:\n' + '\n'.join([('-%s' % module_name.split('.')[0]) for module_name in self.module_dependencies])

        if len(self.procedure_dependencies) > 0:
            print 'Used external procedures:\n' + '\n'.join([('-%s' % procedure_name) for procedure_name in self.procedure_dependencies])

        # Compilation rule for the makefile
        self.compile_rule_declr = '\n\n%s\n%s%s: %s%s ' \
                                  % ('# Rule for compiling ' + self.filename,
                                     self.object_name,
                                     (' ' if len(self.modules) != 0 else '') + ' '.join(self.modules), 
                                     filename_with_path.replace(' ', '\ '),
                                     (' ' if len(self.module_dependencies) != 0 else '') + ' '.join(self.module_dependencies))

        self.compile_rule = '\n%s\t$(COMP) -c $(COMP_FLAGS) \"%s\"' \
                            % (('\trm -f %s\n' % (' '.join(self.modules))) if len(self.modules) != 0 else '', 
                               filename_with_path)

def process_files(working_dir_path, source_paths, source_files):

    # This function creates lists of f90_source instances from the given 
    # lists of filenames and paths.

    source_objects = []

    for file_string in source_files:

        filename_with_path = makemake_lib.search_for_file(file_string, 
                                                          working_dir_path, 
                                                          source_paths)[0]

        source_objects.append(f90_source(filename_with_path))

    return source_objects

def gather_source_information(source_objects, force_openmp):

    # This function collects the information about the individual sources.

    use_mpi = False
    use_openmp = force_openmp

    main_source = None

    # Go through all source and header objects and gather information
    # about which libraries to use and which source has the main function.

    for source in source_objects:

        use_mpi = use_mpi or source.use_mpi
        use_openmp = use_openmp or source.use_openmp

        if not source.main_program is None:

            if main_source is None:
                main_source = source
            else:
                makemake_lib.abort_multiple_something_files('program', main_source.filename, source.filename)

    if main_source is None:
        makemake_lib.abort_no_something_file('program')

    return main_source, use_mpi, use_openmp

def validate_dependencies(source_objects):

    # This function makes sure that all dependencies are present,
    # and that no modules or procedures are implemented multiple
    # times.

    all_modules = []
    all_procedures = []

    for source in source_objects:

        all_modules += source.modules
        all_procedures += source.procedures

    for module in all_modules:

        if all_modules.count(module) > 1:

            makemake_lib.abort_multiple_something('modules', module.split('.')[0])

    for procedure in all_procedures:

        if all_procedures.count(procedure) > 1:

            makemake_lib.abort_multiple_something('procedures', procedure)

    for source in source_objects:

        for module_dep in source.module_dependencies:

            found = False

            for module in all_modules:

                if module_dep == module:

                    found = True
                    break

            if not found:
                makemake_lib.abort_missing_something('module', source.filename, module_dep.split('.')[0])

        for procedure_dep in source.procedure_dependencies:

            found = False

            for procedure in all_procedure:

                if procedure_dep == procedure:

                    found = True
                    break

            if not found:
                makemake_lib.abort_missing_something('procedure', source.filename, procedure_dep)

    return all_modules

def determine_object_dependencies(source_objects):

    # This function creates a dictionary with the f90_source objects
    # as keys. The values are lists of object names for the other
    # sources that implement modules and procedures that the source uses.

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

                    if procedure in other_source.procedures:
                        object_dependencies[source].append(other_source)

        # Get rid of duplicate object names
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

    # Convert values from f90_source instances to object names

    for source in object_dependencies:

        object_dependencies[source] = [src.object_name for src in object_dependencies[source]]

    return object_dependencies

def gather_compile_rules(source_objects, object_dependencies):

    # This function creates a list of compile rules for all the sources,
    # making sure that all the dependencies of the sources are taken
    # into account.

    compile_rules = []

    # For each source
    for source in source_objects:

        # Update prerequisites section of the main compile rule and add to the list
        compile_rules.append(source.compile_rule_declr + ' '.join(object_dependencies[source]) + source.compile_rule)

    return ''.join(compile_rules)

def generate_f90_makefile(working_dir_path, source_paths, source_files, force_openmp):

    # This function generates a makefile for compiling the given 
    # Fortran source files.

    # Get information from files

    print '\nCollecting files...'

    source_objects = process_files(working_dir_path, 
                                   source_paths, 
                                   source_files)

    main_source, use_mpi, use_openmp = gather_source_information(source_objects, 
                                                                 force_openmp)

    print '\nExamining dependencies...'

    all_modules = validate_dependencies(source_objects)

    object_dependencies = determine_object_dependencies(source_objects)

    print '\nGenerating makefile text...'

    compile_rule_string = gather_compile_rules(source_objects, 
                                               object_dependencies)

    # Collect makefile parameters

    compiler = 'mpif90' if use_mpi else 'gfortran'

    executable_name = main_source.name + '.x'

    source_object_names_string = ' '.join([source.object_name for source in source_objects])
    module_names_string = ' '.join(all_modules)

    parallel_flag = '-fopenmp' if use_openmp else ''

    compilation_flags = parallel_flag
    linking_flags = parallel_flag

    # Create makefile
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
MODULES = %s
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
\t$(eval COMP_FLAGS = $(COMP_FLAGS) -Og -Wall -Wextra -Wconversion -pedantic -Wno-tabs -fbounds-check -ffpe-trap=zero,overflow)

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
\trm -f $(OBJECTS) $(MODULES)

# Action for reading profiling results
gprof:
\tgprof $(EXECNAME)''' \
    % (compiler,
       executable_name,
       source_object_names_string,
       module_names_string,
       compilation_flags,
       linking_flags,
       compile_rule_string)

    makemake_lib.save_makefile(makefile, working_dir_path)