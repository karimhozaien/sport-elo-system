import requests
from bs4 import BeautifulSoup
import time

url = 'https://www.bjjheroes.com/'
url_az = url + '/a-z-bjj-fighters-list'

response = requests.get(url_az)
soup = BeautifulSoup(response.text, 'html.parser')

tables = soup.find_all('td')

for table in tables:
    names = table.find('a')
    if names:
        print(names.get_text(strip=True))