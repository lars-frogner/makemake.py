#!/usr/bin/env python3
#
# This program takes a list of Fortran or C source files from the
# command line, and generates a makefile for building the corresponding
# executable.
#
# State: Functional
#
# Last modified 21.02.2017 by Lars Frogner
#
import sys
import os


def abort_usage():

    print('''Usage:
makemake.py <flags> <source files>

Separate arguments with spaces. Surround arguments that contain
spaces with double quotes. Source files lying in another directory
can be prepended with their absoulte path (from {0}{1}) or relative path
(from .{1}).

Flags:
-c <compiler name>: Specifies which compiler to use (default is GCC
                    compilers).
-w:                 Generates a wrapper for all .mk files in the
                    directory.
-S <paths>:         Specifies search paths to use for source files.
-H <paths>:         Specifies search paths to use for header files.
-L <paths>:         Specifies search paths to use for library files.

The S, H and L flags can be combined arbitrarily (e.g. -SH or -LSH).'''
          .format('<drive>:' if sys.platform == 'win32' else '', os.sep))

    sys.exit(1)


def abort_language():

    print('Error: could not determine language unambiguously')
    sys.exit(1)


def abort_ending(filename):

    print('Error: invalid file ending for \"{}\"'.format(filename))
    sys.exit(1)


def extract_flag_args(arg_list, valid_file_endings):

    # This function finds the arguments following the flags
    # in the argument list, removes them from the argument list
    # and returns them in a dictionary.

    n_args = len(arg_list)
    flag_args = {}
    flag_arg_indices = []

    for i in range(n_args):

        if arg_list[i][0] == '-' and len(arg_list[i]) > 1:

            flag = arg_list[i][1:]

            if flag not in flag_args:
                flag_args[flag] = []

            flag_arg_indices.append(i)

            idx = i + 1

            # Loop through arguments following the flag
            while idx < n_args:

                # Find the file ending of the argument if it has one
                dot_splitted = arg_list[idx].split('.')
                ending = None if len(dot_splitted) == 0 else dot_splitted[-1]

                # If the file ending is a valid one, or a new flag has been
                # reached, the flag argument list has ended, and the parsing
                # can end.
                if ending in valid_file_endings or arg_list[idx][0] == '-':

                    break

                # Otherwise, add the argument to a separate list
                else:

                    flag_args[flag].append(arg_list[idx])
                    flag_arg_indices.append(idx)
                    idx += 1

    flag_arg_indices.reverse()

    # Remove identified arguments from the argument list
    for idx in flag_arg_indices:
        arg_list.pop(idx)

    return flag_args


def separate_flags(flag_args, combinable_flags, incombinable_flags):

    # This function separates combined flags into individual flags.

    new_flag_args = flag_args.copy()

    for flag in flag_args:

        if flag not in incombinable_flags:

            arguments = new_flag_args.pop(flag)

            for cflag in flag:

                if cflag in combinable_flags:

                    if cflag in new_flag_args:
                        new_flag_args[cflag] += list(arguments)
                    else:
                        new_flag_args[cflag] = list(arguments)

    return new_flag_args


def detect_language(arg_list, source_endings):

    # This function checks the file endings of the arguments to
    # determine the language in question.

    used_language = None

    for filename in arg_list:

        # Find file ending
        dot_splitted = filename.split('.')
        ending = '<no ending>' if len(dot_splitted) == 0 else dot_splitted[-1]

        for language in source_endings:

            if ending in source_endings[language]:

                if used_language is None:
                    used_language = language
                elif used_language != language:
                    abort_language()

    return used_language


def convert_relative_paths(working_dir_path, paths):

    for i in range(len(paths)):

        if paths[i][:2] == '.' + os.sep:
            paths[i] = os.path.join(working_dir_path, paths[i][2:])

# Print usage if no arguments are provided
if len(sys.argv) < 2:
    abort_usage()

arg_list = sys.argv[1:]

# List of supported languages
languages = ['fortran', 'c']

# Lists of valid flags
combinable_flags = ['S', 'H', 'L']
incombinable_flags = ['w', 'c']

# Organize valid file endings

source_endings = {'fortran': ['f90', 'f95', 'f03', 'f', 'for', 'F', 'F90'],
                  'c': ['c']}
header_endings = {'fortran': ['h'],
                  'c': ['h']}
library_endings = {'fortran': ['a', 'so'],
                   'c': ['a', 'so']}

valid_endings = {language: source_endings[language] +
                           header_endings[language] +
                           library_endings[language]
                 for language in languages}

all_valid_endings = sum(valid_endings.values(), [])

# Get path to the directory this script was run from
working_dir_path = os.getcwd()

# Extract flag arguments

flag_args_combined = extract_flag_args(arg_list, all_valid_endings)
flag_args = separate_flags(flag_args_combined,
                           combinable_flags,
                           incombinable_flags)

generate_wrapper = 'w' in flag_args
compiler = None if 'c' not in flag_args else flag_args['c'][0]
source_paths = [] if 'S' not in flag_args else list(set(flag_args['S']))
header_paths = [] if 'H' not in flag_args else list(set(flag_args['H']))
library_paths = [] if 'L' not in flag_args else list(set(flag_args['L']))

# Convert any relative paths to absoult paths
convert_relative_paths(working_dir_path, source_paths)
convert_relative_paths(working_dir_path, header_paths)
convert_relative_paths(working_dir_path, library_paths)

# Find used language
language = detect_language(arg_list, source_endings)

if language not in languages and not generate_wrapper:
    abort_language()

if language in languages:

    import makemake_lib

    # Extract file arguments

    source_files = []
    header_files = []
    library_files = []

    for filename in arg_list:

        ending = filename.split('.')[-1]

        if ending in source_endings[language]:
            source_files.append(filename)
        elif ending in header_endings[language]:
            header_files.append(filename)
        elif ending in library_endings[language]:
            library_files.append(filename)
        else:
            abort_ending(filename)

    # Run relevant makefile generator

    if language == 'fortran':

        import makemake_f

        print('\nCollecting files...')

        manager = makemake_lib.file_manager(working_dir_path,
                                            source_paths,
                                            header_paths,
                                            library_paths,
                                            source_files,
                                            header_files,
                                            library_files,
                                            makemake_f.fortran_source,
                                            makemake_f.fortran_header,
                                            compiler)

        for sources in manager.source_containers:
            makemake_f.generate_makefile(manager, sources)

    elif language == 'c':

        import makemake_c

        print('\nCollecting files...')

        manager = makemake_lib.file_manager(working_dir_path,
                                            source_paths,
                                            header_paths,
                                            library_paths,
                                            source_files,
                                            header_files,
                                            library_files,
                                            makemake_c.c_source,
                                            makemake_c.c_header,
                                            compiler)

        for sources in manager.source_containers:
            makemake_c.generate_makefile(manager, sources)

if generate_wrapper:

    # Run function for generating a makefile wrapper
    writer = makemake_lib.file_writer(working_dir_path)
    writer.generate_wrapper()
