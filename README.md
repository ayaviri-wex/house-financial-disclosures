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
[x] Install SQLite
[x] Create bash script to ensure that dependency is installed (or create a docker-compose.yml file to install the client)
[ ] Create DB schemas
    [x] Table for reports
    [x] Table for transactions
    [x] Table for assets
    [ ] Add not null constraints to necessary fields and a constraint to ensure that the amount_min attribute is strictly less than the amount_max attribute
[ ] Perform schema creation migration
[ ] Create script to be called by daily running cron job
    [ ] Have it download all reports across all representatives for the current year
    [ ] Parse all reports, filter out reports that have already been written to the database
    [ ] Write new report transactions to database
    [ ] SOMEWHERE in here, consider writing the reports themselves to some sort of object storage for the sake of posterity
