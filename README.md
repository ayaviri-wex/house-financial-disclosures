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
