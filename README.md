# house-financial-disclosures

Python script that creates a model of transactions from a single [House Financial Disclosure Report](https://disclosures-clerk.house.gov/FinancialDisclosure)

## Setup

```
$ # Create venv and install requirements (needed pypdf for PDF text extraction, since that is the format the reports come in)
$ python3 -m venv <venv-name>
$ source <venv-name>/bin/activate
$ pip install -r requirements.txt
```

## Usage

For now, the script just prints the in-memory representations of the parsed transactions. The goal is to run this on all reports for a given day, and then write the transactions to a SQLite database for warehousing purposes + further analysis

```
$ # With venv activated
$ python script.py sample/report.pdf
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
    - [ ] Have it download all reports across all representatives for the current year
    - [ ] Parse all reports, filter out reports that have already been written to the database
    - [ ] Write new report transactions to database
    - [ ] SOMEWHERE in here, consider writing the reports themselves to some sort of object storage for the sake of posterity
- [ ] Improve parser robustness, sample size of 1 off of which to build regex patterns was obviously too small
    - [ ] Filing ID appears to be at the end of the first page. It's likely best to search for it in its own pass through of the document and not as a capturing group in a larger regex
    - [ ] Additional transaction asset sections. These are not breaking the parser, but they are being read as part of the next transaction's asset name
        - [ ] Subholding Of
        - [ ] Description
        - [ ] Comments
    - [ ] A populated Owner column of the transaction table also bleeds into the asset name. Best course of action is likely to get the distinct values for it and add a capturing group for it in or exclude it entirely from the transaction pattern
        - So far, we've found SP
    - [ ] Some transaction types are marked as "S (partial)". This might break the parser since the group after the transaction type doesn't expect a parenthesis
    - [ ] Physical scans don't produce text. Deal with this case
    - [ ] There are different varieties of the transactions table header and footer, as well as multiple occurences of the searched after table footer
    - NOTE: No action item here for now, but values "Cap. Gains > $200" column don't seem to leave any text
- [ ] Restrict search to periodic transaction reports
