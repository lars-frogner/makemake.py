#!/usr/bin/env python
#
# This program takes a list of Fortran files from the command line, 
# and generates a makefile for building the corresponding executable.
#
# State: Functional
#
# Last modified 21.09.2016 by Lars Frogner
#
import sys, os

class Source:

	# This class parses an inputted .f90 file and stores information
	# about which programs, modules and dependencies it contains.

	def __init__(self, path, filename):

		name_parts = filename.split('.')

		# -- Validate filename
		if name_parts[-1] != 'f90':

			print '(makemake.py) Invalid file extension for \"%s\".' % filename \
				  + ' Must be \".f90\".'
			sys.exit(1)

		try:
			f = open(os.path.join(path, filename), 'r')

		except IOError:

			print '(makemake.py) Couldn\'t open file \"%s\".' % filename
			sys.exit(1)
		# --

		lines = f.readlines()
		f.close()

		self.object_name = '.'.join(name_parts[:-1]) + '.o'
		self.programs = []
		self.modules = []
		self.procedures = []
		self.deps = []

		inside = False

		# Parse source file
		for line in lines:

			words = (line.split('!')[0]).split()

			# Skip blank lines
			if len(words) == 0: continue

			first_word = words[0].lower()
			second_word = '' if len(words) < 2 else words[1].lower()
			third_word = '' if len(words) < 3 else words[2].lower()

			if not inside:

				# Check for program declaration
				if first_word == 'program':

					self.programs.append(second_word)
					inside = 'program'

				# Check for module declaration
				elif first_word == 'module':

					self.modules.append(second_word + '.mod')
					inside = 'module'

				# Check for function declaration
				elif first_word == 'function':

					self.procedures.append(second_word.split('(')[0])
					inside = 'function'

				elif second_word == 'function':

					self.procedures.append(third_word.split('(')[0])
					inside = 'function'

				# Check for subroutine declaration
				elif first_word == 'subroutine':

					self.procedures.append(second_word.split('(')[0])
					inside = 'subroutine'

				# Check for module import statement
				elif first_word == 'use':

					dep = second_word

					# Remove trailing comma if present
					if dep[-1] == ',':
						dep = dep[:-1]

					self.deps.append(dep + '.mod')

			else:

				if first_word == 'end' and second_word == inside:
					inside = False

		# Ignore dependencies on modules in the same file
		for dep in self.deps:
			if dep in self.modules: self.deps.remove(dep)

		# Compilation rule for the makefile
		self.compile_rule_declr = '\n\n%s\n%s%s: %s%s ' \
								  % ('# Rule for compiling ' + filename,
									 self.object_name + (' ' if len(self.modules) != 0 else ''),
									 ' '.join(self.modules), 
									 filename + (' ' if len(self.deps) != 0 else ''),
									 ' '.join(self.deps))
		self.compile_rule = '\n\t$(COMP) -c $(FLAGS) %s' % filename

if len(sys.argv) < 2:

	print '(makemake.py) Usage: makemake.py source1.f90 source2.f90 ...'
	sys.exit(1)

# Get path to directory this script was run from
source_path = os.getcwd()

# Read filenames from command line and turn them into Source instances
sources = [Source(source_path, filename) for filename in sys.argv[1:]]

# -- Collect all program, module and dependency names
all_programs = []
all_modules = []
all_procedures = []
all_deps = []

for src in sources:

	all_programs += src.programs
	all_modules += src.modules
	all_procedures += src.procedures
	all_deps += src.deps
# --

print all_procedures

# Only one executable can be built
if len(all_programs) != 1:
	print '(makemake.py) There must be exactly one program in all the sources combined.'
	sys.exit()

# -- Check for missing dependencies
missing_deps = []
for dep in all_deps:

	if not dep in all_modules:
		missing_deps.append(dep)

if len(missing_deps) != 0:

	print '(makemake.py) Missing dependencies: %s' % ' '.join(missing_deps)
	sys.exit(1)

# -- Determine which objects each source depends on
compile_rules = []

# For each source
for src in sources:

	dep_obects = []

	# For each dependency the source has
	for dep in src.deps:

		# Loop through all the other sources
		for src2 in sources:

			if not (src2 is src):

				# Add object name if it has the correct module
				if dep in src2.modules:
					dep_obects.append(src2.object_name)

	# Get rid of duplicate object names
	dep_obects = list(set(dep_obects))

	# Update prerequisites section of compile rule and store in list
	compile_rules.append(src.compile_rule_declr + ' '.join(dep_obects) + src.compile_rule)
# --

# Create makefile
makefile = '''# Define variables
COMP = gfortran
EXECNAME = %s
OBJECTS = %s
MODULES = %s
FLAGS = 

# Make sure certain rules are not activated by the presence of files
.PHONY: all debug fast set_debug_flags set_fast_flags clean

# Define default target group (call 'make' to use)
all: $(EXECNAME)

# Define optional target groups (call 'make <name of target group>' to use)
debug: set_debug_flags $(EXECNAME)
fast: set_fast_flags $(EXECNAME)

# Defines appropriate compiler flags for debugging
set_debug_flags:
	$(eval FLAGS = -Og -Wall -Wextra -Wconversion -pedantic -Wno-tabs -fbounds-check -ffpe-trap=zero,overflow)

# Defines appropriate compiler flags for high performance
set_fast_flags:
	$(eval FLAGS = -O2)

# Rule for linking object files
$(EXECNAME): $(OBJECTS)
	$(COMP) -o $(EXECNAME) $(OBJECTS)%s

# Action for removing all auxiliary files (call 'make clean' to use)
clean:
	rm -f $(OBJECTS) $(MODULES)''' \
% (all_programs[0],
   ' '.join([src.object_name for src in sources]),
   ' '.join(all_modules),
   ''.join(compile_rules))

# -- Save makefile
makefilepath = os.path.join(source_path, 'makefile')
writeFile = True

if os.path.exists(makefilepath):

	# Ask user before overwriting any existing makefiles
	yn = ''
	while not yn in ['y', 'n']:
		yn = raw_input('(makemake.py) A makefile already exists. Overwrite? [Y/n]\n').lower()

	if yn == 'n':

		writeFile = False
		print '(makemake.py) Makefile generation cancelled.'

if writeFile:

	f = open(makefilepath, 'w')
	f.write(makefile)
	f.close()
	print '(makemake.py) New makefile generated (%s).' % makefilepath