import requests
import xml.etree.ElementTree as ET
from supabase import create_client
import re
from datetime import datetime, time
import pytz

SUPABASE_URL = 'your-supabase-url'
SUPABASE_KEY = 'your-supabase-key'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_sec_business_hours():
    """Check if current time is within SEC EDGAR operating hours (6AM-10PM EST, weekdays)"""
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    if now.weekday() >= 5:  # Saturday(5) or Sunday(6)
        return False
    return time(6, 0) <= now.time() <= time(22, 0)

def fetch_and_process_filings():
    if not is_sec_business_hours():
        print("Outside SEC operating hours - skipping check")
        return

    print("Checking for new filings...")
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&output=atom"
    headers = {"User-Agent": "Your Name your@email.com"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            process_filing(entry)
            
    except requests.RequestException as e:
        print(f"Error fetching filings: {e}")

def process_filing(entry):
    filing_url = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']
    filing_text = requests.get(filing_url, headers={"User-Agent": "Your Name your@email.com"}).text
    
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

if __name__ == '__main__':
    fetch_and_process_filings()
