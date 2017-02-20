# makemake.py
makemake.py is a Python script for generating makefiles that can be used with the [GNU Make](https://www.gnu.org/software/make/) utility for compiling source code. Currently supported programming languages are C and Fortran.
## How it works
The script takes a list of source files, and scans their content to determine how the files depend on each other. It then generates a makefile containing compilation and linking rules that take these dependecies into account. An executable can then be produced simply by writing `make`. The makefile contains additional rules for using predefined groups of compiler flags, e. g. using `make debug` will compile with flags useful for debugging.

**Important:** With any automatically generated makefile there is always a chance that some dependencies have been handled incorrectly. This can result in sources not getting recompiled when they should, leading to unexpected behaviour when the program is run. It is therefore important that you always verify the list of dependencies printed by makemake.py when it generates a new makefile.

## Requirements
To run the script you only need to have Python 2.7 installed. To use the makefiles you need to have GNU Make as well. On Linux and OS X it should be installed by default. On Windows you can get it through [GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm). It is also included in [MinGW](http://www.mingw.org/) (in that case the program to run is called `mingw32-make` rather than just `make`).

## Installation
#### Linux/OS X
1. Download the files in the *src* folder to a destination of your choice. If you use Git, you can just clone the repository.
2. Make sure the source folder is included in the PATH environment variable. To include the folder in PATH, you can add the line `export PATH=$PATH:<path to source folder>` to your *.bashrc* file (if you use Linux) or your *.bash_profile* file (if you use OS X). Either should be located in the home directory.
3. Make sure *makemake.py* is allowed to be executed. To make it executable, use `chmod +x makemake.py`.
4. You can now run the script from anywhere by typing `makemake.py <arguments>`.

#### Windows
1. Download the files in the *src* folder to a destination of your choice. If you use Git, you can just clone the repository.
2. Make sure the source folder is included in the PATH environment variable. To include the folder in PATH, go to Control Panel -> System and Security -> System -> Advanced system settings. Click on "Environment Variables...", select "Path" and click "Edit...". Now add the path to the *src* folder.
3. Make sure *makemake.py* will be executed by Python by default. Right-click on *makemake.py* and select "Properties". Click the "Change..." button and choose the python.exe executable. (Note that this will cause all `.py` files to be executed by Python by default, which can be annoying when you just want to open a file for editing. I haven't found a way around this however.)
4. In some cases the arguments to *makemake.py* specified on the command line will not automatically be seen by the Python interpreter. To fix this, start *regedit* and find the `HKEY_CLASSES_ROOT\Applications\python.exe\shell\open\command` registry. Double-click on the "(Default)" entry and make sure that the text string has a `%*` at the end. So if the string reads `"C:\Python27\python.exe" "%1"`, change it to `"C:\Python27\python.exe" "%1" %*`.
5. You can now run the script from anywhere by typing `makemake.py <arguments>`.

## Usage
You can run *makemake.py* without any arguments to get usage instructions in a compact format. Here is a more in-depth description.
#### Arguments
The arguments to *makemake.py* are the names of the files you want to create a makefile for. The arguments are separated by spaces, and any arguments containing spaces must be surrounded with double quotes. The files can either be ordinary source code files (e. g. `.c` or `.f90`), header files (`.h`) that get included in the code or library files (`.a` or `.so`) that are used.

For files residing in the current working directory, only the name of the file needs to be specified. For files lying in a different folder, the absolute path (starting with `/`) or relative path (starting with `./`) must be added in front of the filename.

#### Language and compiler
The script will automatically recognize the programming language based on the file extension of the source files. You can specify the compiler to use with the `-c` flag. Just write the name of the compiler directly following the flag. The default option will be a compiler from the GNU Compiler Collection, i. e. `gcc` for C and `gfortran` for Fortran.

#### Search paths
An alternative to specifying individual paths is to add one or more search paths. For source files this is done with the `-S` flag. Just add `-S` somewhere in the argument list, followed by the (absolute or relative) paths that you want to include in the list of search paths. Then, if the script fails to find a source file in the working directory, it automatically searches the paths specified in the list of search paths. This is useful if you have several source files residing in the same directory. There is an equivalent `-H` flag for header file search paths, and an `-L` flag for library search paths. These can all be combined arbitrarily, so e. g. `-SH` would specify paths to search for both source and header files.

#### Using the makefile
Here is a list of the available arguments you can add after `make`:
- `debug`:   Compiles with flags useful for debugging.
- `fast`:    Compiles with flags for high performance.
- `profile`: Compiles with flags for profiling.
- `gprof`:   Displays the profiling results with gprof.
- `clean`:   Deletes auxiliary files.
- `help`:    Displays a help text.

You can also specify any additional compilation flags to use with the argument `FLAGS="<additional flags>"`.

#### Modifying flag groups
The group of flags used when `debug` or `fast` is added depends on the compiler. You can modify which flags to use, or include flags for more compilers, by editing the *debug_flags.ini* and *performance_flags.ini* files. Each line in these files has the following format: `<compiler>: <flags>`.

#### Multiple makefiles
If compiling the group of source files will result in several executables, one makefile is generated for each executable. Note however that it is not recommended to include multiple executable producing sources that have different dependecies in the same call to makemake.py, as this might cause the script to detect apparent dependencies that you don't want.

By default the script tries to save the newly generated makefile as just `makefile`. If a file of that name already exists, you can opt to choose a different name, or, if the existing makefile was generated by makemake.py, the script can rename the two relevant makefiles to `<executable name>.mk` and create a "wrapper" makefile that allows you to choose which executable you want to create every time you run `make`. All files with the `.mk` extension that are present will be included in this wrapper. If such a wrapper already exists, an entry for the newly generated makefile can be added to it. The `-w` flag will tell the script to generate a makefile wrapper even if it doesn't find it necessary. To create an executable `my_prog.x` via the wrapper, simply write `make my_prog`, and the wrapper will run the relevant makefile. Any arguments for that makefile must be specified in the following way: `make my_prog ARGS="<list of arguments>"`.

