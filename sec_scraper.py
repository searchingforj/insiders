import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client
import re

# 1. Setup - Only the essentials
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

# 2. Single HTTP call with quick J-code check
def check_filing(filing_url):
    try:
        txt_url = filing_url.replace("-index.htm", ".txt")
        response = requests.get(
            txt_url,
            headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"},
            timeout=10
        )
        return '<transactionCode>J</transactionCode>' in response.text
    except:
        return False

# 3. Straightforward processing
def process_filings():
    feed = requests.get(
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=100&output=atom",
        headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"}
    ).content

    for entry in ET.fromstring(feed).findall('{http://www.w3.org/2005/Atom}entry'):
        index_url = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']
        
        if check_filing(index_url):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text
            accession_number = index_url.split('/')[-2]  # Extract from URL path
            
            supabase.table('j_code_filings').upsert({
                'filing_id': accession_number,  # Now using the clean accession number
                'ticker': re.search(r'\((.*?)\)', title).group(1) if '(' in title else None,
                'company_name': title.split(' - ')[0].split(' (')[0],
                'filing_date': entry.find('{http://www.w3.org/2005/Atom}updated').text,
                'filing_url': index_url.replace("-index.htm", ".txt")
            }).execute()

if __name__ == '__main__':
    process_filings()
