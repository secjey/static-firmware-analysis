#!/usr/bin/env python

"""
This script enables users to perform static analyses of firmware images
based on some rules defined in JSON format.
Custom patterns, files and binaries can be searched.
"""

from __future__ import print_function
import sys, os, subprocess, argparse, re, signal, psutil, time, json, csv, codecs
from terminaltables import AsciiTable, SingleTable

__author__ = "secjey"
__copyright__ = "Copyright 2017"
__credits__ = [""]
__license__ = "GPLv3"
__version__ = "1.0.1"
__maintainer__ = "secjey"
__status__ = "Development"

# the default location of the rules file is in the same dir as this file
RULES_FILE = '{}/rules.json'.format(os.path.dirname(os.path.abspath(__file__)))
MAX_OUTPUT_LINES = 5

# COMMANDS
# -a = to handle unknown encoding
# info: the ack command could also be used
# it is optimized to look for source code
# https://beyondgrep.com
# TODO: --exclude-dir should be an option in the rules.json file
GREP_COMMAND = "grep -sira{0} {2} --exclude-dir=dev --exclude-dir=proc --exclude-dir=sys -E '{1}' . {3}"	# 0 = additional args, 1 = value to lookup, 2 = exclude args, 3 = further processing (e.g. pipes)
FIND_COMMAND = "find . -type f -iname '{0}' {1} {2}"

class bcolors:
    """Defines some ANSI color codes."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

def signal_handler(sig, frame):
    """Handles signals sent by the user.
    In the case the SIGINT signal is received, child processes will be stopped.
    """
    if sig == signal.SIGINT:
        print(bcolors.OKBLUE + "\n[-] The program is stopping..." + bcolors.ENDC)
        procs = psutil.Process().children(recursive=True)
        try:
            for p in procs:
                p.terminate()
                gone, still_alive = psutil.wait_procs(psutil.Process().children(recursive=True), timeout=3)
            for p in still_alive:
                p.kill()
        except:
            pass
        sys.exit(0)

def welcome():
    """Prints the welcome message at the start of the script."""
    print(bcolors.HEADER + """
    Welcome to the FIRMWARE AUTOMATION TOOL - v1.0.1
    This tool performs static analyses of firmware images based on
    custom user rules to look for specific patterns, files and binaries.
    By secjey - https://github.com/secjey
	""" + bcolors.ENDC)

def get_parser():
	"""Parses the arguments passed in the command line."""
	parser = argparse.ArgumentParser(description='DESCRIPTION')
	parser.add_argument('filesystem', help="Path to the extracted filesystem directory")
	parser.add_argument('-o', '--output', metavar="OUTPUT_FILE", help="Path to the output file which contains all information")
#	parser.add_argument('--csv', action="store_true", help="The output file will be in CSV format", default=False)
	parser.add_argument('--rules', metavar="JSON_FILE", help="Path to the file containing the rules in JSON format", default=RULES_FILE)
	return parser

def get_json_input(json_file):
	"""Get json data from a file."""
	with open(json_file, 'r') as data_file:
		data = json.load(data_file)
	data_file.close()
	return data

def union(mylist1, mylist2):
	"""Merges two lists and removes duplicates."""
	return list(set(mylist1) | set(mylist2))

def remove_from(mylist1, mylist2):
	"""Removes items from mylist1 that are in mylist2."""
	return list(set(mylist1) - set(mylist2))

def update_command(data_type, obj_dict, exclude_list):
    """Update the command to execute based on the data type to process and a list of elements to exclude."""

    # updating the exclusion list by looking for specific exclude and include rules
    if "exclude" in obj_dict:
        exclude_list = union(exclude_list, obj_dict["exclude"].split(','))
    if "include" in obj_dict:
        # if the same element is in the exclude and include rule, it will be included
        exclude_list = remove_from(exclude_list, obj_dict["include"].split(','))

    other_args = ""
    # value = obj_dict["value"].decode('unicode_escape') # works only with python 2.x
    # support for python 2.x and 3.x with codecs
    value = codecs.escape_decode(obj_dict["value"])[0].decode('utf8') # will e.g. transform \\ into \
    exclude_args = ""
    further_process = ""

    if exclude_list:
        if data_type == "patterns":
            if "binary" in exclude_list:
                other_args += "I"
            # add every exclude argument apart from "binary" to the exclude parameter
            exclude_args_list = [e for e in exclude_list if e != "binary"]
            # create the string containing the exclude parameter with the arguments contained in the list
            exclude_args = ("--exclude=*.%s" if len(exclude_args_list) == 1 else "--exclude=*.{%s}") % (",".join(map(str,exclude_args_list)))
        elif data_type == "binaries" or data_type =="files":
            # exclude with "-not" or "!" followed by the parameter to exclude
            exclude_args = ("-not -iname '{}'" * len(exclude_list)).format(*exclude_list)

    if data_type == "patterns":
        # if the print_match rule is defined and its value is True, the exact match will be shown
        if "print_match" in obj_dict and obj_dict["print_match"] == True:
            other_args += "oh"
            further_process = "| sort -u"
        # otherwise, the output will only contain the name of the matching file
        else:
            other_args += "l"
        return GREP_COMMAND.format(other_args, value, exclude_args, further_process)

    # look for executable binaries only
    elif data_type == "binaries":
	    further_process = "-exec file -i {} \; | grep 'x-executable; charset=binary' | cut -d: -f1"
			
    return FIND_COMMAND.format(value, exclude_args, further_process)
	
def lookup(filesystem, data):
	"""Looks for the data defined in the JSON file in the chosen filesystem directory
	and returns a dictionary with the output information."""
	# change directory to perform the commands
	# thanks to this, no need to cut the base directory name in the output
	old_dir = os.getcwd()
	os.chdir(filesystem)
	output_info = dict()
	for data_type in data:
		exclude_list = list()
		# get the list of objects (dict type) for each data_type
		objects = data[data_type]["object"]
		# if the exclude rule is defined globally for the whole data type set
		if "exclude" in data[data_type]:
			exclude_list = data[data_type]["exclude"].split(',')
		# loop through each obj and execute the custom command for it
		for obj in objects:
			command = update_command(data_type, obj, exclude_list)
			# universal_newlines to read output in utf-8
			# POSIX shell does not support syntax with curly brackets, use bash instead
			p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True, executable='/bin/bash')
			output, error = p.communicate()
			if output:
				# update the dictionary with the new info
				output_info = update_output_info(output_info, data_type, obj, output)
	
	# lookup finished, back to the script directory
	os.chdir(old_dir)
	return output_info

def cut_output(output):
	"""Cuts the output so that it does not contain more than MAX_OUTPUT_LINES lines."""
	output_list = output.splitlines()
	if len(output_list) > MAX_OUTPUT_LINES:
		output_list[MAX_OUTPUT_LINES:] = ['...'] # replace all values from the MAX_OUTPUT_LINESth position by the single value '...'
	return output_list

def update_output_info(output_info, data_type, obj, output):
	"""Updates the output information by adding important fields from the rules file
	and the output of the command to the output dictionary."""
	obj_out = dict()
	obj_out["data_type"] = data_type
	# if the name rule is defined, its value will be put into parentheses
	if "name" in obj:
		obj_out["name"] = "{}\n({})".format(obj["name"], obj["value"])
	else:
		obj_out["name"] = obj["value"]

	# keep both, the output info that has been cut and the full output info
	obj_out["output_short"] = cut_output(output)
	obj_out["output_full"] = output.splitlines()

	# if the key exists, get the list of objects and append the current object (obj_out) to it
	# otherwise, create a list as value for the key and append the current object to it
	output_info.setdefault(obj["category"], list()).append(obj_out)

	return output_info

def create_table(data, short_version=True, full_version=False):
	"""Creates a table based on the provided data. The full version will contain the full output of each command
	whereas the short version will only contain the first MAX_OUTPUT_LINES lines."""
	table_data_short = list()
	table_data_full = list()

	for category in data:
		# loop through the obj of each category and add rows with the info
		for i, obj in list(enumerate(data[category])):
			# the first item of each category will contain the name of the category
			if i == 0:
				if short_version:
					# add some color codes for the short version, so that the data can be nicely displayed in the console
					table_data_short.append([bcolors.OKGREEN + category.replace('_', ' ').upper() + bcolors.ENDC, obj["data_type"], obj["name"], "\n".join(obj["output_short"])])
				if full_version:
					table_data_full.append([category.replace('_', ' ').upper(), obj["data_type"], obj["name"], "\n".join(obj["output_full"])])
			# following items in the same category will just have the '*' symbol as category name			
			else:
				if short_version:
					table_data_short.append([bcolors.OKGREEN + "*" + bcolors.ENDC, obj["data_type"], obj["name"], "\n".join(obj["output_short"])])
				if full_version:
					table_data_full.append(["*", obj["data_type"], obj["name"], "\n".join(obj["output_full"])])

	tables = [None] * 2
	if short_version:
		table_headers_short = [bcolors.WARNING + "CATEGORY", "DATA TYPE", "NAME", "OUTPUT" + bcolors.ENDC]
		# headers must be the first row
		table_data_short.insert(0, table_headers_short)
		table_short = AsciiTable(table_data_short)
		table_short.inner_row_border = True
		table_short.justify_columns[0] = 'center'
		tables[0] = table_short.table
	if full_version:
		table_headers_full = ["CATEGORY", "DATA TYPE", "NAME", "OUTPUT"]
		table_data_full.insert(0, table_headers_full)
		table_full = AsciiTable(table_data_full)
		table_full.inner_row_border = True
		table_full.justify_columns[0] = 'center'
		tables[1] = table_full.table

	return tables
		
def main():
	welcome()
	parser = get_parser()
	result = parser.parse_args()
	signal.signal(signal.SIGINT, signal_handler) # catch ctrl+c

	if not os.path.isdir(result.filesystem):
		print(bcolors.WARNING + "[!] The path provided is not a valid directory..." + bcolors.ENDC)
		parser.print_help()
		return
	elif result.output and os.path.isfile(result.output):
		print(bcolors.WARNING + "[!] The output file already exists..." + bcolors.ENDC)
		return
	elif not os.path.isfile(result.rules):
		print(bcolors.WARNING + "[!] The rules file could not be found..." + bcolors.ENDC)
		return

	data = get_json_input(result.rules)
	output_json = lookup(result.filesystem, data)
	if result.output:
		short, full = create_table(output_json, full_version=True)
		with open(result.output, 'w') as f:
			f.write(full)
			f.close()
	else:
		short = create_table(output_json)[0]

	print(short)

if __name__ == '__main__':
	main()
