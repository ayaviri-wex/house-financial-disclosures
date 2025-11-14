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

DATE_PATTERN = r"\d{1,2}/\d{1,2}/\d{4}"
ASSET_PATTERN = r".*?\[.*?\]"
MONETARY_AMOUNT_PATTERN = r"\$[\d,]*"
SUBHOLDING_OF_PATTERN = r"S\sO:"
DESCRIPTION_PATTERN = r"D:"
COMMENT_PATTERN = r"C:"
TRANSACTION_PATTERN = re.compile(fr"""
    # Asset group (eg. Amazon (AMZN) [ST])
    \s*(?P<asset>{ASSET_PATTERN})

    # Transaction type group
    \s*(?P<type>
    P
    |
    S\s*(?:\(partial\))? # Matches "S" or "S (partial)"
    )

    # Transaction date group
    \s*(?P<transaction_date>{DATE_PATTERN})

    # Notification date group
    \s*(?P<notification_date>{DATE_PATTERN})

    # Amount range group
    \s*(?P<amount_range>{MONETARY_AMOUNT_PATTERN}\s-\s{MONETARY_AMOUNT_PATTERN})

    # Filing status group (Required starting point of transaction footer)
    \s*F\sS:\s(?P<filing_status>.*?)\s
    (?=({SUBHOLDING_OF_PATTERN}|{DESCRIPTION_PATTERN}|{COMMENT_PATTERN}|\Z|{ASSET_PATTERN}))

    # Subholding of group (Optional)
    (?:\s*{SUBHOLDING_OF_PATTERN}\s*(?P<subholding_of>.*?)\s
    (?=({DESCRIPTION_PATTERN}|{COMMENT_PATTERN}|\Z|{ASSET_PATTERN})))?

    # Comment group (Optional)
    (?:\s*{COMMENT_PATTERN}\s*(?P<comment>.*?)\s
    (?=({DESCRIPTION_PATTERN}|\Z|{ASSET_PATTERN})))?

    # Description group (Optional)
    (?:\s*{DESCRIPTION_PATTERN}\s*(?P<description>.*?)\s
    (?=({COMMENT_PATTERN}|\Z|{ASSET_PATTERN})))?

    # Lookahead: Assert that the transaction is followed by the start of a new one
    # or the end of the entire string, which prevents the final optional group from
    # consuming the start of the next transaction asset
    (?=\s*({ASSET_PATTERN}|\Z))
""", re.VERBOSE | re.DOTALL)
TABLE_HEADER_PATTERN = re.compile(
    r'ID\s+Owner\s+Asset\s+Transaction\s+Type\s+Date\s+Notification\s+Date\s+Amount\s+Cap\.\s+Gains\s+>\s+\$200\?',
    re.DOTALL
)
TABLE_FOOTER_PATTERN = re.compile(
    r'\* For the complete list of asset type',
    re.DOTALL
)

# NOTE: The only reason the following two patterns aren't combined into one and
# stored as a static variable of the Report class is because the order of these
# 3 attributes isn't fixed. The filing ID could come after the signing date for
# single page reports, and I don't want to make the pattern to unwieldy to 
# accommodate for this
FILING_ID_PATTERN = re.compile(
    r'Filing ID #([\d]+)',
    re.DOTALL
)
REP_NAME_AND_SIGNING_DATE_PATTERN = re.compile(fr"""
    # Representative name group
    Signed:\sHon\.\s(.+?)\s,

    # Signing date group
    \s({DATE_PATTERN})
""", re.VERBOSE | re.DOTALL)

# Signed: Hon\. (.+?) ,
# # Signing date group
# \s({DATE_PATTERN})

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
        # Name group (required)
        (?P<name>.*?)\s

        # Ticker group (optional)
        (?:
            \((?P<ticker>.*)\)\s
        )?

        # Type group (required)
        \[(?P<type>.*?)\]
    """, re.VERBOSE | re.DOTALL)

    @staticmethod
    def from_group(g: str):
        m: Match = Asset.PATTERN.search(g)
        name = m.group("name")
        ticker = m.group("ticker")
        type = m.group("type")

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
    SALE_PARTIAL = 3

    @staticmethod
    def from_group(g: str):
        if g == "P":
            return TransactionType.PURCHASE
        elif g == "S":
            return TransactionType.SALE
        elif g == "S (partial)":
            return TransactionType.SALE_PARTIAL
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
    type: TransactionType
    transaction_date: date
    notification_date: date
    amount: AmountRange
    filing_status: FilingStatus
    subholding_of: Optional[str]
    description: Optional[str]
    comment: Optional[str]
    raw_text: str

    @staticmethod
    def from_match(m: Match):
        asset = Asset.from_group(m.group("asset"))
        type = TransactionType.from_group(m.group("type"))
        transaction_date = Date.from_group(m.group("transaction_date"))
        notification_date = Date.from_group(m.group("notification_date"))
        amount = AmountRange.from_group(m.group("amount_range"))
        filing_status = FilingStatus.from_group(m.group("filing_status"))
        subholding_of = m.group("subholding_of")
        description = m.group("description")
        comment = m.group("comment")
        raw_text = m.group()

        return Transaction(
            asset,
            type,
            transaction_date,
            notification_date,
            amount,
            filing_status,
            subholding_of,
            description,
            comment,
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
        filing_id_match = FILING_ID_PATTERN.search(raw_text)

        if not filing_id_match:
            # TODO
            raise Exception()

        # NOTE: This group matches to digits only, so this conversion should work
        filing_id = int(filing_id_match.group(1))
        rep_name_and_signing_date_match = REP_NAME_AND_SIGNING_DATE_PATTERN.search(raw_text)

        if not rep_name_and_signing_date_match:
            # TODO
            raise Exception()

        match_groups_iterator = iter(rep_name_and_signing_date_match.groups())
        representative_name = next(match_groups_iterator)
        signed_date = Date.from_group(next(match_groups_iterator))

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
def parse_report(report_file_path: str) -> Optional[Report]:
    cleansed_text: str = extract_cleansed_text(report_file_path)

    if not cleansed_text:
        return None

    transactions_block: str = extract_transactions_block(cleansed_text)

    if not transactions_block:
        return None

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
    print(a.report_file_path)
    r: Optional[Report] = parse_report(a.report_file_path)

    if not r:
        print("no report found")
    else:
        print(f"""
        filing_id: {r.filing_id}
        representative_name: {r.representative_name}
        signed_date: {r.signed_date}

        """)

        for t in r.transactions:
            print(str(t) + "\n\n\n")
