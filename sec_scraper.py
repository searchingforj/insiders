import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client
import re
from datetime import datetime

def extract_xml_data(filing_text):
    """Advanced XML parser with SEC-specific handling"""
    try:
        # Isolate the XML section (handles malformed wrappers)
        xml_start = filing_text.find('<ownershipDocument>')
        xml_end = filing_text.find('</ownershipDocument>')
        
        if xml_start == -1 or xml_end == -1:
            return None
            
        xml_content = filing_text[xml_start:xml_end+18]  # +18 for tag length
        
        # Fix common XML issues
        xml_content = re.sub(r'<\?xml[^>]+\?>', '', xml_content)  # Remove duplicate declarations
        xml_content = re.sub(r'&(?!#?[a-z0-9]+;)', '&amp;', xml_content)  # Fix unescaped ampersands
        
        # Parse with explicit encoding
        root = ET.fromstring(xml_content.encode('utf-8'))
        
        # XPath helper with null checks
        def xpath_text(path):
            node = root.find(path)
            return node.text if node is not None else None
            
        return {
            'issuer_name': xpath_text('.//issuerName'),
            'ticker': xpath_text('.//issuerTradingSymbol'),
            'period_of_report': xpath_text('.//periodOfReport'),
            'transaction_date': xpath_text('.//nonDerivativeTransaction/transactionDate/value')
        }
        
    except Exception as e:
        print(f"XML parsing failed: {str(e)}")
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
            response = requests.get(txt_url, headers={"User-Agent": "Jackson Gray jacksongray23@gmail.com"})
            filing_text = response.text
            
            # Quick J-code check before parsing
            if '<transactionCode>J</transactionCode>' not in filing_text:
                continue
                
            # Extract data
            xml_data = extract_xml_data(filing_text)
            if not xml_data:
                continue

            # Prepare database record
            accession_number = txt_url.split('/')[-1].replace('.txt', '')
            record = {
                'filing_id': accession_number,
                'ticker': xml_data['ticker'],  # NTHI from example
                'company_name': xml_data['issuer_name'],  # "NEONC TECHNOLOGIES..."
                'filing_date': entry.find('{http://www.w3.org/2005/Atom}updated').text,  # RSS timestamp
                'transaction_date': xml_data['period_of_report'],  # 2025-03-26 from example
                'filing_url': txt_url
            }
            
            supabase.table('j_code_filings').upsert(record).execute()
            print(f"Processed: {record['company_name']} ({record['ticker']})")
            
        except Exception as e:
            print(f"Error processing {txt_url}: {str(e)}")

if __name__ == '__main__':
    process_filings()
