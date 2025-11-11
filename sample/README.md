# Directory Overview

This directory contains a sample of the available financial disclosure reports. Each directory is named after a noteworthy feature of the report/report archetype (useful for improve the robustness of the parser). In each directory is the following:

- `report.pdf`: The original report in its raw form
- `cleansed.txt`: The text extracted from it after cleansing
- `notes.md`: Notes that I've gathered about each one. They're meant to be read in a particular order, but that obviously can't be reconstructed without looking at file metadata and so forth. All of this is to say that insights uncovered in previous reports do not show up again

`script.py` was created to quickly extract the cleansed text from a new report. To use it:

1) Create a directory with a name that sets the report apart. Is it a new kind of report ? Does it have a unique feature to it that has not been considered by the regex patterns in `parse.py`, etc ?
2) Place the report in it as `report.pdf`
3) 

```
$ python script.py <directory-name>
# example
$ python script.py description_section_report
``
