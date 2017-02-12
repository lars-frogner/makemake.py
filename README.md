# makemake.py
makemake.py is a Python script for generating makefiles that can be used with the GNU make utility for compiling source code. Currently supported programming languages are C and Fortran.
### How it works
The script takes a list of source files, and scans their content to determine how the files depend on each other. It then generates a makefile containing rules for compiling and linking the source files.
### Installation
1. Download the files in the *src* folder to a destination of your choice.
2. Make sure *makemake.py* is allowed to be executed. To make it executable, use `chmod +x makemake.py`.
3. Make sure the source folder is included in the PATH environment variable. To include the folder in PATH, you can add the line `export PATH=$PATH:<path to source folder>` to your *.bashrc* file (located in the home directory).
You can now run the script from anywhere by typing `makemake.py <arguments>`.
### Usage
