#!/usr/bin/env python
#
# This program takes a list of Fortran or C source files from the 
# command line, and generates a makefile for building the corresponding 
# executable.
#
# State: Functional
#
# Last modified 14.01.2017 by Lars Frogner
#
import sys, os

def abort():

    print '(makemake.py) Usage: makemake.py [-openmp] [path1/]source1.(f90|c|h) [path2/]source2.(f90|c|h) ...'
    sys.exit(1)

if len(sys.argv) < 2: abort()

use_openmp = False

# Get path to the directory this script was run from
source_path = os.getcwd()

source_list = sys.argv[1:]

# Check if user says to use OpenMP
if '-openmp' in source_list:

    use_openmp = True
    source_list.remove('-openmp')

# Run relevant makemake code
if source_list[0].split('.')[-1] == 'f90':

    import makemake_f
    makemake_f.generate_f90_makefile(source_list, source_path, use_openmp=use_openmp)

elif source_list[0].split('.')[-1] in ['c', 'h']:

    import makemake_c
    makemake_c.generate_c_makefile(source_list, source_path, use_openmp=use_openmp)

else:
    abort()