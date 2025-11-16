import argparse
import re
from models import (
    Result,
    Transactions,
    TransactionsParseResult,
    Report,
    ReportParseResult
)
from dataclasses import dataclass
from pypdf import PdfReader

#                       _              _       
#    ___ ___  _ __  ___| |_ __ _ _ __ | |_ ___ 
#   / __/ _ \| '_ \/ __| __/ _` | '_ \| __/ __|
#  | (_| (_) | | | \__ \ || (_| | | | | |_\__ \
#   \___\___/|_| |_|___/\__\__,_|_| |_|\__|___/
#                                              

TABLE_HEADER_PATTERN = re.compile(
    r'ID\s+Owner\s+Asset\s+Transaction\s+Type\s+Date\s+Notification\s+Date\s+Amount\s+Cap\.\s+Gains\s+>\s+\$200\?',
    re.DOTALL
)
TABLE_FOOTER_PATTERN = re.compile(
    r'\* For the complete list of asset type',
    re.DOTALL
)

#       _       _              _       __ _       _ _   _                 
#    __| | __ _| |_ __ _    __| | ___ / _(_)_ __ (_) |_(_) ___  _ __  ___ 
#   / _` |/ _` | __/ _` |  / _` |/ _ \ |_| | '_ \| | __| |/ _ \| '_ \/ __|
#  | (_| | (_| | || (_| | | (_| |  __/  _| | | | | | |_| | (_) | | | \__ \
#   \__,_|\__,_|\__\__,_|  \__,_|\___|_| |_|_| |_|_|\__|_|\___/|_| |_|___/
#                                                                         

@dataclass
class Args:
    report_file_path: str

# NOTE: In my decision to move more of the parsing logic into the data models
# themselves, I was left with some parsing functionality for the report in
# this script and some in the data model. This is why this funky clash of names
# came about. This script might just need to call a single function in the 
# report data model to consolidate parsing logic there and avoid this clash.
# This will do for now
@dataclass
class ParseReportResult(Result[Report]):
    file_path: str

class TransactionsBlockExtractionResult(Result[str]):
    pass

#   _          _                    __                  _   _                 
#  | |__   ___| |_ __   ___ _ __   / _|_   _ _ __   ___| |_(_) ___  _ __  ___ 
#  | '_ \ / _ \ | '_ \ / _ \ '__| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#  | | | |  __/ | |_) |  __/ |    |  _| |_| | | | | (__| |_| | (_) | | | \__ \
#  |_| |_|\___|_| .__/ \___|_|    |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
#               |_|                                                           

# 1) Extracts the page-delimited raw text from the PDF at the given path
# 2) Concatenates the pages together with a space in between each one
# 3) Cleans the text and returns it
def extract_cleansed_text(report_file_path: str) -> str:
    reader = PdfReader(report_file_path)
    raw_page_texts: list[str] = [p.extract_text() for p in reader.pages]
    raw_text: str = " ".join(raw_page_texts)
    cleansed_text: str = cleanse_raw_text(raw_text)

    return cleansed_text

# Given a full report's worth of text
# 1) Finds matches for the table header
# 2) Removes everything leading up (and including) to the first table 
# header match
# 3) Removes the remaining table header matches alone
# 4) Removes everything after (and including) the first table footer match
def extract_transactions_block(raw_text: str) -> TransactionsBlockExtractionResult:
    table_header_matches: list[re.Match] = list(TABLE_HEADER_PATTERN.finditer(raw_text))

    if not table_header_matches:
        return TransactionsBlockExtractionResult(
            success=False,
            message="No match was found for the table header",
            data=None
        )

    raw_text = raw_text[table_header_matches[0].end():]
    raw_text = re.sub(TABLE_HEADER_PATTERN, '', raw_text)
    table_footer_match = TABLE_FOOTER_PATTERN.search(raw_text)

    if not table_footer_match:
        return TransactionsBlockExtractionResult(
            success=False,
            message="No match was found for the table footer",
            data=None
        )

    raw_text = raw_text[:table_footer_match.start()]
    # NOTE: Randomly, the Filing ID which appears at the top of the report appears
    # at the end of the first page when the report's text is extracted. This
    # might be needed at some point though
    transactions_block = re.sub(r'Filing ID #\d+', '', raw_text).strip()

    return TransactionsBlockExtractionResult(
        success=True,
        message="",
        data=transactions_block
    )

# 1) Removes all null byte ASCII representations
# 2) Replaces contiguous whitespace characters with a single space
def cleanse_raw_text(raw_text: str) -> str:
    cleansed_text = raw_text.replace('\x00', '')
    cleansed_text = re.sub(r'\s+', ' ', cleansed_text)

    return cleansed_text

# 1) Extract the text from the report at the given file path
# 2) Extracts the block of transactions from
# the document's raw text
# 3) Finds the transaction matches using a regex pattern
# 4) Constructs a transaction from each match
# 5) Constructs a report from the raw text and list of transactions, returns report
def parse_report(report_file_path: str) -> ParseReportResult:
    cleansed_text: str = extract_cleansed_text(report_file_path)

    if not cleansed_text:
        return ParseReportResult(
            success=False,
            message="No text was extracted from the report PDF",
            file_path=report_file_path,
            data=None
        )

    tber: TransactionsBlockExtractionResult = extract_transactions_block(cleansed_text)

    if not tber.success:
        return ParseReportResult(
            success=False,
            message=f"Failed to extract transactions block from cleansed report text: {tber.message}",
            file_path=report_file_path,
            data=None
        )

    tpr: TransactionsParseResult = Transactions.from_transactions_block(tber.data)

    if not tpr.success:
        return ParseReportResult(
            success=False,
            message=f"Failed to create transactions from cleansed transactions block: {tpr.message}",
            file_path=report_file_path,
            data=None,
        )
    # NOTE: The report data model came after the script's first draft was created.
    # Not sure I would have constructed it in this way if I had this in mind from
    # the start
    rpr: ReportParseResult = Report.from_cleansed_text(
        cleansed_text, transactions=tpr.data
    )

    return ParseReportResult(
        success=rpr.success,
        message=f"Failed to create report: {rpr.message}" if not rpr.success else "",
        file_path=report_file_path,
        data=None if not rpr.success else rpr.data
    )

def parse_arguments() -> Args:
    parser = argparse.ArgumentParser(
        prog='TODO',
        description='TODO'
    )
    parser.add_argument('filename', help='Path to the financial discloure report to parse')
    args: argparse.Namespace = parser.parse_args()

    if not args.filename:
        raise Exception()
    else:
        return Args(
            report_file_path = args.filename
        )

#                   _       
#   _ __ ___   __ _(_)_ __  
#  | '_ ` _ \ / _` | | '_ \ 
#  | | | | | | (_| | | | | |
#  |_| |_| |_|\__,_|_|_| |_|
#                           

def main():
    a: Args = parse_arguments()
    prr: ParseReportResult = parse_report(a.report_file_path)

    if not prr.success:
        print(prr.message)
    else:
        r: Report = prr.data
        print(prr.file_path)
        print(r.filing_id)
        print(r.representative_name)
        print(r.signed_date)
        print()

        for t in r.transactions:
            print(str(t)+"\n\n")

if __name__ == "__main__":
    main()
