#
# This program contains functions that are used by several makefile
# generators.
#
# State: Functional
#
# Last modified 23.02.2017 by Lars Frogner
#
import sys
import os
import datetime


class file_manager:

    # This class contains methods for finding files and creating lists
    # of source instances.

    def __init__(self,
                 working_dir_path,
                 source_paths,
                 header_paths,
                 library_paths,
                 source_files,
                 header_files,
                 library_files,
                 source_class,
                 header_class,
                 compiler,
                 executable,
                 library):

        self.working_dir_path = working_dir_path
        self.source_paths = source_paths
        self.header_paths = header_paths
        self.library_paths = library_paths
        self.source_files = source_files
        self.header_files = header_files
        self.library_files = library_files
        self.source_class = source_class
        self.header_class = header_class
        self.compiler = compiler
        self.executable = executable
        self.library = library
        self.library_is_shared = library and library.split('.')[-1] == 'so'

        self.source_instances, self.header_instances, self.library_link_names, \
            self.all_header_paths, self.all_library_paths, \
            self.shared_library_paths = self.process_files()

        self.source_containers = self.collect_programs()

    def process_files(self):

        # This method creates a list of fortran_source instances from the given
        # lists of filenames and paths, and also returns a list of fortran_header
        # instances produced by the process_headers() method.

        # Process source files

        source_instances = []

        for file_string in self.source_files:

            filename_with_path = self.search_for_file(file_string,
                                                      self.source_paths
                                                      )[1]

            source_instances.append(self.source_class(filename_with_path))

        # Process header files

        header_instances, \
            extra_header_paths = self.process_headers(self.header_files)

        missing_header_instances, \
            missing_header_paths = self.find_missing_headers(source_instances,
                                                             header_instances)

        all_header_paths = list(set(self.header_paths + extra_header_paths +
                                    missing_header_paths))
        header_instances = list(set(header_instances +
                                    missing_header_instances))

        # Process library files

        extra_library_paths = []
        shared_library_paths = []
        library_link_names = []

        for file_string in self.library_files:

            has_unlisted_path, path, \
                filename = self.search_for_file(file_string,
                                                self.library_paths
                                                )[2:]

            if len(filename) < 3 or filename[:3] != 'lib':
                self.abort_invalid_lib(filename)

            if filename.split('.')[-1] == 'so' \
               and path not in shared_library_paths:

                shared_library_paths.append(path)

            filename = '.'.join(filename.split('.')[:-1])

            library_link_names.append(filename[3:])

            if has_unlisted_path and \
               path not in self.library_paths + extra_library_paths:

                extra_library_paths.append(path)

        all_library_paths = self.library_paths + extra_library_paths

        return source_instances, header_instances, library_link_names, \
            all_header_paths, all_library_paths, shared_library_paths

    def search_for_file(self, file_string, search_paths, abort_on_fail=True):

        # This method searches for the given file and returns the full
        # path where the file was found.

        slash_splitted = file_string.split(os.sep)

        filename = slash_splitted[-1]

        specified_path = os.sep.join(slash_splitted[:-1])
        has_specified_path = len(specified_path.strip()) > 0

        path = specified_path
        has_unlisted_path = has_specified_path

        filename_with_path = None

        found = True

        print('\n{}:'.format(filename))

        if has_specified_path:

            # Search specified path for the file

            if specified_path[:2] == '.' + os.sep:
                specified_path = os.path.join(self.working_dir_path,
                                              specified_path[2:])

            print('Searching in \"{}\"... '.format(specified_path), end='')

            filename_with_path = os.path.join(specified_path, filename)

            if not os.path.isfile(filename_with_path) and abort_on_fail:

                self.abort_not_found(filename)

            elif not abort_on_fail:

                print('Not found')
                found = False

            else:
                print('Found')

        else:

            # Search the working directory for the file

            possible_path = self.working_dir_path

            print('Searching in working directory... ', end='')

            filename_with_path = os.path.join(self.working_dir_path, filename)

            # If not present in the working directory, search the given list of paths

            if not os.path.isfile(filename_with_path):

                print('Not found')
                found = False

                for possible_path in search_paths:

                    print('Searching in \"{}\"... '.format(possible_path), end='')

                    filename_with_path = os.path.join(possible_path, filename)

                    if os.path.isfile(filename_with_path):

                        print('Found')

                        found = True
                        path = possible_path
                        break

                    else:
                        print('Not found')

                if not found and abort_on_fail:

                    self.abort_not_found(filename)

            else:

                print('Found')

                path = possible_path
                has_unlisted_path = True

        if not found and not abort_on_fail:

            ans = ''
            while ans not in ['y', 'n']:
                ans = input('Could not find \"{}\". Still continue? [y/n]\n'
                            .format(filename)).lower()

            if ans == 'n':
                abort()

        return found, filename_with_path, has_unlisted_path, \
            path, filename

    def process_headers(self, header_files, abort_on_fail=True):

        # This method creates a list of fortran_source header instances
        # from the given lists of filenames and paths.

        header_instances = []
        extra_header_paths = []

        for file_string in header_files:

            found, filename_with_path, has_unlisted_path, \
                path = self.search_for_file(file_string,
                                            self.header_paths,
                                            abort_on_fail=abort_on_fail
                                            )[:4]
            if found:

                header_instances.append(self.header_class(filename_with_path))

                if has_unlisted_path and path not in extra_header_paths:
                    extra_header_paths.append(path)

        return header_instances, extra_header_paths

    def find_missing_headers(self, source_instances, header_instances):

        # Find all headers included by any source or header file

        missing_header_instances = []
        missing_header_paths = []

        iter_list = source_instances + header_instances

        while len(iter_list) > 0:

            missing_headers = []

            for source in iter_list:

                for header_name in source.included_headers:

                    found = False

                    for header in header_instances + missing_header_instances:

                        if header_name == header.filename:

                            found = True
                            break

                    if not found:

                        missing_headers.append(header_name)

            missing_headers = list(set(missing_headers))

            if len(missing_headers) > 0:
                print('\nFound unspecified header dependencies' +
                      '\nStarting search for missing headers...')

            extra_header_instances, \
                extra_header_paths = self.process_headers(missing_headers,
                                                          abort_on_fail=False)

            missing_header_instances = list(set(missing_header_instances +
                                                extra_header_instances))
            missing_header_paths = list(set(missing_header_paths +
                                            extra_header_paths))

            iter_list = extra_header_instances

        return missing_header_instances, missing_header_paths

    def collect_programs(self):

        # This method finds all program sources and creates a source
        # container for each of them.

        program_sources = []

        filtered_source_instances = list(self.source_instances)

        for source in self.source_instances:

            if source.is_main:

                program_sources.append(source)
                filtered_source_instances.remove(source)

        if len(program_sources) == 0 and not self.library:
            print()
            self.abort_no_program_file()

        source_containers = []

        if self.executable:

            if len(program_sources) > 1:
                print()
                self.abort_multiple_program_files([src.filename
                                                   for src in program_sources])

            source_containers.append(source_container(program_sources[0],
                                                      self.source_instances,
                                                      self.header_instances))

        elif self.library:

            if len(program_sources) > 0:
                print()
                self.abort_program_files([src.filename
                                          for src in program_sources])

            source_containers.append(source_container(None,
                                                      self.source_instances,
                                                      self.header_instances))

        else:

            print('\nPrograms to generate makefiles for:\n{}'
                  .format('\n'.join(['-{} ({})'
                                     .format(src.executable_name,
                                             src.filename)
                                     for src in program_sources])))

            for program_source in program_sources:

                new_source_instances = [program_source] + filtered_source_instances
                source_containers.append(source_container(program_source,
                                                          new_source_instances,
                                                          self.header_instances))

        return source_containers

    def abort_not_found(self, filename):

        print('Error: could not find file \"{}\"'.format(filename))
        sys.exit(1)

    def abort_invalid_lib(self, library):

        print('Error: invalid name for library \"{}\". Name must start with \"lib\"'
              .format(library))
        sys.exit(1)

    def abort_no_program_file(self):

        print('Error: found no program file')
        sys.exit(1)

    def abort_multiple_program_files(self, program_files):

        print('Error: cannot have multiple program files ({}) when -x flag is specified'
              .format(', '.join(program_files)))
        sys.exit(1)

    def abort_program_files(self, program_files):

        print('Error: cannot have program files ({}) when -l flag is specified'
              .format(', '.join(program_files)))
        sys.exit(1)


class source_container:

    # This class is used for holding source instances, and contains
    # methods for processing dependencies and extracting relevant
    # information.

    def __init__(self, program_source, source_instances, header_instances):

        self.program_source = program_source
        self.source_instances = source_instances
        self.header_instances = header_instances

    def determine_header_dependencies(self):

        # This method creates a dictionary with source_class instances
        # as keys. The values are lists of paths to the headers that the
        # source depends on.

        # Find all headers that each header includes

        print('Finding header dependencies... ', end='')

        header_header_dependencies = {}

        for header in self.header_instances:

            header_header_dependencies[header] = []

            for header_name in header.included_headers:

                for other_header in self.header_instances:

                    if header is not other_header and \
                       header_name == other_header.filename:

                        header_header_dependencies[header].append(other_header)
                        break

        # Find all headers that each header dependes on, directly or
        # indirectly

        def add_header_dependencies(original_parent, parent):

            for child in header_header_dependencies[parent]:

                if not (child is original_parent or
                        child in header_header_dependencies[original_parent]):

                    header_header_dependencies[original_parent].append(child)

                    add_header_dependencies(original_parent, child)

        for header in self.header_instances:

            for child in header_header_dependencies[header]:

                add_header_dependencies(header, child)

        # Find all headers that each source depends on, directly or
        # indirectly. Also transfer any dependencies the headers have
        # to the sources that depend on them

        source_header_dependencies = {}

        for source in self.source_instances:

            source_header_dependencies[source] = []

            for header_name in source.included_headers:

                for header in self.header_instances:

                    if header_name == header.filename:

                        for other_header in [header] + header_header_dependencies[header]:

                            if other_header.filename_with_path not in \
                               source_header_dependencies[source]:

                                source_header_dependencies[source]\
                                    .append(other_header.filename_with_path)

                                source.update_source_information(other_header)

                        break

        print('Done')

        self.header_dependencies = source_header_dependencies

    def process_dependencies(self, unprocessed_object_dependencies):

        # This method cleans the object dependency dictionary by removing
        # unnecessary sources and resolving circular dependencies. It also
        # returns a dependency string for printing.

        object_dependencies = unprocessed_object_dependencies.copy()
        source_instances = list(object_dependencies.keys())

        # Remove unnecessary sources

        if self.program_source is not None:

            print('Removing independent sources... ', end='')

            not_needed = []

            for source in source_instances:

                if not source.is_main:

                    is_needed = False

                    for other_source in source_instances:

                        if other_source is not source:

                            for source_dependency in object_dependencies[other_source]:

                                if source_dependency is source:
                                    is_needed = True

                    if not is_needed:
                        not_needed.append(source)

            for remove_src in not_needed:

                source_instances.remove(remove_src)
                object_dependencies.pop(remove_src)

            print('Done')

        # Fix circular dependencies

        print('Checking for circular dependencies... ', end='')

        object_dependencies = cycle_resolver().resolve_cycles(object_dependencies)

        print('Done')

        # Print dependency list

        dependency_text = '\nList of detected dependencies:'

        for source in sorted(object_dependencies,
                             key=lambda source: len(object_dependencies[source] +
                                                    self.header_dependencies[source]),
                             reverse=True):

            if len(object_dependencies[source] + self.header_dependencies[source]) == 0:

                dependency_text += '\n' + '\n{}: None'.format(source.filename)

            else:

                dependency_text += '\n' + '\n{}:'.format(source.filename)

                if len(self.header_dependencies[source]) > 0:
                    dependency_text += '\n' + \
                        '\n'.join(['-{} [{}]'
                                   .format(hdr.split(os.sep)[-1],
                                           source.dependency_descripts[hdr.split(os.sep)[-1]])
                                   for hdr in self.header_dependencies[source]])

                if len(object_dependencies[source]) > 0:
                    dependency_text += '\n' + \
                        '\n'.join(['-{} [{}]'
                                   .format(src.filename,
                                           source.dependency_descripts[src.filename])
                                   for src in object_dependencies[source]])

        # Convert values from source instances to object names

        for source in object_dependencies:

            object_dependencies[source] = [src.object_name
                                           for src in object_dependencies[source]]

        self.reduced_source_instances = source_instances
        self.object_dependencies = object_dependencies

        return dependency_text

    def get_internal_libraries(self):

        # This method determines which libraries must be used based
        # on which libraries the individual sources use.

        internal_libraries = {lib: False
                              for lib in self.reduced_source_instances[0].internal_libraries}

        # Go through all source and header objects and gather information
        # about which libraries to use and which source has the main function

        for instance in self.reduced_source_instances + self.header_instances:

            for lib in internal_libraries:

                internal_libraries[lib] = internal_libraries[lib] or \
                                           instance.internal_libraries[lib]

        return internal_libraries

    def get_compile_rules(self):

        # This method creates a list of compile rules for all the sources,
        # making sure that all the dependencies of the sources are taken
        # into account.

        compile_rules = []

        # For each source
        for source in self.reduced_source_instances:

            dependencies = [header_path.replace(' ', '\ ')
                            for header_path in self.header_dependencies[source]] \
                           + self.object_dependencies[source]

            # Update prerequisites section of the main compile rule and add to the list
            compile_rules.append(source.compile_rule_declr +
                                 ' '.join(dependencies) + source.compile_rule)

        return ''.join(compile_rules)


class cycle_resolver:

    # This class contains methods for detecting and resolving circular
    # dependencies in a source dependency dictionary.

    def resolve_cycles(self, nodes):

        # This method keeps repeating the cycle detection an resolving
        # as long as the dependecy tree is being modified.

        self.nodes = nodes.copy()
        self.ignore_cycles = []

        while True:

            self.run_depth_first_traversal()

            if len(self.cycle_nodes_list) > 0:

                self.fix_cycle()

            else:

                break

        return self.nodes

    def run_depth_first_traversal(self):

        # This runs the cycle detection with every node as a root.

        self.cycle_nodes_list = []
        self.cycle_nodes = []
        self.visited = {}
        self.start = {}

        for node in self.nodes:

            self.visited[node] = False
            self.start[node] = False

        for node in self.nodes:

            self.start_node = node
            self.depth_first_traversal(node, is_not_first=False)
            self.start[node] = True

        self.cycle_nodes_list = sorted(self.cycle_nodes_list, key=len)

    def depth_first_traversal(self, node, is_not_first=True):

        # This method traverses the dependency graph recursively from
        # a certain node and finds cycles rooted on that node. The nodes
        # involved in the cycles are added to a list.

        if not self.start[node]:

            if self.visited[node]:

                if node == self.start_node:

                    cycle_nodes_complete = [node] + self.cycle_nodes

                    if cycle_nodes_complete not in self.ignore_cycles:
                        self.cycle_nodes_list.append(cycle_nodes_complete)

            else:

                self.visited[node] = True

                for child in self.nodes[node]:

                    if is_not_first:
                        self.cycle_nodes.append(node)

                    self.depth_first_traversal(child)

                    self.cycle_nodes = self.cycle_nodes[:-1]

                self.visited[node] = False

    def fix_cycle(self):

        # This method informs the use about circular dependecies and
        # ask for how to resolve them.

        for cycle_nodes in self.cycle_nodes_list:

            idx_list = range(1, len(cycle_nodes)+1)
            idx_str_list = [str(i) for i in idx_list]
            ans_list = idx_str_list + ['a', 'i']

            print('\nWarning: circular dependency detected:\n{}( <-{} ...)'
                  .format(' <- '.join([node.filename for node in cycle_nodes]),
                          cycle_nodes[0].filename))

            ans = ''
            while ans not in ans_list:
                ans = input('Which dependency to drop? ' +
                            '[<n>: drop file # n <-, a: abort, i: ignore]\n').lower()

            if ans in idx_str_list:

                idx1 = int(ans)-1
                idx2 = idx1 + 1 if idx1 < len(cycle_nodes) - 1 else 0

                parent = cycle_nodes[idx1]
                child = cycle_nodes[idx2]

                print('Dropping dependency {} <- {}'
                      .format(parent.filename, child.filename))

                self.nodes[parent].remove(child)

            elif ans == 'a':

                abort()

            elif ans == 'i':

                print('Ignoring circular dependency')
                self.ignore_cycles.append(cycle_nodes)

                continue

            break


class file_writer:

    # This class contains methods for writing a makefile text.

    def __init__(self, working_dir_path):

        self.working_dir_path = working_dir_path

    def save_makefile(self, makefile, output_name):

        # This method saves the generated makefile text to a file, while
        # managing any existing makefiles to avoid conflicts.

        filename = 'makefile'
        makefilepath = os.path.join(self.working_dir_path, filename)

        if os.path.exists(makefilepath):

            f = open(makefilepath, 'r')
            lines = f.readlines()
            f.close()

            is_wrapper = False
            other_output_name = None

            for line in lines:

                stripped = line.strip()

                if stripped == '#$wrapper':

                    is_wrapper = True
                    break

                elif len(stripped) > 2 and stripped[:2] == '#@':

                    other_output_name = stripped[2:]
                    break

            if is_wrapper:

                print('\nThere exists a makefile wrapper in this directory')

                ans = ''
                while ans not in ['o', 'n', 'w', 'a']:
                    ans = input('How to proceed? [o: overwrite wrapper, ' +
                                'n: set custom name, w: include in wrapper, a: abort]\n').lower()

                if ans == 'o':

                    print('Overwriting makefile wrapper... ', end='')

                    f = open(makefilepath, 'w')
                    f.write(makefile)
                    f.close()

                    print('Done')

                elif ans == 'n':

                    filename = input('Input new makefile name:\n')
                    self.write_new_file(makefile, filename)

                elif ans == 'w':

                    makefile_name = '{}.mk'.format(output_name)

                    self.write_new_file(makefile, makefile_name)

                    self.generate_wrapper()

                elif ans == 'a':

                    abort()

            elif other_output_name is not None and \
                 output_name != other_output_name:

                print('\nThere already exists a default ' +
                      'generated makefile for another output file')

                ans = ''
                while ans not in ['o', 'n', 'w', 'a']:
                    ans = input('How to proceed? [o: overwrite, ' +
                                'n: set custom name, w: create wrapper, a: abort]\n').lower()

                if ans == 'o':

                    print('Overwriting old makefile... ', end='')

                    f = open(makefilepath, 'w')
                    f.write(makefile)
                    f.close()

                    print('Done')

                elif ans == 'n':

                    filename = input('Input new makefile name:\n')
                    self.write_new_file(makefile, filename)

                elif ans == 'w':

                    makefile_name = '{}.mk'.format(output_name)
                    other_makefile_name = '{}.mk'.format(other_output_name)

                    print('Renaming old makefile to \"{}\"... '
                          .format(other_makefile_name), end='')

                    os.rename(makefilepath,
                              os.path.join(self.working_dir_path, other_makefile_name))

                    print('Done')

                    self.write_new_file(makefile, makefile_name)

                    self.generate_wrapper()

                elif ans == 'a':

                    abort()

            else:

                if output_name == other_output_name:
                    print('\nThere already exists a default ' +
                          'generated makefile for this output file')
                else:
                    print('\nThere already exists a default ' +
                          'non-generated makefile in this directory')

                ans = ''
                while ans not in ['o', 'n', 'a']:
                    ans = input('How to proceed? [o: overwrite, ' +
                                'n: set custom name, a: abort]\n').lower()

                if ans == 'o':

                    print('Overwriting old makefile... ', end='')

                    f = open(makefilepath, 'w')
                    f.write(makefile)
                    f.close()

                    print('Done')

                elif ans == 'n':

                    filename = input('Input new makefile name:\n')
                    self.write_new_file(makefile, filename)

                elif ans == 'a':

                    abort()

        else:

            print('\nSaving makefile... ', end='')

            f = open(makefilepath, 'w')
            f.write(makefile)
            f.close()

            print('Done')

    def write_new_file(self, text, filename, ftype='makefile'):

        # This method saves a new file with a custom name.

        filepath = os.path.join(self.working_dir_path, filename)
        cannot_write = True

        while cannot_write:

            print('\nSaving {} as \"{}\"... '.format(ftype, filename), end='')

            if os.path.exists(filepath):

                print('\nA file of the same name already exists')

                ans = ''
                while ans not in ['o', 'n', 'a']:
                    ans = input('How to proceed? [o: overwrite, ' +
                                'n: new name, a: abort]\n').lower()

                if ans == 'o':

                    print('Overwriting old file... ', end='')

                    cannot_write = False

                elif ans == 'n':

                    filename = input('Input new {} name:\n'.format(ftype))
                    filepath = os.path.join(self.working_dir_path, filename)

                elif ans == 'a':

                    abort()

            else:
                cannot_write = False

        f = open(filepath, 'w')
        f.write(text)
        f.close()

        print('Done')

    def generate_wrapper(self):

        # This method generates a wrapper for the makefiles in the
        # working directory.

        print('\nGenerating makefile wrapper...')

        makefile_names = []

        for filename in os.listdir(self.working_dir_path):
            if os.path.isfile(filename):
                if '.' in filename and filename.split('.')[-1] == 'mk':

                    makefile_names.append('.'.join(filename.split('.')[:-1]))

        if len(makefile_names) > 0:

            print('Makefiles found:\n' +
                  '\n'.join(['-{}.mk'.format(makefile_name)
                             for makefile_name in makefile_names]))

            wrapper_text = '''#$wrapper
    # This makefile wrapper was generated by makemake.py ({}).
    # GitHub repository: https://github.com/lars-frogner/makemake.py
    #
    # Usage:
    # 'make <name> [ARGS="<argument 1> <argument 2> ..."]'
    #
    # This runs <name>.mk with the stated arguments.''' \
            .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

            for makefile_name in makefile_names:

                wrapper_text += '\n\n{}:\n\tmake -f {} $(ARGS)'\
                                .format(makefile_name, makefile_name + '.mk')

            self.write_new_file(wrapper_text,
                                'makefile',
                                ftype='makefile wrapper')

        else:

            print('No makefiles found')


def abort():

    print('Aborted')
    sys.exit(1)


def abort_missing_something(something, source_name, something_name):

    print('Error: could not find {} \"{}\" used by source file \"{}\"'
          .format(something, something_name, source_name))
    sys.exit(1)


def abort_multiple_something(something, something_name, name_list=False):

    print('Error: found multiple {} named \"{}\"{}'
          .format(something,
                  something_name,
                  '' if not name_list else '\n({})'.format(', '.join(name_list))))
    sys.exit(1)


def read_flag_groups(compiler):

    # This functions reads the debug_flags.ini and performance_flags.ini
    # files and extracts the relevant debug and performance flag groups.

    source_path = os.path.dirname(os.path.abspath(__file__))

    try:
        f = open(os.path.join(source_path, 'debug_flags.ini'), 'r')
        lines = f.readlines()
        f.close()

        debug_flags = ''

        for line in lines:

            colon_splitted = line.split(':')

            if len(colon_splitted) > 1 and colon_splitted[0].strip() == compiler:

                debug_flags = ':'.join(colon_splitted[1:]).strip()
                break

        if debug_flags == '':
            print('\nWarning: no entry for compiler \"{}\" in \"debug_flags.ini\"'
                  .format(compiler))
            print('No debug flag group set')

    except IOError:

        print('\nWarning: could not open \"debug_flags.ini\"')
        print('No debug flag group set')
        debug_flags = ''

    try:
        f = open(os.path.join(source_path, 'performance_flags.ini'), 'r')
        lines = f.readlines()
        f.close()

        fast_flags = ''

        for line in lines:

            colon_splitted = line.split(':')

            if len(colon_splitted) > 1 and colon_splitted[0].strip() == compiler:

                fast_flags = ':'.join(colon_splitted[1:]).strip()
                break

        if fast_flags == '':
            print('\nWarning: no entry for compiler \"{}\" in \"performance_flags.ini\"'
                  .format(compiler))
            print('No debug flag group set')

    except IOError:

        print('\nWarning: could not open \"performance_flags.ini\"')
        print('No debug flag group set')
        fast_flags = ''

    return debug_flags, fast_flags


def get_common_makefile_parameters(manager, sources, default_compiler, mpi_compiler):

    # Collect makefile parameters

    internal_libraries = sources.get_internal_libraries()
    compile_rule_string = sources.get_compile_rules()

    if manager.executable:
        output_name = manager.executable
    elif manager.library:
        output_name = manager.library
    else:
        output_name = sources.program_source.executable_name

    pure_output_name = output_name.split('.')[0]

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if internal_libraries.pop('mpi'):
        compiler = mpi_compiler
    elif manager.compiler:
        compiler = manager.compiler
    else:
        compiler = default_compiler

    debug_flags, fast_flags = read_flag_groups(compiler)

    object_files = ' '.join([source.object_name
                             for source in sources.reduced_source_instances])

    if internal_libraries.pop('openmp'):
        compilation_flags = '-fopenmp '
        linking_flags = '-fopenmp '
    else:
        compilation_flags = ''
        linking_flags = ''

    if manager.library_is_shared:
        compilation_flags += '-fpic'
        linking_flags += '-shared'

    header_path_flags = ' '.join(['-I\"{}\"'.format(path)
                                  for path in manager.all_header_paths])

    library_path_flags = ' '.join(['-L\"{}\"'.format(path)
                                   for path in manager.all_library_paths])

    if len(manager.shared_library_paths) > 0:
        library_path_flags += ' -Wl,' +\
            ','.join(['-rpath,\"{}\"'.format(path)
                      for path in manager.shared_library_paths])

    used_internal_libraries = []
    for lib in internal_libraries:
        if internal_libraries[lib]:
            used_internal_libraries.append(lib)

    library_link_flags = ' '.join(['-l{}'.format(filename)
                                   for filename in manager.library_link_names +
                                                   used_internal_libraries])

    if sys.platform == 'win32':

        delete_cmd = 'del /F'
        delete_trail = ' 2>nul'

        help_text = 'Usage:' + \
                    ' & echo make ^<argument 1^> ^<argument 2^> ...' + \
                    ' & echo.' + \
                    ' & echo Arguments: ' + \
                    ' & echo ^<none^>:  Compiles with no compiler flags.' + \
                    ' & echo debug:   Compiles with flags useful for debugging.' + \
                    ' & echo fast:    Compiles with flags for high performance.' + \
                    ' & echo profile: Compiles with flags for profiling.' if not manager.library else '' + \
                    ' & echo gprof:   Displays the profiling results with gprof.' if not manager.library else '' + \
                    ' & echo clean:   Deletes auxiliary files.' + \
                    ' & echo help:    Displays this help text.' + \
                    ' & echo.' + \
                    ' & echo To compile with additional flags, add the argument' + \
                    ' & echo EXTRA_FLAGS="<flags>"'
    else:

        delete_cmd = 'rm -f'
        delete_trail = ''

        help_text = '"Usage:' + \
                    '\\nmake <argument 1> <argument 2> ...' + \
                    '\\n' + \
                    '\\nArguments:' + \
                    '\\n<none>:  Compiles with no compiler flags.' + \
                    '\\ndebug:   Compiles with flags useful for debugging.' + \
                    '\\nfast:    Compiles with flags for high performance.' + \
                    '\\nprofile: Compiles with flags for profiling.' if not manager.library else '' + \
                    '\\ngprof:   Displays the profiling results with gprof.' if not manager.library else '' + \
                    '\\nclean:   Deletes auxiliary files.' + \
                    '\\nhelp:    Displays this help text.' + \
                    '\\n' + \
                    '\\nTo compile with additional flags, add the argument' + \
                    '\\nEXTRA_FLAGS=\\"<flags>\\""'

    return pure_output_name, current_time, compiler, \
        output_name, object_files, compilation_flags, \
        linking_flags, header_path_flags, library_link_flags, \
        library_path_flags, debug_flags, fast_flags, \
        compile_rule_string, delete_cmd, delete_trail, \
        help_text
