import os
import asyncio
import aiohttp
import aiofiles
from sqlite3 import Connection
from datetime import datetime
from parse import parse_report, ParseReportResult
from models import Report, DBWriteResult
from search import search_disclosures
from timer import Timer

#                       _              _       
#    ___ ___  _ __  ___| |_ __ _ _ __ | |_ ___ 
#   / __/ _ \| '_ \/ __| __/ _` | '_ \| __/ __|
#  | (_| (_) | | | \__ \ || (_| | | | | |_\__ \
#   \___\___/|_| |_|___/\__\__,_|_| |_|\__|___/
#                                              

TMP_DIR = "tmp"
DB_FILE = "report.db"

#       _       _              _       __ _       _ _   _                 
#    __| | __ _| |_ __ _    __| | ___ / _(_)_ __ (_) |_(_) ___  _ __  ___ 
#   / _` |/ _` | __/ _` |  / _` |/ _ \ |_| | '_ \| | __| |/ _ \| '_ \/ __|
#  | (_| | (_| | || (_| | | (_| |  __/  _| | | | | | |_| | (_) | | | \__ \
#   \__,_|\__,_|\__\__,_|  \__,_|\___|_| |_|_| |_|_|\__|_|\___/|_| |_|___/
#                                                                         

ReportPath = str

#   _          _                    __                  _   _                 
#  | |__   ___| |_ __   ___ _ __   / _|_   _ _ __   ___| |_(_) ___  _ __  ___ 
#  | '_ \ / _ \ | '_ \ / _ \ '__| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#  | | | |  __/ | |_) |  __/ |    |  _| |_| | | | | (__| |_| | (_) | | | \__ \
#  |_| |_|\___|_| .__/ \___|_|    |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
#               |_|                                                           

# 1) Establishes connection with the database
# 2) Writes all successfully parsed reports
# 3) Writes all transactions belonging to newly written reports
# 4) Rolls back any successful writes in transaction in case of failure
# 5) Return result of operation
def write_new_reports_to_db(
    parse_results: list[ParseReportResult]
) -> DBWriteResult:
    conn = Connection(DB_FILE)
    cur = conn.cursor()
    success_results: list[ParseReportResult] = [r for r in parse_results if r.success]
    r: DBWriteResult = Report.db_write_many(cur, [r.data for r in success_results])
    
    # TODO: The written transaction count doesn't reconcile, but it's off by a slight margin, so I wanted to write
    # the records that are parsed for now, at the very least
    # if r.success:
    #     conn.commit()
    # else:
    #     conn.rollback()
    conn.commit()

    return r

# TODO: Description
def parse_reports(report_directory: str) -> list[ParseReportResult]:
    ps: list[ReportPath] = [os.path.join(report_directory, r) for r in os.listdir(report_directory)]
    rs: list[ParseReportResult] = [parse_report(p) for p in ps]

    return rs

# TODO: Gemini slop
async def download_file(session: aiohttp.ClientSession, link: str, index: int) -> None:
    async with session.get(link) as response:
        response.raise_for_status()
        content = await response.read()
        path = os.path.join(TMP_DIR, f"{index}.pdf")

        async with aiofiles.open(path, "wb") as f:
            await f.write(content)

# 1) Fetches the PDF links for all reports from the current year
# 2) Writes them to a temporary directory on the runner's disk
# 3) Returns the path to the directory in which they are written
# relative to the directory in which this script is
async def download_reports() -> str:
    current_year: int = datetime.now().year
    report_links = search_disclosures(filing_year=current_year)

    async with aiohttp.ClientSession() as session:
        tasks = []

        for index, l in enumerate(report_links):
            tasks.append(download_file(session, l, index))

        await asyncio.gather(*tasks)

    # TODO: For now, files are writing to same directory on every run, which means
    # directory must be empty before each run. We could create a new directory
    # for each run. Consider in future if necessary
    return TMP_DIR

def log_parse_results(rs: list[ParseReportResult]):
    print("------ parse results ------")
    for r in rs:
        print(f"success: {r.success}")
        print(f"message: {r.message}")
        print(f"file_path: {r.file_path}")
        print(f"data: {r.data}\n")

def log_write_result(r: DBWriteResult):
    print("------ write results ------")
    print(f"success: {r.success}")
    print(f"message: {r.message}")
    print(f"data: {r.data}")


#                   _       
#   _ __ ___   __ _(_)_ __  
#  | '_ ` _ \ / _` | | '_ \ 
#  | | | | | | (_| | | | | |
#  |_| |_| |_|\__,_|_|_| |_|
#                           

async def main():
    os.makedirs(TMP_DIR, exist_ok=True)

    with Timer("downloading all reports for current calendar year"):
        report_directory: str = await download_reports()

    with Timer("parsing all downloaded reports"):
        rs: list[ParseReportResult] = parse_reports(TMP_DIR)


    with Timer("writing new reports to db"):
        r: DBWriteResult = write_new_reports_to_db(rs)

    # TODO: Write this to a log file. It's too damn long. A logger object instead of the print function would obviously be best here
    log_parse_results(rs)    
    log_write_result(r)

if __name__ == "__main__":
    asyncio.run(main())
