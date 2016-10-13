#!/usr/bin/env python
#
# This program takes a list of Fortran files from the command line, 
# and generates a makefile for building the corresponding executable.
#
# State: Functional
#
# Last modified 13.10.2016 by Lars Frogner
#
import sys, os

class Source:

	# This class parses an inputted .f90 file and stores information
	# about which programs, modules, external procedures and 
	# dependencies it contains.

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
		self.mod_deps = []
		self.proc_deps = []

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

			words = words.replace(',', ' ') 				 # Treat "," as word separator
			words = words.replace('::', ' :: ')				 # Ensure separation at "::"
			words = [word.lower() for word in words.split()] # List of words in lowercase

			n_words = len(words)

			first_word = words[0]
			second_word = '' if n_words < 2 else words[1]
			third_word = '' if n_words < 3 else words[2]

			# External scope declarations
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

			# Internal scope declarations
			else:

				# Check for module import statement
				if first_word == 'use':

					dep = second_word

					# Remove trailing comma if present
					if dep[-1] == ',':
						dep = dep[:-1]

					self.mod_deps.append(dep + '.mod')

				# Check for declaration of external procedure
				elif 'external' in words:

					ext_idx = words.index('external')

					if '::' in words:

						sep_idx = words.index('::')
						self.proc_deps += words[sep_idx+1:]

					else:
						self.proc_deps += words[ext_idx+1:]

				# Check for end of external scope
				elif first_word == 'end' and second_word == inside:
					inside = False

		# Ignore dependencies on modules and procedures in the same file
		for dep in list(self.mod_deps):
			if dep in self.modules: self.mod_deps.remove(dep)
		for dep in list(self.proc_deps):
			if dep in self.procedures: self.proc_deps.remove(dep)

		# Compilation rule for the makefile
		self.compile_rule_declr = '\n\n%s\n%s%s: %s%s ' \
								  % ('# Rule for compiling ' + filename,
									 self.object_name + (' ' if len(self.modules) != 0 else ''),
									 ' '.join(self.modules), 
									 filename + (' ' if len(self.mod_deps) != 0 else ''),
									 ' '.join(self.mod_deps))
		self.compile_rule = '\n%s\t$(COMP) -c $(FLAGS) %s' \
							% (('\trm -f %s\n' % (' '.join(self.modules))) if len(self.modules) != 0 else '', 
							   filename)

if len(sys.argv) < 2:

	print '(makemake.py) Usage: makemake.py source1.f90 source2.f90 ...'
	sys.exit(1)

# Get path to the directory this script was run from
source_path = os.getcwd()

# -- Determine which compiler to use
command_arguments = sys.argv[1:]

if '-p' in command_arguments:

	command_arguments.remove('-p')
	compiler = 'mpif90'
else:
	compiler = 'gfortran'
# --

# Read filenames from command line and turn them into Source instances
sources = [Source(source_path, filename) for filename in command_arguments]

# -- Collect all program, module, procedure and dependency names
all_programs = []
all_modules = []
all_procedures = []
all_mod_deps = []
all_proc_deps = []

for src in sources:

	all_programs += src.programs
	all_modules += src.modules
	all_procedures += src.procedures
	all_mod_deps += src.mod_deps
	all_proc_deps += src.proc_deps
# --

# Only one executable can be built
if len(all_programs) != 1:
	print '(makemake.py) There must be exactly one program in all the sources combined.'
	sys.exit()

# -- Check for missing dependencies

missing_mod_deps = []
for dep in all_mod_deps:
	if not dep in all_modules: missing_mod_deps.append(dep)

if len(missing_mod_deps) != 0:

	print '(makemake.py) Missing module dependencies: %s' % ' '.join(missing_mod_deps)
	sys.exit(1)

missing_proc_deps = []
for dep in all_proc_deps:
	if not dep in all_procedures: missing_proc_deps.append(dep)

if len(missing_proc_deps) != 0:

	print '(makemake.py) Missing procedure dependencies: %s' % ' '.join(missing_proc_deps)
	sys.exit(1)

# -- Determine which objects each source depends on
compile_rules = []

# For each source
for src in sources:

	dep_obects = []

	# For each module dependency the source has
	for dep in src.mod_deps:

		# Loop through all the other sources
		for src2 in sources:

			if not (src2 is src):

				# Add object name if it has the correct module
				if dep in src2.modules:
					dep_obects.append(src2.object_name)

	# Repeat for procedure dependencies
	for dep in src.proc_deps:

		for src2 in sources:

			if not (src2 is src):

				if dep in src2.procedures:
					dep_obects.append(src2.object_name)

	# Get rid of duplicate object names
	dep_obects = list(set(dep_obects))

	# Update prerequisites section of compile rule and store in list
	compile_rules.append(src.compile_rule_declr + ' '.join(dep_obects) + src.compile_rule)
# --

# Create makefile
makefile = '''
# This makefile was generated by makemake.py.
# 
# Usage:
# 'make':       Compiles with no compiler flags.
# 'make debug': Compiles with flags useful for debugging.
# 'make fast':  Compiles with flags for high performance.
# 'make clean': Deletes auxiliary files.

# Define variables
COMP = %s
EXECNAME = %s
OBJECTS = %s
MODULES = %s
FLAGS = 

# Make sure certain rules are not activated by the presence of files
.PHONY: all debug fast set_debug_flags set_fast_flags clean

# Define default target group
all: $(EXECNAME)

# Define optional target groups
debug: set_debug_flags $(EXECNAME)
fast: set_fast_flags $(EXECNAME)

# Defines appropriate compiler flags for debugging
set_debug_flags:
	$(eval FLAGS = -Og -Wall -Wextra -Wconversion -pedantic -Wno-tabs -fbounds-check -ffpe-trap=zero,overflow)

# Defines appropriate compiler flags for high performance
set_fast_flags:
	$(eval FLAGS = -O3)

# Rule for linking object files
$(EXECNAME): $(OBJECTS)
	$(COMP) -o $(EXECNAME) $(OBJECTS)%s

# Action for removing all auxiliary files
clean:
	rm -f $(OBJECTS) $(MODULES)''' \
% (compiler,
   all_programs[0],
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