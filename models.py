import re
import sqlite3
import zlib
from dataclasses import dataclass
from typing import Optional, TypeVar, Generic
from enum import Enum
from datetime import date, datetime
from db import DBWrite, create_placeholders_string

T = TypeVar("T")

@dataclass
class Result(Generic[T]):
    success: bool
    message: str # Always empty if success is True
    data: Optional[T] # _Almost_ always present if success is True

"""
Below are models of the data available in the Periodic Transaction Report (PTR)
filings of House Financial Disclosure report database. Here are some notes
common to all models

Parsing:
- The GROUP_PATTERN attribute is meant to match the attributes of the model in a
block of text that _just_ contains the model's data. For this reason, it'll contain
named capture groups for the easy construction of the model instance
- The PATTERN attribute is to match the object in a larger block of text (ie. that
contains the model's data along with data from other models). This attribute likely 
does not have (named) capture groups, as it's meant for embedding in a larger pattern.
For this reason, too, the pattern is not compiled, as compiled patterns cannot be
embedded in another pattern
- The result of the separation from above is that there is some duplicate logic across
the two patterns, as they represent the same model, just with a different level of
granularity each

ORM:
"""

class AssetParseResult(Result["Asset"]):
    pass

# Represents the asset transacted upon
@dataclass
class Asset:
    name: str
    type: str
    ticker: Optional[str]
    PATTERN = r".*?\[.*?\]"
    GROUP_PATTERN = re.compile(r"""
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
    def from_match(g: str) -> AssetParseResult:
        m: Optional[re.Match] = Asset.GROUP_PATTERN.search(g)

        if not m:
            return AssetParseResult(
                success=False,
                message=f"Asset attributes could not be extracted from asset pattern match '{g}'",
                data=None
            )

        name = m.group("name")
        ticker = m.group("ticker")
        type = m.group("type")
        a = Asset(name, type, ticker)

        return AssetParseResult(
            success=True,
            message="",
            data=a
        )

class FilingStatusParseResult(Result["FilingStatus"]):
    pass

class FilingStatus(Enum):
    NEW = "new"

    @staticmethod
    def from_match(g: str) -> FilingStatusParseResult:
        if g == "New":
            return FilingStatusParseResult(
                success=True,
                message="",
                data=FilingStatus.NEW
            )
        else:
            return FilingStatusParseResult(
                success=False,
                message=f"Filing status '{g}' not recognized",
                data=None
            )

class TransactionTypeParseResult(Result["TransactionType"]):
    pass

class TransactionType(Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    SALE_PARTIAL = "partial sale"

    @staticmethod
    def from_match(g: str) -> TransactionTypeParseResult:
        success = True
        message = ""
        data = None

        if g == "P":
            data = TransactionType.PURCHASE
        elif g == "S":
            data = TransactionType.SALE
        elif g == "S (partial)":
            data = TransactionType.SALE_PARTIAL
        else:
            success=False
            message=f"Transaction type '{g}' not recognized"

        return TransactionTypeParseResult(
            success=success,
            message=message,
            data=data
        )

class DateParseResult(Result["Date"]):
    pass

# This is just being extended to implement a method to create an instance
# from a capturing group of it in the transaction regex pattern
class Date(date):
    FORMAT = "%m/%d/%Y"
    PATTERN = r"\d{1,2}/\d{1,2}/\d{4}"

    @staticmethod
    def from_date(d: date) -> "Date":
        return Date(d.year, d.month, d.day)

    @classmethod
    def today(cls) -> "Date":
        return Date.from_date(date.today())

    # Writes this date as a string using the format above
    def format(self) -> str:
        return self.strftime(Date.FORMAT)

    @staticmethod
    def from_match(g: str) -> "DateParseResult":
        try:
            d = Date.from_date(datetime.strptime(g, Date.FORMAT).date())

            return DateParseResult(
                success=True,
                message="",
                data=d
            )
        except:
            return DateParseResult(
                success=False,
                message=f"Failed to create date from 'g'",
                data=None
            )

class AmountRangeParseResult(Result["AmountRange"]):
    pass

@dataclass
class AmountRange:
    min: int
    max: int
    MONETARY_AMOUNT_PATTERN = r"\$[\d,]*"
    PATTERN = fr"{MONETARY_AMOUNT_PATTERN}\s-\s{MONETARY_AMOUNT_PATTERN}"
    GROUP_PATTERN = re.compile(r"""
        # Min group
        \$(?P<min>\d+)\s
        -
        # Max group
        \s\$(?P<max>\d+)
    """, re.VERBOSE | re.DOTALL)

    @staticmethod
    def from_match(g: str) -> AmountRangeParseResult:
        # NOTE: Commas are removed in a first pass cus the regex looks
        # worse if we try to create capturing groups that exclude it
        g = re.sub(",", "", g)
        m: Optional[re.Match] = AmountRange.GROUP_PATTERN.search(g)

        if not m:
            return AmountRangeParseResult(
                success=False,
                message=f"Amount range attributes could not be extracted from amount range pattern match '{g}'",
                data=None
            )

        min = int(m.group("min"))
        max = int(m.group("max"))
        ar = AmountRange(min, max)

        return AmountRangeParseResult(
            success=True,
            message="",
            data=ar
        )

class TransactionParseResult(Result["Transaction"]):
    pass

# Represents a transaction made by a member of the House of 
# Representatives
@dataclass
class Transaction:
    asset: Asset
    type: TransactionType
    transaction_date: Date
    notification_date: Date
    amount: AmountRange
    filing_status: FilingStatus
    subholding_of: Optional[str]
    description: Optional[str]
    comment: Optional[str]
    raw_text: str
    SUBHOLDING_OF_PATTERN = r"S\sO:"
    DESCRIPTION_PATTERN = r"D:"
    COMMENT_PATTERN = r"C:"
    GROUP_PATTERN = re.compile(fr"""
        # Asset group (eg. Amazon (AMZN) [ST])
        \s*(?P<asset>{Asset.PATTERN})
    
        # Transaction type group
        \s*(?P<type>
        P
        |
        S(?:\s*\(partial\))?
        )
    
        # Transaction date group
        \s*(?P<transaction_date>{Date.PATTERN})
    
        # Notification date group
        \s*(?P<notification_date>{Date.PATTERN})
    
        # Amount range group
        \s*(?P<amount_range>{AmountRange.PATTERN})
    
        # Filing status group (Required starting point of transaction footer)
        \s*F\sS:\s(?P<filing_status>.*?)\s
        (?=({SUBHOLDING_OF_PATTERN}|{DESCRIPTION_PATTERN}|{COMMENT_PATTERN}|\Z|{Asset.PATTERN}))
    
        # Subholding of group (Optional)
        (?:\s*{SUBHOLDING_OF_PATTERN}\s*(?P<subholding_of>.*?)\s
        (?=({DESCRIPTION_PATTERN}|{COMMENT_PATTERN}|\Z|{Asset.PATTERN})))?
    
        # Comment group (Optional)
        (?:\s*{COMMENT_PATTERN}\s*(?P<comment>.*?)\s
        (?=({DESCRIPTION_PATTERN}|\Z|{Asset.PATTERN})))?
    
        # Description group (Optional)
        (?:\s*{DESCRIPTION_PATTERN}\s*(?P<description>.*?)\s
        (?=({COMMENT_PATTERN}|\Z|{Asset.PATTERN})))?
    
        # Lookahead: Assert that the transaction is followed by the start of a new one
        # or the end of the entire string, which prevents the final optional group from
        # consuming the start of the next transaction asset
        (?=\s*({Asset.PATTERN}|\Z))
    """, re.VERBOSE | re.DOTALL)
    TABLE_NAME = "transactions"

    @staticmethod
    def from_match(m: re.Match) -> TransactionParseResult:
        asset_result = Asset.from_match(m.group("asset"))
        type_result = TransactionType.from_match(m.group("type"))
        transaction_date_result = Date.from_match(m.group("transaction_date"))
        notification_date_result = Date.from_match(m.group("notification_date"))
        amount_result = AmountRange.from_match(m.group("amount_range"))
        filing_status_result = FilingStatus.from_match(m.group("filing_status"))
        subholding_of = m.group("subholding_of")
        description = m.group("description")
        comment = m.group("comment")
        match_text = m.group()

        if not asset_result.success:
            return TransactionParseResult(
                success=False,
                message=f"Transaction asset could not be created: {asset_result.message}",
                data=None
            )
        elif not type_result.success:
            return TransactionParseResult(
                success=False,
                message=f"Transaction type could not be created: {type_result.message}",
                data=None
            )
        elif not transaction_date_result.success:
            return TransactionParseResult(
                success=False,
                message=f"Transaction date could not be created: {transaction_date_result.message}",
                data=None
            )
        elif not notification_date_result.success:
            return TransactionParseResult(
                success=False,
                message=f"Notification date could not be created: {notification_date_result.message}",
                data=None
            )
        elif not amount_result.success:
            return TransactionParseResult(
                success=False,
                message=f"Transaction amount range could not be created: {amount_result.message}",
                data=None
            )
        elif not filing_status_result.success:
            return TransactionParseResult(
                success=False,
                message=f"Transaction filing status could not be created: {filing_status_result.message}",
                data=None
            )
        else:
            t = Transaction(
                asset_result.data,
                type_result.data,
                transaction_date_result.data,
                notification_date_result.data,
                amount_result.data,
                filing_status_result.data,
                subholding_of,
                description,
                comment,
                match_text
            )

            return TransactionParseResult(
                success=True,
                message="",
                data=t
            )

class TransactionsParseResult(Result[list[Transaction]]):
    pass

class Transactions:

    # Constructs a list of transactions from a block of cleansed
    # text that _just_ contains transactions data
    @staticmethod
    def from_transactions_block(b: str) -> TransactionsParseResult:
        ms: list[re.Match] = list(Transaction.GROUP_PATTERN.finditer(b))

        if not ms:
            return TransactionsParseResult(
                success=False,
                message="No transactions matches were found in the transactions block",
                data=None
            )

        rs: list[TransactionParseResult] = [Transaction.from_match(m) for m in ms]
        failures: list[TransactionParseResult] = [r for r in rs if not r.success]

        if failures:
            joined_failure_messages = "\n".join([f.message for f in failures])
            message = f"Failure to construct transactions from block:\n{joined_failure_messages}"
            return TransactionsParseResult(
                success=False,
                message=message,
                data=None
            )
        else:
            return TransactionsParseResult(
                success=True,
                message="",
                data=[r.data for r in rs]
            )

    # Creates a list of tuples, one for each transaction in the given list,
    # that'll be used as the data inserted into database
    @staticmethod
    def to_db_tuples(ts: list[list[Transaction]], filing_ids: list[int]) -> list[tuple]:
        if len(ts) != len(filing_ids):
            # TODO: Result object needed here
            return []

        nested_transactions_data: list[list[tuple]] = [
            [
                (
                    zlib.crc32(f"{filing_id}-{t.asset.name}-{t.type}-{t.transaction_date}".encode("utf-8")) & 0xFFFFFFFF,
                    filing_id,
                    t.asset.name,
                    t.asset.type,
                    t.asset.ticker,
                    t.filing_status.value,
                    t.subholding_of,
                    t.description,
                    t.comment,
                    t.type.value,
                    t.transaction_date.format(),
                    t.notification_date.format(),
                    t.amount.min,
                    t.amount.max,
                    t.raw_text,
                    Date.today().format()
                )
                for t in rts
            ]
            for rts, filing_id in zip(ts, filing_ids)
        ]
        flattened_transactions_data: list[tuple] = [t for rts in nested_transactions_data for t in rts]
        
        return flattened_transactions_data

class ReportParseResult(Result["Report"]):
    pass

# NOTE: Data is present _regardless_ of success as long as the write went through
class DBWriteResult(Result[DBWrite]):
    pass

@dataclass
class Report:
    filing_id: int
    representative_name: str
    signed_date: Date
    transactions: list[Transaction]
    FILING_ID_PATTERN = re.compile(
        r'Filing ID #([\d]+)',
        re.DOTALL
    )
    # NOTE: The only reason the following two patterns aren't combined into one and
    # stored as a static variable of the Report class is because the order of these
    # 3 attributes isn't fixed. The filing ID could come after the signing date for
    # single page reports, and I don't want to make the pattern to unwieldy to 
    # accommodate for this
    REP_NAME_AND_SIGNING_DATE_PATTERN = re.compile(fr"""
        # Representative name group
        Signed:\sHon\.\s(?P<rep_name>.+?)\s,
    
        # Signing date group
        \s(?P<signing_date>{Date.PATTERN})
    """, re.VERBOSE | re.DOTALL)
    TABLE_NAME = "reports"

    # NOTE: The transactions probably could be extracted from the text, but 
    # the Report object was an afterthought, and I don't care enough to 
    # implement this
    @staticmethod
    def from_cleansed_text(
        cleansed_text: str, transactions: list[Transaction]
    ) -> ReportParseResult:
        filing_id_match = Report.FILING_ID_PATTERN.search(cleansed_text)

        if not filing_id_match:
            return ReportParseResult(
                success=False,
                message="Filing ID could not be found in report",
                data=None
            )

        # NOTE: This group matches to digits only, so this conversion should work
        filing_id = int(filing_id_match.group(1))
        rep_name_and_signing_date_match = Report.REP_NAME_AND_SIGNING_DATE_PATTERN.search(cleansed_text)

        if not rep_name_and_signing_date_match:
            return ReportParseResult(
                success=False,
                message="Representative name and signing date could not be found in report",
                data=None
            )

        representative_name = rep_name_and_signing_date_match.group("rep_name")
        sdr: DateParseResult = Date.from_match(
            rep_name_and_signing_date_match.group("signing_date")
        )

        if not sdr.success:
            return ReportParseResult(
                success=False,
                message=f"Report signing date could not be created: {sdr.message}",
                data=None
            )

        r = Report(
            filing_id=filing_id,
            representative_name=representative_name,
            signed_date=sdr.data,
            transactions=transactions
        )

        return ReportParseResult(
            success=True,
            message="",
            data=r
        )

    # Given a database cursor and a list of reports:
    # 1) Queries for the filing IDs from the given report list already 
    # present in the reports table
    # 2) Discards those by taking the set difference of the given set/list and
    # the set/list present in the database
    # 3) Writes new reports
    # 4) Writes new transactions
    @staticmethod
    def db_write_many(cur: sqlite3.Cursor, rs: list["Report"]) -> DBWriteResult:
        # Returns a list of reports, filtered from the given list of reports, whose 
        # filing IDs are not present in the given list of filing IDs
        def _discard_present_reports(
            cur: sqlite3.Cursor, rs: list["Report"], 
        ) -> list["Report"]:
            filing_ids: list[int] = [r.filing_id for r in rs]
            placeholders_string = create_placeholders_string(len(filing_ids))
            filing_ids_query = f"""
select report_id from reports where report_id in ({', '.join(['?'] * len(filing_ids))})
            """
            # TODO: There is no protection against/visibility into a failure here
            cur.execute(filing_ids_query, tuple(filing_ids))
            # NOTE: No matter how many rows are selected, each row is still a tuple
            present_filing_ids = [t[0] for t in cur.fetchall()]
            return [r for r in rs if r.filing_id not in present_filing_ids]

        reports_to_write: list["Report"] = _discard_present_reports(cur, rs)

        # 1) Creates a batch insert SQL statement
        # 2) Writes them using the given cursor
        # TODO: Modify description of step below
        # 3) Returns true if the number of rows affected/inserted is equal
        # to the length of the list of reports given
        def _batch_write_to_reports_table(
            cur: sqlite3.Cursor, rs: list["Report"]
        ) -> DBWriteResult:
            reports_data: list[tuple] = Reports.to_db_tuples(rs)
            placeholders_string = create_placeholders_string(len(reports_data[0]))
            report_statement = f"""
insert into {Report.TABLE_NAME} values {placeholders_string};
            """

            try:
                cur.executemany(report_statement, reports_data)
            except Exception as e:
                return DBWriteResult(
                    success=False,
                    message=f"Failed to write reports to database: {str(e)}",
                    data=None
                )
            
            success = cur.rowcount == len(rs)

            return DBWriteResult(
                success=success,
                message="Rows affected do not match calculated count of reports to write" if not success else "",
                data=DBWrite(actual=cur.rowcount, expected=len(rs)),
            )

        r: DBWriteResult = _batch_write_to_reports_table(cur, reports_to_write)

        if not r.success:
            return r

        def _batch_write_to_transactions_table(
            cur: sqlite3.Cursor, rs: list["Report"]
        ) -> DBWriteResult:
            transactions_data = Transactions.to_db_tuples(
                [r.transactions for r in rs],
                [r.filing_id for r in rs]
            )
            placeholders_string = create_placeholders_string(len(transactions_data[0]))
            transaction_statement = f"""
insert into {Transaction.TABLE_NAME} values {placeholders_string};
            """

            try:
                cur.executemany(transaction_statement, transactions_data)
            except Exception as e:
                return DBWriteResult(
                    success=False,
                    message=f"Failed to write transactions to database: {str(e)}",
                    data=None
                )

            success = cur.rowcount == len(transactions_data)
            expected_write_count = sum([len(r.transactions) for r in rs])

            return DBWriteResult(
                success=success,
                message="Rows affected do not match calculated count of transactions to write" if not success else "",
                data=DBWrite(actual=cur.rowcount, expected=expected_write_count)
            )

        return _batch_write_to_transactions_table(cur, reports_to_write)

class Reports:

    # Creates a list of tuples, one for each report in the given list,
    # that'll be used as the data inserted into database
    @staticmethod
    def to_db_tuples(rs: list[Report]) -> list[tuple]:
        reports_data: list[tuple] = [
            (
                r.filing_id,
                r.representative_name,
                r.signed_date.format(),
                Date.today().format()
            )
            for r in rs
        ]
        
        return reports_data
