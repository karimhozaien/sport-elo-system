import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv

# Create a session for connection pooling
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

def get_fighter_urls_from_sitemap():
    """Extract all fighter URLs from the sitemap XML"""
    sitemap_url = 'https://www.bjjheroes.com/post-sitemap.xml'
    fighter_urls = set()
    
    try:
        print(f"Fetching sitemap from: {sitemap_url}")
        response = session.get(sitemap_url, timeout=10)
        response.raise_for_status()
        
        # Parse the XML sitemap
        root = ET.fromstring(response.text)
        
        # Find all URL elements in the sitemap
        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
            url_text = url_elem.text
            if url_text and 'bjj-fighters/' in url_text:
                # Extract the fighter URL part
                fighter_url = url_text.split('bjj-fighters/')[-1]
                if fighter_url:
                    fighter_urls.add(fighter_url)
                    print(f"Found fighter URL: {fighter_url}")
        
        print(f"Total fighter URLs found: {len(fighter_urls)}")
        
    except ET.ParseError as e:
        print(f"Error parsing XML sitemap: {e}")
        return []
    except requests.RequestException as e:
        print(f"Error fetching sitemap: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
    
    return list(fighter_urls)

def get_fighter_data_from_url(fighter_url):
    """Get data for a fighter using a known URL"""
    url_name = f"https://www.bjjheroes.com/bjj-fighters/{fighter_url}"
    
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

def export_to_csv(results, filename='fighter_matches.csv'):
    """Export fighter match data to CSV file"""
    if not results:
        print("No data to export")
        return
    
    # Sort results alphabetically by fighter name
    results.sort(key=lambda x: x['name'].lower())
    
    # Get all unique headers from all matches
    all_headers = set()
    for fighter_data in results:
        for match in fighter_data['matches']:
            all_headers.update(match.keys())
    
    # Convert to list and add fighter info headers
    headers = ['Fighter_Name', 'Fighter_URL'] + list(all_headers)
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for fighter_data in results:
            fighter_name = fighter_data['name']
            fighter_url = fighter_data['url']
            
            for match in fighter_data['matches']:
                # Create row with fighter info and match data
                row = {
                    'Fighter_Name': fighter_name,
                    'Fighter_URL': fighter_url
                }
                # Add match data
                for header in all_headers:
                    row[header] = match.get(header, '')
                writer.writerow(row)
    
    print(f"Exported {sum(len(fighter['matches']) for fighter in results)} matches to {filename} (sorted alphabetically)")

def main():
    print("Starting sitemap-based fighter URL discovery...")
    
    # Get all fighter URLs from sitemap
    fighter_urls = get_fighter_urls_from_sitemap()
    
    if not fighter_urls:
        print("No fighter URLs found in sitemap!")
        return
    
    print(f"Discovered {len(fighter_urls)} fighter URLs from sitemap")
    
    # Save URLs to file for reference
    with open('fighter_urls_from_sitemap.txt', 'w') as f:
        for url in sorted(fighter_urls):
            f.write(url + '\n')
    print("Saved fighter URLs to fighter_urls_from_sitemap.txt")
    
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

    # Export to CSV
    export_to_csv(results, 'fighter_matches.csv')
    
    # Print results
    print(f"\nFound data for {len(results)} fighters with matches:")
    print("=" * 80)
    
    printed_names = set()  # Track which names have been printed
    
    for fighter_data in results:
        fighter_name = fighter_data['name']
        
        # Only print the name if we haven't seen it before
        if fighter_name not in printed_names:
            print(f"Athlete: {fighter_name} (URL: {fighter_data['url']})")
            printed_names.add(fighter_name)
        
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