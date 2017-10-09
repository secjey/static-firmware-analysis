# Static firmware analysis

[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/secjey/static-firmware-analysis/issues)

## Description

This project has been inspired by "firmwalker", a tool developed by [Smith](https://github.com/craigz28/firmwalker), which enables users to search for files of interest in an extracted firmware file system. Unfortunately, rules that are used in this tool to detect files are too restrictive as they do not handle wildcards, which means they are likely to miss important files. Moreover, some rules are hard-coded in the script which makes it difficult to extend with other rules and obtain a flexible solution.

To tackle this latter problem and have a more robust tool designed to be easily expanded with new rules, a python tool has been implemented from scratch. Thanks to all the rules being defined in a JSON file, users can customise their search according to their needs. Regular expressions for hashes, URLs, e-mails, files and binaries can be searched. Moreover, various parameters are pre-defined to e.g. let users group items into categories or exclude specific files in their search. This tool represents a good starting point when performing static analysis of file systems. The python tool will automatically look for the following:

* keywords related to potential sensitive information such as root, password, backdoor, shell, WEP.
* IP addresses, email addresses, URLs.
* Files of interest such as /etc/passwd, /etc/shadow, SSL and SSH keys, configuration files, scripts, source code.
* Binaries of interest in embedded systems and IoT devices such as web server's binaries, busybox, FTP and SSH server's binaries.
* Potential MD5/SHA1 hashes in any type of file.

## Installation

```sh
$ git clone https://github.com/secjey/static-firmware-analysis
$ cd static-firmware-analysis 
$ pip install -r requirements.txt
$ chmod +x static_analysis.py
```

## Usage

```
$ python static_analysis.py --help
	
usage: static_analysis.py [-h] [-o OUTPUT_FILE] [--rules JSON_FILE] filesystem

DESCRIPTION

positional arguments:
  filesystem            Path to the extracted filesystem directory

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_FILE, --output OUTPUT_FILE
                        Path to the output file which contains all information
  --rules JSON_FILE     Path to the file containing the rules in JSON format
```

Using this tool is straightforward: Simply provide the path to the extracted file system root directory as follows:

```
./static_analysis.py /path/to/rootfs
```

This tool can be used as it is, thanks to basic rules pre-defined in `rules.json`. However, if you want to customise the rules in order to identify further information in the root file system, have a look at the [JSON structure](#id-json-structure).

By default, the output will be displayed in the console, but it will only contain X matches for each object (shortened version). In the case there are more results, a `...` will be added. This is useful to have a quick overview. In the case you want to see all information (full version), you need to provide a path for the output file as follows:

```
./static_analysis.py /path/to/rootfs -o output.txt
```

### Output

The output information will be displayed in a table as follows:

| CATEGORY | DATA TYPE | NAME | OUTPUT
| :---: | --- | --- | --- |
| [`category`](#id-category) | "patterns" \| "binaries" \| "files" | [`name`](#id-name) (if defined) and [`value`](#id-value) | File or data that matches the rule defined by [`value`](#id-value)
| * | ... | ... | 1st match<br>2nd match<br>3rd match
| Other [`category`](#id-category) | ... | ... | ...
| * | ... | ... | ...

## Demo

[![asciicast](https://asciinema.org/a/131575.png)](https://asciinema.org/a/131575)

## Rules

Thanks to the rules defined in a JSON format, users can customize their search according to their needs. You can easily edit the `rules.json` file with a [JSON editor](http://www.jsoneditoronline.org).

### <a id="id-json-structure">JSON structure</a>

The current JSON structure to describe the user-defined rules is as follows:

![JSON structure](images/json_structure.png)

In each category (i.e. `patterns`, `binaries` and `files`), there is a list of objects that can contain multiple [keys](#id-keys) such as `category` and `value`:

![JSON object](images/json_object.png)

### <a id="id-keys">Keys</a>

* For `patterns`, `binaries` and `files` objects:
    * <a id="id-category">`category`</a> (**mandatory**): Its value describes the category the object belongs to (e.g. script, sensitive info, webserver, ...).
    * <a id="id-value">`value`</a> (**mandatory**): This is the string, regexp or file you want to look for.
    * <a id="id-name">`name`</a> (optional): This is the key to add a meaningful name to your regexp. If this key is defined, it will be displayed in the output alongside the `value`.
    * `exclude` defined locally (optional): Its value will be excluded from the search for the specific object only. For instance, defining `"exclude": "html,js"` alongside `"value": "admin"` in an object will exclude every html _and_ js file that might contain the value "admin".
    * `exclude` defined globally (optional): Its value will be excluded from the search for every object in the list of objects.
    * `include` defined locally (optional): Its value will be included to the search. This is useful if you would like to globally exclude a file type but still include it for a specific object. In the case a value is locally excluded and locally included at the same time, the value will be _included_.

* For `patterns` objects only:
    * `print_match` (optional): By default, the output will only display the file that contains the data. You can change this behaviour by adding a key `"print_match": true` to display the exact match instead. This is particularly useful for regexp where you want to extract information such as URLs, e-mails and the like.

### Values

Using the value "binary" for the keys `exclude` or `include` in `patterns` will exclude/include binary files in the search.

## Contributing

All your bug reports and feature ideas are highly appreciated, thanks in advance! Please add a star if you like the content of this repository! The more people interested in this content, the more features will be added in the near future.

If you would like to contribute but you don't know what to implement, here is the task list:

### Tasks

- [ ] Add support for the keys `exclude-dir` and `include-dir` to exclude/include directories
- [ ] Write a unittest with pytest
- [ ] Add other `rules.json` templates to meet specific requirements (e.g. specific vendor)
- [ ] Perform further analysis if files such as certificates or ssh configuration files are found
- [x] Update the README

## License

>You can check out the full license [here](https://github.com/secjey/static-firmware-analysis/blob/master/LICENSE)

This project is licensed under the terms of the **GPLv3** license.
