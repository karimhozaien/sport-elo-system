from curses.ascii import islower

import requests
from bs4 import BeautifulSoup

url = 'https://www.bjjheroes.com/'
url_az = url + '/a-z-bjj-fighters-list'
url_fighters = url + 'bjj-fighters/'

response = requests.get(url_az)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all first and last names
first_names = soup.find_all('td', class_='column-1')
last_names = soup.find_all('td', class_='column-2')

# Iterate over the names and print only those with matches
if first_names and last_names:
    for first, last in zip(first_names, last_names):
        first_name = first.get_text(strip=True)
        last_name = last.get_text(strip=True)
        url_name = url_fighters + first_name + '-' + last_name
        response_name = requests.get(url_name)
        soup = BeautifulSoup(response_name.text, 'html.parser')
        
        # Find the matches table
        matches_table = soup.find('table')
        if not matches_table:
            continue
            
        # Get table headers to understand the structure
        headers = []
        header_row = matches_table.find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Get all data rows
        data_rows = matches_table.find_all('tr')[1:]  # Skip header row
        
        if data_rows:
            print(f"Athlete: {first_name}")
            
            for row in data_rows:
                cells = row.find_all('td')
                if len(cells) >= len(headers):
                    match_data = {}
                    
                    # Map data to headers
                    for i, header in enumerate(headers):
                        if i < len(cells):
                            match_data[header] = cells[i].get_text(strip=True)
                    
                    # Print match data using header names
                    for header, value in match_data.items():
                        if value:  # Only print non-empty values
                            print(f"  {header}: {value}")
                    print("  ---")
            print('=' * 80)
