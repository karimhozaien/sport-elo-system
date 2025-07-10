from curses.ascii import islower
import requests
from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from name_normalizer import normalize_fighter_name
import xml.etree.ElementTree as ET

# Create a session for connection pooling
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

url = 'https://www.bjjheroes.com/'
url_az = url + '/a-z-bjj-fighters-list'
url_fighters = url + 'bjj-fighters/'

def get_fighter_urls_from_sitemap():
    """Extract all fighter URLs from the sitemap"""
    fighter_urls = set()
    
    # Try different sitemap locations
    sitemap_urls = [
        url + 'sitemap.xml',
        url + 'sitemap_index.xml',
        url + 'sitemap1.xml',
        url + 'sitemap-fighters.xml'
    ]
    
    for sitemap_url in sitemap_urls:
        try:
            print(f"Trying sitemap: {sitemap_url}")
            response = session.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                # Try to parse as XML
                try:
                    root = ET.fromstring(response.text)
                    # Look for URLs in sitemap
                    for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                        url_text = url_elem.text
                        if 'bjj-fighters/' in url_text:
                            fighter_url = url_text.split('bjj-fighters/')[-1]
                            if fighter_url:
                                fighter_urls.add(fighter_url)
                                print(f"Found fighter URL: {fighter_url}")
                except ET.ParseError:
                    # If not valid XML, try parsing as HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('loc')
                    for link in links:
                        url_text = link.get_text()
                        if 'bjj-fighters/' in url_text:
                            fighter_url = url_text.split('bjj-fighters/')[-1]
                            if fighter_url:
                                fighter_urls.add(fighter_url)
                                print(f"Found fighter URL: {fighter_url}")
                                
        except Exception as e:
            print(f"Error with sitemap {sitemap_url}: {e}")
            continue
    
    # If sitemap approach fails, fall back to crawling the A-Z list
    if not fighter_urls:
        print("Sitemap approach failed, trying A-Z list...")
        fighter_urls = get_fighter_urls_from_az_list()
    
    return list(fighter_urls)

def get_fighter_urls_from_az_list():
    """Fallback: Extract fighter URLs from the A-Z list"""
    fighter_urls = set()
    
    try:
        response = session.get(url_az, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that point to fighter pages
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if 'bjj-fighters/' in href:
                fighter_url = href.split('bjj-fighters/')[-1]
                if fighter_url:
                    fighter_urls.add(fighter_url)
        
        print(f"Found {len(fighter_urls)} fighter URLs from A-Z list")
        
    except Exception as e:
        print(f"Error getting A-Z list: {e}")
    
    return list(fighter_urls)

def get_fighter_data_from_url(fighter_url):
    """Get data for a fighter using a known URL"""
    url_name = url_fighters + fighter_url
    
    try:
        response = session.get(url_name, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract fighter name from the page
        fighter_name = "Unknown"
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            # Try to extract name from title
            if 'BJJ Heroes' in title_text:
                name_part = title_text.split('BJJ Heroes')[0].strip()
                if name_part:
                    fighter_name = name_part
        
        # Find the matches table
        matches_table = soup.find('table')
        if not matches_table:
            return None
            
        # Get table headers to understand the structure
        headers = []
        header_row = matches_table.find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Get all data rows
        data_rows = matches_table.find_all('tr')[1:]  # Skip header row
        
        if data_rows:
            fighter_data = {
                'name': fighter_name,
                'url': fighter_url,
                'matches': []
            }
            
            for row in data_rows:
                cells = row.find_all('td')
                if len(cells) >= len(headers):
                    match_data = {}
                    
                    # Map data to headers
                    for i, header in enumerate(headers):
                        if i < len(cells):
                            match_data[header] = cells[i].get_text(strip=True)
                    
                    if match_data:  # Only add non-empty matches
                        fighter_data['matches'].append(match_data)
            
            return fighter_data if fighter_data['matches'] else None
            
    except Exception as e:
        print(f"Error processing {fighter_url}: {e}")
        return None

def main():
    print("Starting fighter URL discovery from sitemap...")
    
    # Get all fighter URLs from sitemap
    fighter_urls = get_fighter_urls_from_sitemap()
    
    if not fighter_urls:
        print("No fighter URLs found!")
        return
    
    print(f"Discovered {len(fighter_urls)} fighter URLs")
    
    # Save URLs to file for reference
    with open('fighter_urls.txt', 'w') as f:
        for url in sorted(fighter_urls):
            f.write(url + '\n')
    print("Saved fighter URLs to fighter_urls.txt")
    
    # Process fighters with threading
    max_workers = 10
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_url = {executor.submit(get_fighter_data_from_url, fighter_url): fighter_url for fighter_url in fighter_urls}
        
        # Process completed tasks
        completed = 0
        for future in as_completed(future_to_url):
            fighter_url = future_to_url[future]
            completed += 1
            
            try:
                fighter_data = future.result()
                if fighter_data:
                    results.append(fighter_data)
                    
                # Print progress
                if completed % 10 == 0:
                    print(f"Processed {completed}/{len(fighter_urls)} fighters...")
                    
            except Exception as e:
                print(f"Error processing {fighter_url}: {e}")

    # Print results
    print(f"\nFound data for {len(results)} fighters with matches:")
    print("=" * 80)
    
    for fighter_data in results:
        print(f"Athlete: {fighter_data['name']} (URL: {fighter_data['url']})")
        
        for match in fighter_data['matches']:
            for header, value in match.items():
                if value:  # Only print non-empty values
                    print(f"  {header}: {value}")
            print("  ---")
        print('=' * 80)

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
