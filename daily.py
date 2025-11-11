from parse import parse_report

# 1) Establishes connection with the database
# 2) Queries for report IDs that don't already exist in the report table
# 3) Writes reports and transactions with the IDs found from the previous
# step to the database
def write_new_reports_to_db(parsed_reports: dict[Report, list[Transaction]]):
    pass

# 1) Parses each report in directory given by the path, extracting a list of
# transactions for each
# 2) Constructs and returns a map from report to the list of extracted 
# transactions, returns it
def parse_reports(report_directory: str) -> dict[Report, list[Transaction]]:
    return {}

# 1) Fetches the PDF links for all reports from the current year
# 2) Writes them to a temporary directory on the runner's disk
# 3) Returns the path to the directory in which they are written
# relative to the directory in which this script is
def download_reports() -> str:
    return ""

#                   _       
#   _ __ ___   __ _(_)_ __  
#  | '_ ` _ \ / _` | | '_ \ 
#  | | | | | | (_| | | | | |
#  |_| |_| |_|\__,_|_|_| |_|
#                           

def main():
    report_directory: str = download_reports()
    parsed_reports: dict[Report, list[Transaction]] = parse_reports(report_directory)
    write_new_reports_to_db(parsed_reports)

main()
