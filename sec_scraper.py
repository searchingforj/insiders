import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client
import re
from datetime import datetime

# Initialize Supabase
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def extract_xml_data(xml_content):
    """Extracts precise data from XML with error handling"""
    try:
        root = ET.fromstring(xml_content)
        return {
            'issuer_name': root.find('.//issuerName').text if root.find('.//issuerName') is not None else None,
            'ticker': root.find('.//issuerTradingSymbol').text if root.find('.//issuerTradingSymbol') is not None else None,
            'period_of_report': root.find('.//periodOfReport').text if root.find('.//periodOfReport') is not None else None,
            'transaction_date': root.find('.//transactionDate/value').text if root.find('.//transactionDate/value') is not None else None
        }
    except ET.ParseError as e:
        print(f"XML parsing error: {str(e)}")
        return None

def process_filings():
    feed = requests.get(
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only&count=100&output=atom",
        headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"}
    ).content

    for entry in ET.fromstring(feed).findall('{http://www.w3.org/2005/Atom}entry'):
        index_url = entry.find('{http://www.w3.org/2005/Atom}link').attrib['href']
        txt_url = index_url.replace("-index.htm", ".txt")
        
        try:
            # 1. Fetch filing
            response = requests.get(txt_url, headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"})
            filing_text = response.text
            
            # 2. Quick J-code check
            if '<transactionCode>J</transactionCode>' not in filing_text:
                continue
                
            # 3. Extract XML data
            xml_match = re.search(r'<XML>(.*?)</XML>', filing_text, re.DOTALL)
            if not xml_match:
                continue
                
            xml_data = extract_xml_data(xml_match.group(1))
            if not xml_data:
                continue

            # 4. Prepare database fields
            accession_number = txt_url.split('/')[-1].replace('.txt', '')
            rss_updated = entry.find('{http://www.w3.org/2005/Atom}updated').text
            
            supabase.table('j_code_filings').upsert({
                'filing_id': accession_number,
                'ticker': xml_data['ticker'],
                'company_name': xml_data['issuer_name'],
                'filing_date': rss_updated,  # From RSS <updated> field
                'transaction_date': xml_data['period_of_report'],  # From XML periodOfReport
                'filing_url': txt_url
            }).execute()
            
            print(f"Processed: {xml_data['issuer_name']} ({xml_data['ticker']}) | Filed: {rss_updated} | Period: {xml_data['period_of_report']}")
            
        except Exception as e:
            print(f"Error processing {txt_url}: {str(e)}")

if __name__ == '__main__':
    process_filings()
