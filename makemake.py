#!/usr/bin/env python
#
# This program takes a list of Fortran or C source files from the 
# command line, and generates a makefile for building the corresponding 
# executable.
#
# State: Functional
#
# Last modified 02.02.2017 by Lars Frogner
#
import sys, os

def abort_usage():

    print 'Usage:\nmakemake.py <list of source files> ...'
    sys.exit(1)

def abort_language():

    print 'Error: could not determine language unambiguously'
    sys.exit(1)

def abort_ending(filename):

    print 'Error: invalid file ending for \"%s\"' % filename
    sys.exit(1)

def extract_flag_args(arg_list, valid_file_endings):

    # This function finds the arguments following the flags
    # in the argument list, removes them from the argument list 
    # and returns them in a dictionary.

    n_args = len(arg_list)
    flag_args = {}
    flag_arg_indices = []

    for i in xrange(n_args):

        if arg_list[i][0] == '-' and len(arg_list[i]) > 1:

            flag = arg_list[i][1:]

            if not flag in flag_args: flag_args[flag] = []

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

        if not flag in incombinable_flags:

            arguments = new_flag_args.pop(flag)

            for cflag in combinable_flags:

                if cflag in flag:

                    new_flag_args[cflag] = arguments

    return new_flag_args

def detect_language(arg_list, valid_fortran_endings, valid_c_endings):

    # This function checks the file endings of the arguments to 
    # determine the language in question.

    language = None

    for filename in arg_list:

        # Find file ending
        dot_splitted = filename.split('.')
        ending = '<no ending>' if len(dot_splitted) == 0 else dot_splitted[-1]

        if ending in valid_fortran_endings:

            if language is None:
                language = 'fortran'
            elif not language == 'fortran':
                abort_language()

        elif ending in valid_c_endings:

            if language is None:
                if ending == 'c':
                    language = 'c'
            elif not language == 'c':
                abort_language()

        else:
            abort_ending(filename)

    if language is None:
        abort_language()

    return language

if len(sys.argv) < 2:
    abort_usage()

combinable_flags = ['S', 'H', 'L']
incombinable_flags = ['openmp']

valid_fortran_endings = ['f90']
valid_c_endings = ['c', 'h', 'a', 'so']
valid_file_endings = valid_fortran_endings + valid_c_endings

# Get path to the directory this script was run from
working_dir_path = os.getcwd()

arg_list = sys.argv[1:]

flag_args = extract_flag_args(arg_list, valid_file_endings)
flag_args = separate_flags(flag_args, combinable_flags, incombinable_flags)

force_openmp = 'openmp' in flag_args
source_paths = [] if not ('S' in flag_args) else flag_args['S']
header_paths = [] if not ('H' in flag_args) else flag_args['H']
library_paths = [] if not ('L' in flag_args) else flag_args['L']

language = detect_language(arg_list, valid_fortran_endings, valid_c_endings)

# Run relevant makemake code
if language == 'fortran':

    import makemake_f

    source_files = arg_list

    makemake_f.generate_f90_makefile(working_dir_path, source_paths, source_files, force_openmp)

elif language == 'c':

    import makemake_c

    source_files = []
    header_files = []
    library_files = []

    for filename in arg_list:

        ending = filename.split('.')[-1]

        if ending == 'c':
            source_files.append(filename)
        elif ending == 'h':
            header_files.append(filename)
        elif ending in ['a', 'so']:
            library_files.append(filename)
        else:
            abort_ending(ending)

    makemake_c.generate_makefile(working_dir_path, 
                                 source_paths, 
                                 header_paths, 
                                 library_paths, 
                                 source_files, 
                                 header_files, 
                                 library_files, 
                                 force_openmp)

else:
    abort_language()