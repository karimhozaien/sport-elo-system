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

# Iterate over the names and print them
if first_names and last_names:
    for first, last in zip(first_names, last_names):
        print(first.get_text(strip=True))
        print(last.get_text(strip=True))

        url_name = url_fighters + first.get_text(strip=True) +'-' + last.get_text(strip=True)
        print(url_name)