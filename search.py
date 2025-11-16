#!/usr/bin/env python3
"""
Script to search House Financial Disclosures and extract PDF links.
Usage: python house_disclosures.py [--last-name NAME] [--filing-year YEAR] [--state STATE] [--district DISTRICT]
"""

import argparse
import re
import sys
import requests
from html.parser import HTMLParser

class LinkExtractor(HTMLParser):
    """
    HTML parser to extract <a> tags with 'PTR Original' filing type.
    """

    def __init__(self):
        super().__init__()
        self.links = []
        # State tracking variables
        self.in_tr = False                  # True when inside a table row <tr>
        self.in_link_cell = False           # True when inside the Name column cell (which contains the link)
        self.in_filing_cell = False         # True when inside the Filing column cell
        self.current_link = None            # Stores the potential link from the <a> tag
        self.current_filing_type = None     # Stores the text data from the Filing column cell

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            # Start of a new row
            self.in_tr = True
            self.current_link = None
            self.current_filing_type = None

        elif tag == "td":
            # Check if this is the 'Name' column (which contains the link)
            attrs_dict = dict(attrs)
            if self.in_tr and attrs_dict.get('data-label') == 'Name':
                self.in_link_cell = True
            # Check if this is the 'Filing' column
            elif self.in_tr and attrs_dict.get('data-label') == 'Filing':
                self.in_filing_cell = True

        elif tag == "a" and self.in_link_cell:
            # Capture the link when inside the link cell
            for attr, value in attrs:
                if attr == "href":
                    self.current_link = value
                    break

    def handle_endtag(self, tag):
        if tag == "td":
            # End of a cell - reset the cell flags
            self.in_link_cell = False
            self.in_filing_cell = False

        elif tag == "tr" and self.in_tr:
            # End of a row - perform the check
            self.in_tr = False
            # Check if we captured a link AND the filing type is exactly 'PTR Original'
            if self.current_link and self.current_filing_type == "PTR Original":
                self.links.append(self.current_link)
            
            # Reset the data variables for the next row (though start_tag does this, too)
            self.current_link = None
            self.current_filing_type = None
    
    def handle_data(self, data):
        # We only care about data inside the Filing column cell
        if self.in_filing_cell:
            # Clean up the data (remove leading/trailing whitespace, etc.)
            clean_data = data.strip()
            if clean_data:
                self.current_filing_type = clean_data

# class LinkExtractor(HTMLParser):
#     """HTML parser to extract all <a> tags and their href attributes."""
# 
#     def __init__(self):
#         super().__init__()
#         self.links = []
# 
#     def handle_starttag(self, tag, attrs):
#         if tag == "a":
#             for attr, value in attrs:
#                 if attr == "href":
#                     self.links.append(value)


def get_verification_token():
    """
    Fetch the initial page to get a valid __RequestVerificationToken.
    This is needed for CSRF protection.
    """
    url = "https://disclosures-clerk.house.gov/FinancialDisclosure"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Extract token from HTML
        match = re.search(
            r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', response.text
        )
        if match:
            return match.group(1), response.cookies
        else:
            print(
                "Warning: Could not find verification token, proceeding without it",
                file=sys.stderr,
            )
            return None, None
    except Exception as e:
        print(f"Warning: Could not fetch verification token: {e}", file=sys.stderr)
        return None, None


def search_disclosures(last_name=None, filing_year=None, state=None, district=None):
    """
    Search House Financial Disclosures with the given parameters.
    Returns a list of links found in the response.
    """
    url = (
        "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult"
    )

    # Get a fresh verification token
    token, cookies = get_verification_token()

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.6",
        "Cache-Control": "max-age=0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://disclosures-clerk.house.gov",
        "Referer": "https://disclosures-clerk.house.gov/FinancialDisclosure",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    }

    # Build the form data
    data = {
        "LastName": last_name or "",
        "FilingYear": filing_year or "",
        "State": state or "",
        "District": district or "",
    }

    # Add verification token if we got one
    if token:
        data["__RequestVerificationToken"] = token

    try:
        response = requests.post(
            url, headers=headers, data=data, cookies=cookies, timeout=30
        )
        response.raise_for_status()

        # Parse the HTML and extract links
        parser = LinkExtractor()
        parser.feed(response.text)

        # NOTE: Seems like only relative links are produced.
        # Make absolute here
        return [
            (
                f"https://disclosures-clerk.house.gov/{l}" 
                if l.startswith("public_disc/") 
                else l 
            )
            for l in parser.links
        ]

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Search House Financial Disclosures and extract PDF links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python house_disclosures.py --last-name PELOSI --filing-year 2025
  python house_disclosures.py --last-name SMITH --state CA
  python house_disclosures.py --filing-year 2024
        """,
    )

    parser.add_argument("--last-name", type=str, help="Last name to search for")
    parser.add_argument("--filing-year", type=str, help="Filing year to search for")
    parser.add_argument("--state", type=str, help="State abbreviation (e.g., CA, NY)")
    parser.add_argument("--district", type=str, help="District number")

    args = parser.parse_args()

    # Check if at least one parameter was provided
    if not any([args.last_name, args.filing_year, args.state, args.district]):
        print(
            "Warning: No search parameters provided, searching all records...",
            file=sys.stderr,
        )

    links = search_disclosures(
        last_name=args.last_name,
        filing_year=args.filing_year,
        state=args.state,
        district=args.district,
    )

    if links:
        print(f"Found {len(links)} links:\n")
        for link in links:
            # Make relative URLs absolute
            if link.startswith("public_disc/"):
                full_url = f"https://disclosures-clerk.house.gov/{link}"
                print(full_url)
            else:
                print(link)
    else:
        print("No links found in the response")


if __name__ == "__main__":
    main()
