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

    if has_specified_path:

        # Search specified path for the file

        if specified_path[:2] == './':
            specified_path = os.path.join(working_dir_path, specified_path[2:])

        sys.stdout.write('Searching for \"%s\" in \"%s\"...' % (filename, specified_path))
        sys.stdout.flush()

        filename_with_path = os.path.join(specified_path, filename)

        if not os.path.isfile(filename_with_path):
            abort_not_found(filename)

        print ' Found'

    else:

        # Search the working directory for the file

        path = working_dir_path

        sys.stdout.write('Searching for \"%s\" in working directory...' % filename)
        sys.stdout.flush()

        filename_with_path = os.path.join(working_dir_path, filename)

        # If not present in the working directory, search the given list of paths

        if not os.path.isfile(filename_with_path):

            print ' Not found'

            found = False

            for path in search_paths:

                if path[:2] == './':
                    path = os.path.join(working_dir_path, path[2:])

                sys.stdout.write('Searching for \"%s\" in \"%s\"...' % (filename, path))
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