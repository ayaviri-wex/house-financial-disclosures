# house-financial-disclosures

Python ETL script that scrapes and extracts transactions from [House Financial Disclosure Reports](https://disclosures-clerk.house.gov/FinancialDisclosure)

## Setup

```
$ # Create venv and install requirements (needed pypdf for PDF text extraction, since that is the format the reports come in)
$ python3 -m venv <venv-name>
$ source <venv-name>/bin/activate
$ pip install -r requirements.txt
```

## Contents & Usage

- `daily.py`: The ETL script to be run on a given basis. It scrapes all reports for the current calendar year, extracts the transactions from them, and writes the new reports to a SQLite database

```
$ python daily.py
```

- `parse.py`: Contains the function to extract transactions from a single report

```
$ python parse.py sample/new_transaction_type_report/report.pdf
```

- `models.py`: The meat of this project. Contains models for the data available in these reports. Each model contains the logic to parse itself from cleansed report text and write itself to the database
- `schemas/tables.sql`: The schemas for the SQLite database tables. To reset the database:

```
$ rm report.db
$ sqlite3 -init schemas/tables.sql
$ sqlite> .exit
```

## To Do
- [x] Install SQLite
- [x] Create bash script to ensure that dependency is installed (or create a docker-compose.yml file to install the client)
- [ ] Create DB schemas
    - [x] Table for reports
    - [x] Table for transactions
    - [x] Table for assets
    - [ ] Add not null constraints to necessary fields and a constraint to ensure that the amount_min attribute is strictly less than the amount_max attribute
- [x] Perform schema creation migration
- [ ] Create script to be called by daily running cron job
    - [x] Have it download all reports across all representatives for the current year
    - [x] Parse all reports, filter out reports that have already been written to the database
    - [x] Write new report transactions to database
    - [ ] SOMEWHERE in here, consider writing the reports themselves to some sort of object storage for the sake of posterity
- [ ] Improve parser robustness, sample size of 1 off of which to build regex patterns was obviously too small
    - [x] Filing ID appears to be at the end of the first page. It's likely best to search for it in its own pass through of the document and not as a capturing group in a larger regex
    - [x] Asset tickers aren't required, and current pattern requires them
    - [ ] Additional transaction asset sections. These are not breaking the parser, but they are being read as part of the next transaction's asset name
        - [ ] Filing Status
        - [ ] Subholding Of
        - [ ] Description
        - [ ] Comments
    - [ ] A populated Owner column of the transaction table also bleeds into the asset name. Best course of action is likely to get the distinct values for it and add a capturing group for it in or exclude it entirely from the transaction pattern
        - So far, we've found SP
    - [x] Some transaction types are marked as "S (partial)". This might break the parser since the group after the transaction type doesn't expect a parenthesis
    - [x] Physical scans don't produce text. Deal with this case
- [x] Restrict search to periodic transaction reports
- [ ] Consider an ORM. I just don't like the absence of a database layer with the current implementation
