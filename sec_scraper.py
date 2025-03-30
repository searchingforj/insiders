import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client
import re
from bs4 import BeautifulSoup  # HTML/XML cleanup

def extract_xml_data(filing_text):
    """Ultra-reliable XML extraction with full J-code detection"""
    try:
        # 1. Isolate XML content using more flexible matching
        xml_start = filing_text.find('<ownershipDocument')
        xml_end = filing_text.rfind('</ownershipDocument>')
        
        if xml_start == -1 or xml_end == -1:
            return None
            
        xml_content = filing_text[xml_start:xml_end+19]  # +19 for full closing tag
        
        # 2. Clean the XML before parsing
        xml_content = re.sub(r'<\?xml[^>]+\?>', '', xml_content)  # Remove declarations
        xml_content = re.sub(r'&(?!#?[a-z0-9]+;)', '&amp;', xml_content)  # Fix ampersands
        
        # 3. Parse with BeautifulSoup for fault tolerance
        soup = BeautifulSoup(xml_content, 'lxml-xml')
        
        # 4. Check for J-codes in ALL transaction types
        j_code_found = False
        for code in soup.find_all('transactionCode'):
            if code.text.strip() == 'J':
                j_code_found = True
                break
                
        if not j_code_found:
            return None
            
        # 5. Extract data with fallbacks
        issuer = soup.find('issuer')
        return {
            'issuer_name': issuer.find('issuerName').text if issuer else None,
            'ticker': issuer.find('issuerTradingSymbol').text if issuer else None,
            'period_of_report': soup.find('periodOfReport').text if soup.find('periodOfReport') else None,
            'transaction_date': (soup.find('transactionDate', {'value': True}) or 
                               soup.find('deemedExecutionDate', {'value': True}) or 
                               soup.find('periodOfReport')).text if soup.find('periodOfReport') else None
        }
        
    except Exception as e:
        print(f"XML parsing error: {str(e)}")
        # Save problematic filing for debugging
        with open('last_failed_parse.txt', 'w') as f:
            f.write(filing_text[xml_start-500:xml_end+500] if 'xml_start' in locals() else filing_text[:1000])
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
            # Fetch filing
            response = requests.get(txt_url, headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"}, timeout=15)
            filing_text = response.text
            
            # Process XML
            xml_data = extract_xml_data(filing_text)
            if not xml_data:  # Either no J-code or parse failure
                continue
                
            # Prepare database record
            accession_number = txt_url.split('/')[-1].replace('.txt', '')
            record = {
                'filing_id': accession_number,
                'ticker': xml_data['ticker'],
                'company_name': xml_data['issuer_name'],
                'filing_date': entry.find('{http://www.w3.org/2005/Atom}updated').text,
                'transaction_date': xml_data['period_of_report'],  # Using periodOfReport as requested
                'filing_url': txt_url
            }
            
            supabase.table('j_code_filings').upsert(record).execute()
            print(f"✅ Processed: {record['company_name']} ({record['ticker']})")
            
        except Exception as e:
            print(f"❌ Failed {txt_url}: {str(e)}")

if __name__ == '__main__':
    process_filings()
