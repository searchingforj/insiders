import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client
import re

def extract_xml_data(filing_text):
    """Extracts and cleans XML from SEC TXT filing"""
    try:
        # 1. Find the XML section (handles malformed wrappers)
        xml_start = filing_text.find('<ownershipDocument')
        xml_end = filing_text.rfind('</ownershipDocument>')
        
        if xml_start == -1 or xml_end == -1:
            return None
            
        xml_content = filing_text[xml_start:xml_end+19]  # +19 for full closing tag
        
        # 2. Remove any XML declarations that might be inside
        xml_content = re.sub(r'<\?xml[^>]+\?>', '', xml_content)
        
        # 3. Handle common XML issues
        xml_content = re.sub(r'&(?!#?[a-z0-9]+;)', '&amp;', xml_content)  # Fix ampersands
        xml_content = re.sub(r'<([^/]\w+)[^>]*>', r'<\1>', xml_content)  # Simplify tags
        
        # 4. Parse the cleaned XML
        root = ET.fromstring(xml_content)
        
        # Check for J-codes in ALL transaction types
        j_code_found = False
        for elem in root.iter():
            if elem.tag == 'transactionCode' and elem.text == 'J':
                j_code_found = True
                break
                
        if not j_code_found:
            return None
            
        # Extract data
        issuer = root.find('.//issuer')
        return {
            'issuer_name': issuer.find('issuerName').text if issuer is not None else None,
            'ticker': issuer.find('issuerTradingSymbol').text if issuer is not None else None,
            'period_of_report': root.findtext('.//periodOfReport'),
            'transaction_date': (root.findtext('.//transactionDate/value') or 
                               root.findtext('.//deemedExecutionDate/value') or 
                               root.findtext('.//periodOfReport'))
        }
        
    except Exception as e:
        print(f"XML parsing error: {str(e)}")
        # Save first 1000 chars for debugging
        with open('last_parse_error.txt', 'w') as f:
            f.write(filing_text[:1000])
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
            
            # First do quick J-code check before parsing
            if 'transactionCode>J</transactionCode>' not in filing_text:
                continue
                
            # Process XML if J-code found
            xml_data = extract_xml_data(filing_text)
            if not xml_data:
                continue
                
            # Prepare database record
            accession_number = txt_url.split('/')[-1].replace('.txt', '')
            record = {
                'filing_id': accession_number,
                'ticker': xml_data['ticker'],
                'company_name': xml_data['issuer_name'],
                'filing_date': entry.find('{http://www.w3.org/2005/Atom}updated').text,
                'transaction_date': xml_data['period_of_report'],
                'filing_url': txt_url
            }
            
            supabase.table('j_code_filings').upsert(record).execute()
            print(f"Processed: {record['company_name']} ({record['ticker']})")
            
        except Exception as e:
            print(f"Error processing {txt_url}: {str(e)}")

if __name__ == '__main__':
    process_filings()
