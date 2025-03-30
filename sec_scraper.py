import os
import requests
import re
import xml.etree.ElementTree as ET
from supabase import create_client

def get_xml_url(txt_url):
    """Your preferred method - extract from TXT"""
    try:
        response = requests.get(txt_url, headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"}, timeout=10)
        match = re.search(r'<FILENAME>(.*?\.xml)', response.text)
        if match:
            base_url = txt_url.rsplit('/', 1)[0]
            return f"{base_url}/{match.group(1)}"
        return None
    except Exception as e:
        print(f"Failed to get XML URL: {str(e)}")
        return None

def process_filings():
    supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    
    feed = requests.get(
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=100&output=atom",
        headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"}
    ).content

    for entry in ET.fromstring(feed).findall('{http://www.w3.org/2005/Atom}entry'):
        index_url = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']
        txt_url = index_url.replace("-index.htm", ".txt")
        
        try:
            # 1. Get XML URL from TXT
            xml_url = get_xml_url(txt_url)
            if not xml_url:
                continue
                
            # 2. Parse XML directly
            response = requests.get(xml_url, headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"})
            root = ET.fromstring(response.content)
            
            # 3. Check for J-codes
            if not any(elem.text == 'J' for elem in root.iter('transactionCode')):
                continue
                
            # 4. Extract data
            accession = txt_url.split('/')[-1].replace('.txt', '')
            record = {
                'filing_id': accession,
                'ticker': root.findtext('.//issuerTradingSymbol'),
                'company_name': root.findtext('.//issuerName'),
                'filing_date': entry.find('{http://www.w3.org/2005/Atom}updated').text,
                'transaction_date': root.findtext('.//periodOfReport'),
                'filing_url': xml_url  # Now points to clean XML
            }
            
            supabase.table('j_code_filings').upsert(record).execute()
            print(f"✅ Processed: {record['company_name']} ({record['ticker']})")
            
        except Exception as e:
            print(f"❌ Failed {index_url}: {str(e)}")

if __name__ == '__main__':
    process_filings()
