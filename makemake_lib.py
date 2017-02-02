#
# This program contains functions that are used by several makefile
# generators.
#
# State: Functional
#
# Last modified 01.02.2017 by Lars Frogner
#
import sys, os

def abort():

    print 'Aborted'
    sys.exit(1)

def abort_not_found(filename):

    print 'Error: could not find file \"%s\"' % filename
    sys.exit(1)

def abort_multiple_something_files(something, source_name_1, source_name_2):

    print 'Error: found multiple %s files (\"%s\" and \"%s\")' \
          % (something, source_name_1, source_name_2)
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

def search_for_file(file_string, working_dir_path, search_paths):

    # This function searches for the given file and returns the full 
    # path where the file was found.

    slash_splitted = file_string.split('/')

    filename = slash_splitted[-1]
    specified_path = '/'.join(slash_splitted[:-1])

    has_specified_path = len(specified_path.strip()) > 0

    print '\n%s:' % filename

    if has_specified_path:

        # Search specified path for the file

        if specified_path[:2] == './':
            specified_path = os.path.join(working_dir_path, specified_path[2:])

        sys.stdout.write('Searching in \"%s\"...' % specified_path)
        sys.stdout.flush()

        filename_with_path = os.path.join(specified_path, filename)

        if not os.path.isfile(filename_with_path):
            abort_not_found(filename)

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

                if path[:2] == './':
                    path = os.path.join(working_dir_path, path[2:])

                sys.stdout.write('Searching in \"%s\"...' % path)
                sys.stdout.flush()

                filename_with_path = os.path.join(path, filename)

                if os.path.isfile(filename_with_path):
                    
                    found = True
                    print ' Found'
                    break

                else:
                    print ' Not found'

            if not found:
                abort_not_found(filename)

        else:
            print ' Found'
            
    return filename_with_path, has_specified_path, specified_path

def save_makefile(makefile, working_dir_path):

    # This function saves the generated makefile text to a file.

    cannot_write = True
    filename = 'makefile'
    makefilepath = os.path.join(working_dir_path, filename)

    while cannot_write:

        if os.path.exists(makefilepath):

            print 'A file named \"%s\" already exists.' % filename

            ans = ''
            while not ans in ['o', 'r', 'a']:
                ans = raw_input('How to proceed? [o: overwrite, r: rename, a: abort]\n').lower()

            if ans == 'o':

                cannot_write = False

            elif ans == 'r':

                filename = raw_input('Input new makfile name:\n')
                makefilepath = os.path.join(working_dir_path, filename)

            elif ans == 'a':

                abort()

        else:
            cannot_write = False

    f = open(makefilepath, 'w')
    f.write(makefile)
    f.close()
    print 'New makefile saved as \"%s\"' % filename

class cycle_resolver:

    def resolve_cycles(self, nodes):

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

                print 'Dropping dependency \"%d\"<-\"%d\"' % (parent.filename, child.filename)

                self.nodes[parent].remove(child)

            elif ans == 'a':

                abort()

            elif ans == 'i':

                print 'Ignoring circular dependency'
                self.ignore_cycles.append(cycle_nodes)

                continue

            break