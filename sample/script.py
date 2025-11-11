import sys
import os
import argparse
from dataclasses import dataclass

#       _       _              _       __ _       _ _   _                 
#    __| | __ _| |_ __ _    __| | ___ / _(_)_ __ (_) |_(_) ___  _ __  ___ 
#   / _` |/ _` | __/ _` |  / _` |/ _ \ |_| | '_ \| | __| |/ _ \| '_ \/ __|
#  | (_| | (_| | || (_| | | (_| |  __/  _| | | | | | |_| | (_) | | | \__ \
#   \__,_|\__,_|\__\__,_|  \__,_|\___|_| |_|_| |_|_|\__|_|\___/|_| |_|___/
#                                                                         

@dataclass
class Arguments:
    directory_name: str

#   _          _                    __                  _   _                 
#  | |__   ___| |_ __   ___ _ __   / _|_   _ _ __   ___| |_(_) ___  _ __  ___ 
#  | '_ \ / _ \ | '_ \ / _ \ '__| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#  | | | |  __/ | |_) |  __/ |    |  _| |_| | | | | (__| |_| | (_) | | | \__ \
#  |_| |_|\___|_| .__/ \___|_|    |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
#               |_|                                                           

def parse_arguments() -> Arguments:
    p = argparse.ArgumentParser(
        description="Takes the name of a directory with a report in it and extracts the cleansed text from it into the same directory" 
    )
    p.add_argument("directory_name", help="Name of directory in which report lives")
    args: argparse.Namespace = p.parse_args()

    if not args.directory_name:
        raise Exception("Directory name is missing")
    else:
        return Arguments(args.directory_name)

def add_parent_dir_to_path() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)

    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

#                   _       
#   _ __ ___   __ _(_)_ __  
#  | '_ ` _ \ / _` | | '_ \ 
#  | | | | | | (_| | | | | |
#  |_| |_| |_|\__,_|_|_| |_|
#                           

if __name__ == "__main__":
    """
    Usage:
    python script.py <directory-name>

    Assumptions:
    - The parse.py script lives in the parent directory
    - The name of the directory the report lives in exists, and the report is in 
    it, named `report.pdf`
    """
    a: Arguments = parse_arguments()
    add_parent_dir_to_path()
    import parse
    report_path = os.path.join(a.directory_name, "report.pdf")
    cleansed_text = parse.extract_cleansed_text(report_path)

    with open(os.path.join(a.directory_name, "cleansed.txt"), "w") as cleansed_text_file:
        cleansed_text_file.write(cleansed_text)
