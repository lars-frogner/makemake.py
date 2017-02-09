#
# This program contains functions that are used by several makefile
# generators.
#
# State: Functional
#
# Last modified 08.02.2017 by Lars Frogner
#
import sys, os

def abort():

    print 'Aborted'
    sys.exit(1)

def abort_not_found(filename):

    print 'Error: could not find file \"%s\"' % filename
    sys.exit(1)

def abort_no_something_file(something):

    print 'Error: found no %s file' % something
    sys.exit(1)

def abort_missing_something(something, source_name, something_name):

    print 'Error: could not find %s \"%s\" used by source file \"%s\"' \
          % (something, something_name, source_name)
    sys.exit(1)

def abort_multiple_something(something, something_name):

    print 'Error: found multiple %s named \"%s\"' \
          % (something, something_name)
    sys.exit(1)

def search_for_file(file_string, working_dir_path, search_paths, abort_on_fail=True):

    # This function searches for the given file and returns the full 
    # path where the file was found.

    slash_splitted = file_string.split('/')

    filename = slash_splitted[-1]

    specified_path = '/'.join(slash_splitted[:-1])
    has_specified_path = len(specified_path.strip()) > 0

    determined_path = specified_path
    has_determined_path = has_specified_path

    filename_with_path = None

    found = True

    print '\n%s:' % filename

    if has_specified_path:

        # Search specified path for the file

        if specified_path[:2] == './':
            specified_path = os.path.join(working_dir_path, specified_path[2:])

        sys.stdout.write('Searching in \"%s\"...' % specified_path)
        sys.stdout.flush()

        filename_with_path = os.path.join(specified_path, filename)

        if not os.path.isfile(filename_with_path) and abort_on_fail:

            abort_not_found(filename)

        elif not abort_on_fail:

            print ' Not found'
            found = False

        else:
            print ' Found'

    else:

        # Search the working directory for the file

        path = working_dir_path

        sys.stdout.write('Searching in working directory...')
        sys.stdout.flush()

        filename_with_path = os.path.join(working_dir_path, filename)

        # If not present in the working directory, search the given list of paths

        if not os.path.isfile(filename_with_path):

            print ' Not found'
            found = False

            for path in search_paths:

                sys.stdout.write('Searching in \"%s\"...' % path)
                sys.stdout.flush()

                filename_with_path = os.path.join(path, filename)

                if os.path.isfile(filename_with_path):
                    
                    print ' Found'

                    found = True
                    break

                else:
                    print ' Not found'

            if not found and abort_on_fail:

                abort_not_found(filename)

        else:

            print ' Found'

            determined_path = path
            has_determined_path = True

    if not found and not abort_on_fail:

        ans = ''
        while not ans in ['y', 'n']:
            ans = raw_input('Could not find \"%s\". Still continue? [y/n]\n' % filename).lower()

        if ans == 'n':
            abort()
            
    return found, filename_with_path, has_determined_path, determined_path, filename

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

                    if not cycle_nodes_complete in self.ignore_cycles:
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

            print '\nWarning: circular dependency detected:\n%s( <-%s ...)' \
                  % (' <- '.join([node.filename for node in cycle_nodes]), cycle_nodes[0].filename)

            ans = ''
            while not ans in ans_list:
                ans = raw_input('Which dependency to drop? [<n>: drop file # n <-, a: abort, i: ignore]\n').lower()

            if ans in idx_str_list:

                idx1 = int(ans)-1
                idx2 = idx1 + 1 if idx1 < len(cycle_nodes) - 1 else 0

                parent = cycle_nodes[idx1]
                child = cycle_nodes[idx2]

                print 'Dropping dependency %s <- %s' % (parent.filename, child.filename)

                self.nodes[parent].remove(child)

            elif ans == 'a':

                abort()

            elif ans == 'i':

                print 'Ignoring circular dependency'
                self.ignore_cycles.append(cycle_nodes)

                continue

            break

def save_makefile(makefile, working_dir_path, executable_name):

    # This function saves the generated makefile text to a file, while
    # managing any existing makefiles to avoid conflicts.

    filename = 'makefile'
    makefilepath = os.path.join(working_dir_path, filename)

    if os.path.exists(makefilepath):

        f = open(makefilepath, 'r')
        lines = f.readlines()
        f.close()

        is_wrapper = False
        other_executable_name = None

        for line in lines:

            stripped = line.strip()

            if stripped == '#$wrapper':

                is_wrapper = True
                break

            elif len(stripped) > 2 and stripped[:2] == '#@':

                other_executable_name = stripped[2:]
                break

        if is_wrapper:

            print '\nThere exists a makefile wrapper in this directory'

            ans = ''
            while not ans in ['o', 'n', 'w', 'a']:
                ans = raw_input('How to proceed? [o: overwrite wrapper, n: set custom name, w: include in wrapper, a: abort]\n').lower()

            if ans == 'o':

                sys.stdout.write('Overwriting makefile wrapper...')
                sys.stdout.flush()

                f = open(makefilepath, 'w')
                f.write(makefile)
                f.close()

                print ' Done'

            elif ans == 'n':

                filename = raw_input('Input new makefile name:\n')
                write_new_file(makefile, working_dir_path, filename)

            elif ans == 'w':

                makefile_name = '%s.mk' % executable_name

                write_new_file(makefile, working_dir_path, makefile_name)

                generate_wrapper(working_dir_path)

            elif ans == 'a':

                abort()

        elif not (other_executable_name is None) and executable_name != other_executable_name:

            print '\nThere already exists a default generated makefile for another executable'

            ans = ''
            while not ans in ['o', 'n', 'w', 'a']:
                ans = raw_input('How to proceed? [o: overwrite, n: set custom name, w: create wrapper, a: abort]\n').lower()

            if ans == 'o':

                sys.stdout.write('Overwriting old makefile...')
                sys.stdout.flush()

                f = open(makefilepath, 'w')
                f.write(makefile)
                f.close()

                print ' Done'

            elif ans == 'n':

                filename = raw_input('Input new makefile name:\n')
                write_new_file(makefile, working_dir_path, filename)

            elif ans == 'w':

                makefile_name = '%s.mk' % executable_name
                other_makefile_name = '%s.mk' % other_executable_name

                sys.stdout.write('Renaming old makefile to \"%s\"...' % other_makefile_name)
                sys.stdout.flush()

                os.rename(makefilepath, os.path.join(working_dir_path, other_makefile_name))

                print ' Done'

                write_new_file(makefile, working_dir_path, makefile_name)

                generate_wrapper(working_dir_path)

            elif ans == 'a':

                abort()

        else:

            if executable_name == other_executable_name:
                print '\nThere already exists a default generated makefile for this executable'
            else:
                print '\nThere already exists a default non-generated makefile in this directory'

            ans = ''
            while not ans in ['o', 'n', 'a']:
                ans = raw_input('How to proceed? [o: overwrite, n: set custom name, a: abort]\n').lower()

            if ans == 'o':

                sys.stdout.write('Overwriting old makefile...')
                sys.stdout.flush()

                f = open(makefilepath, 'w')
                f.write(makefile)
                f.close()

                print ' Done'

            elif ans == 'n':

                filename = raw_input('Input new makefile name:\n')
                write_new_file(makefile, working_dir_path, filename)

            elif ans == 'a':

                abort()

    else:

        sys.stdout.write('\nSaving makefile...')
        sys.stdout.flush()

        f = open(makefilepath, 'w')
        f.write(makefile)
        f.close()

        print ' Done'

def write_new_file(text, working_dir_path, filename, ftype='makefile'):

    # This function saves a new file with a custom name.

    filepath = os.path.join(working_dir_path, filename)
    cannot_write = True

    while cannot_write:

        sys.stdout.write('\nSaving %s as \"%s\"... ' % (ftype, filename))
        sys.stdout.flush()

        if os.path.exists(filepath):

            print '\nA file of the same name already exists'

            ans = ''
            while not ans in ['o', 'n', 'a']:
                ans = raw_input('How to proceed? [o: overwrite, n: new name, a: abort]\n').lower()

            if ans == 'o':

                sys.stdout.write('Overwriting old file... ')
                sys.stdout.flush()

                cannot_write = False

            elif ans == 'n':

                filename = raw_input('Input new %s name:\n' % ftype)
                filepath = os.path.join(working_dir_path, filename)

            elif ans == 'a':

                abort()

        else:
            cannot_write = False

    f = open(filepath, 'w')
    f.write(text)
    f.close()

    print 'Done'

def generate_wrapper(working_dir_path):

    # This function generates a wrapper for the makefiles in the
    # working directory.

    print '\nGenerating makefile wrapper...'

    makefile_names = []

    for filename in os.listdir(working_dir_path):
        if os.path.isfile(filename):
            if '.' in filename and filename.split('.')[-1] == 'mk':

                makefile_names.append('.'.join(filename.split('.')[:-1]))

    if len(makefile_names) > 0:

        print 'Makefiles found:\n' + '\n'.join([('-%s.mk' % makefile_name) for makefile_name in makefile_names])

        wrapper_text = '''#$wrapper
# This makefile wrapper was generated by makemake.py.
# GitHub repository: https://github.com/lars-frogner/makemake.py
# 
# Usage:
# 'make <name> [ARGS="<argument 1> <argument 2> ..."]'
#
# This runs <name>.mk with the stated arguments.'''

        for makefile_name in makefile_names:

            wrapper_text += '\n\n%s:\n\tmake -f %s $(ARGS)' % (makefile_name, makefile_name + '.mk')

        write_new_file(wrapper_text, working_dir_path, 'makefile', ftype='makefile wrapper')

    else:

        print 'No makefiles found'