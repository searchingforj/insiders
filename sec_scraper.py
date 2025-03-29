import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client
import re
from datetime import datetime, time
import pytz

# Initialize Supabase client
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# SEC configuration
SEC_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=4&company=&dateb=&owner=only&start=0&count=100&output=atom"
SEC_HEADERS = {
    "User-Agent": "Jackson Gray jacksongray23@gmail.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

# TESTING MODE - set to False for production
TESTING_MODE = True  # <<< Change to False when done testing

def is_sec_business_hours():
    """Check if current time is within SEC EDGAR operating hours"""
    if TESTING_MODE:
        return True  # Always run in testing mode
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    if now.weekday() >= 5:  # Saturday(5) or Sunday(6)
        return False
    return time(6, 0) <= now.time() <= time(22, 0)

def fetch_and_process_filings():
    if not is_sec_business_hours():
        print("Outside SEC operating hours - skipping check")
        return

    print(f"{'[TESTING MODE] ' if TESTING_MODE else ''}Checking for new filings...")
    
    try:
        response = requests.get(SEC_RSS_URL, headers=SEC_HEADERS, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        # Count total filings found
        filings = list(root.findall('{http://www.w3.org/2005/Atom}entry'))
        print(f"Found {len(filings)} filings to process")
        
        j_code_count = 0
        for entry in filings:
            if process_filing(entry):
                j_code_count += 1
                
        print(f"Processing complete. Found {j_code_count} J-code filings")
            
    except requests.RequestException as e:
        print(f"Error fetching filings: {e}")

def process_filing(entry):
    filing_url = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']
    
    try:
        print(f"Processing filing: {filing_url}")
        filing_response = requests.get(filing_url, headers=SEC_HEADERS, timeout=10)
        filing_response.raise_for_status()
        filing_text = filing_response.text
        
        if '<transactionCode>J</transactionCode>' in filing_text:
            title_parts = entry.find('{http://www.w3.org/2005/Atom}title').text.split(' - ')
            company_name = title_parts[0]
            ticker = title_parts[0].split('(')[-1].rstrip(')') if '(' in title_parts[0] else None
            
            filing_data = {
                'filing_id': entry.find('{http://www.w3.org/2005/Atom}id').text.split('/')[-1],
                'ticker': ticker,
                'company_name': company_name,
                'filing_date': entry.find('{http://www.w3.org/2005/Atom}updated').text,
                'filing_url': filing_url
            }
            
            # Upsert to avoid duplicates
            supabase.table('j_code_filings').upsert(filing_data).execute()
            print(f"Found J-code filing: {company_name} ({ticker})")
            return True
            
    except requests.RequestException as e:
        print(f"Error processing filing {filing_url}: {e}")
    return False

if __name__ == '__main__':
    fetch_and_process_filings()
