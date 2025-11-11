import argparse
import re
from re import Match
from typing import Optional
from enum import Enum
from datetime import date, datetime
from dataclasses import dataclass
from pypdf import PdfReader

#                       _              _       
#    ___ ___  _ __  ___| |_ __ _ _ __ | |_ ___ 
#   / __/ _ \| '_ \/ __| __/ _` | '_ \| __/ __|
#  | (_| (_) | | | \__ \ || (_| | | | | |_\__ \
#   \___\___/|_| |_|___/\__\__,_|_| |_|\__|___/
#                                              

REPORT_PATTERN = re.compile(r"""
    # 
""", re.VERBOSE | re.DOTALL)

TRANSACTION_PATTERN = re.compile(r"""
    # Asset group (eg. Amazon (AMZN) [ST])
    \s*(.*?\[.*?\])

    # Transaction type group
    \s*([PS])

    # Transaction date group
    \s*(\d{1,2}/\d{1,2}/\d{4})

    # Notification date group
    \s*(\d{1,2}/\d{1,2}/\d{4})

    # Amount range group
    \s*(\$[\d]*[,]*[\d]*\s-\s\$[\d]*[,]*[\d]*)

    # Filing status group
    \s*(F\sS:\sNew)
""", re.VERBOSE | re.DOTALL)
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

@dataclass
class Asset:
    name: str
    type: str
    ticker: Optional[str]
    PATTERN = re.compile("""
        # Name group
        (.*)\s

        # Ticker group
        \((.*)\)\s

        # Type group
        \[(.*)\]
    """, re.VERBOSE | re.DOTALL)

    @staticmethod
    def from_group(g: str):
        m: Match = Asset.PATTERN.search(g)
        match_groups_iterator = iter(m.groups())
        name = next(match_groups_iterator)
        ticker = next(match_groups_iterator)
        type = next(match_groups_iterator)

        return Asset(name, type, ticker)

class FilingStatus(Enum):
    NEW = 1

    @staticmethod
    def from_group(g: str):
        # TODO: Implement based on what other options arise
        if "New" in g:
            return FilingStatus.NEW
        else:
            raise Exception()

class TransactionType(Enum):
    PURCHASE = 1
    SALE = 2

    @staticmethod
    def from_group(g: str):
        if g == "P":
            return TransactionType.PURCHASE
        elif g == "S":
            return TransactionType.SALE
        else:
            # TODO
            raise Exception()

# This is just being extended to implement a method to create an instance
# from a capturing group of it in the transaction regex pattern
class Date(date):
    FORMAT = "%m/%d/%Y"

    @staticmethod
    def from_group(g: str):
        return datetime.strptime(g, Date.FORMAT).date()

@dataclass
class AmountRange:
    min: int
    max: int
    PATTERN = re.compile("""
        # Min group
        \$(\d+)\s

        # Max group
        -\s\$(\d+)
    """, re.VERBOSE | re.DOTALL)

    @staticmethod
    def from_group(g: str):
        # NOTE: Commas are removed in a first pass cus the regex looks
        # worse if we try to create capturing groups that exclude it
        g = re.sub(",", "", g)
        m = AmountRange.PATTERN.search(g)
        match_groups_iterator = iter(m.groups())
        min = int(next(match_groups_iterator))
        max = int(next(match_groups_iterator))

        return AmountRange(min, max)

# Represents a transactino made by a member of the House of 
# Representatives
@dataclass
class Transaction:
    asset: Asset
    filing_status: FilingStatus
    type: TransactionType
    transaction_date: date
    notification_date: date
    # The specific amount for a given transaction is not given in these 
    # reports, only a range is provided
    amount: AmountRange
    # Represents the raw text that was parsed to create this object
    raw_text: str

    @staticmethod
    def from_match(m: Match):
        match_groups_iterator = iter(m.groups())

        asset: Asset = Asset.from_group(next(match_groups_iterator))
        type: TransactionType = TransactionType.from_group(next(match_groups_iterator))
        transaction_date: date = Date.from_group(next(match_groups_iterator))
        notification_date: date = Date.from_group(next(match_groups_iterator))
        amount: AmountRange = AmountRange.from_group(next(match_groups_iterator))
        filing_status = FilingStatus.from_group(next(match_groups_iterator))
        raw_text = m.group()

        return Transaction(
            asset,
            filing_status,
            type,
            transaction_date,
            notification_date,
            amount,
            raw_text
        )

    def is_complete(self) -> bool:
        return (
            self.asset is not None and
            self.filing_status is not None and
            self.type is not None and
            self.transaction_date is not None and
            self.notification_date is not None and
            self.amount is not None
        )

@dataclass
class Report:
    filing_id: int
    representative_name: str
    signed_date: date
    transactions: list[Transaction]

    @staticmethod
    def from_cleansed_text(raw_text: str, transactions: list[Transaction]):
        filing_id = 1
        representative_name = "foo"
        signed_date = date.today()

        return Report(
            filing_id=filing_id,
            representative_name=representative_name,
            signed_date=signed_date,
            transactions=transactions
        )

#   _          _                    __                  _   _                 
#  | |__   ___| |_ __   ___ _ __   / _|_   _ _ __   ___| |_(_) ___  _ __  ___ 
#  | '_ \ / _ \ | '_ \ / _ \ '__| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#  | | | |  __/ | |_) |  __/ |    |  _| |_| | | | | (__| |_| | (_) | | | \__ \
#  |_| |_|\___|_| .__/ \___|_|    |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
#               |_|                                                           

# 1) Extracts the raw text from the PDF at the given path
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
def extract_transactions_block(raw_text: str) -> str:
    table_header_matches: list[Match] = list(TABLE_HEADER_PATTERN.finditer(raw_text))

    if not table_header_matches:
        # TODO: Figure out what to do in this case
        return raw_text

    raw_text = raw_text[table_header_matches[0].end():]
    raw_text = re.sub(TABLE_HEADER_PATTERN, '', raw_text)
    table_footer_match = TABLE_FOOTER_PATTERN.search(raw_text)

    if not table_footer_match:
        # TODO: Figure out what to do in this case
        return raw_text

    raw_text = raw_text[:table_footer_match.start()]
    # NOTE: Randomly, the Filing ID which appears at the top of the report appears
    # at the end of the first page when the report's text is extracted. This
    # might be needed at some point though
    transactions_block = re.sub(r'Filing ID #\d+', '', raw_text).strip()

    return transactions_block

# 1) Removes all null byte ASCII representations
# 2) Replaces contiguous whitespace characters with a single space
def cleanse_raw_text(raw_text: str) -> str:
    cleansed_text = raw_text.replace('\x00', '')
    cleansed_text = re.sub(r'\s+', ' ', cleansed_text)

    return cleansed_text

# 1) Extract the text from the report at the given file path
# 2) Concatenates the text from each page into a single string
# 3) Cleans the document and extracts the block of transactions from
# the document's raw text
# 4) Finds the transaction matches using a regex pattern
# 5) Constructs a transaction from each match
# 6) Constructs a report from the raw text and list of transactions, returns report
def parse_report(report_file_path: str) -> Report:
    cleansed_text: str = extract_cleansed_text(report_file_path)
    transactions_block: str = extract_transactions_block(cleansed_text)
    transaction_matches: list[Match] = list(TRANSACTION_PATTERN.finditer(transactions_block))
    ts: list[Transaction] = [Transaction.from_match(m) for m in transaction_matches]
    # NOTE: I'm adding the Report object after I've created the script to parse 
    # all transactions, so it's easiest to just construct the report from the raw
    # text at this point, though I likely would not have done it this way if I had
    # had the creation of the Report object in mind from the start
    r: Report = Report.from_cleansed_text(cleansed_text, ts)

    return r

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

if __name__ == "__main__":
    a: Args = parse_arguments()
    r: Report = parse_report(a.report_file_path)

    for t in r.transactions:
        print(str(t) + "\n")
