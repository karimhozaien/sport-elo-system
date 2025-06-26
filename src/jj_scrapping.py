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
        matches = soup.find_all('td')
        
        if matches:
            # Print athlete name
            print(f"Athlete: {first_name} {last_name}")
            # Print matches in groups of 7
            for i in range(0, len(matches), 7):
                if i + 6 < len(matches):
                    opponent = matches[i+1].get_text(strip=True)
                    result = matches[i+2].get_text(strip=True)
                    method = matches[i+3].get_text(strip=True)
                    competition = matches[i+4].get_text(strip=True)
                    weight = matches[i+5].get_text(strip=True)
                    stage = matches[i+6].get_text(strip=True)
                    year = matches[i+7].get_text(strip=True)
                    print(f"  Opponent: {opponent}")
                    print(f"  Result: {result}")
                    print(f"  Method: {method}")
                    print(f"  Competition: {competition}")
                    print(f"  Weight: {weight}")
                    print(f"  Stage: {stage}")
                    print(f"  Year: {year}")
                    print("  ---")
            print('=' * 80)
