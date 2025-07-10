import csv
from collections import defaultdict
import re

# Elo parameters
INITIAL_RATING = 1500
K_NEW = 32  # K-factor for new fighters
K_ESTABLISHED = 16  # K-factor for established fighters
PROVISIONAL_MATCHES = 10  # Number of matches before a fighter is considered established

def clean_name(name):
    # Remove leading/trailing spaces, collapse multiple spaces, and fix repeated names
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)  # Collapse multiple spaces
    # Remove repeated names (e.g., 'Mica GalvaoMica Galvao' -> 'Mica Galvao')
    if len(name) % 2 == 0:
        half = len(name) // 2
        if name[:half] == name[half:]:
            name = name[:half]
    return name

# Read match data
matches = []
with open('fighter_matches.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Ensure Year and ID are integers for sorting
        row['Year'] = int(row['Year'])
        row['ID'] = int(row['ID'])
        matches.append(row)

# Sort matches by Year, then ID
matches.sort(key=lambda x: (x['Year'], x['ID']))

# Initialize ratings and match counts
ratings = defaultdict(lambda: INITIAL_RATING)
match_counts = defaultdict(int)

# Optionally, track rating history
rating_history = defaultdict(list)
# Track peak Elo and year
peak_elo = defaultdict(lambda: {'Rating': INITIAL_RATING, 'Year': None})

# Elo calculation
for match in matches:
    fighter = clean_name(match['Fighter_Name'])
    opponent = clean_name(match['Opponent'])
    year = match['Year']
    match_id = match['ID']
    result = match.get('W/L', '').strip().upper()  # 'W', 'L', or 'D'
    method = match.get('Method', '').strip().lower()

    # Get ratings
    rating_f = ratings[fighter]
    rating_o = ratings[opponent]
    count_f = match_counts[fighter]
    count_o = match_counts[opponent]

    # Expected scores
    expected_f = 1 / (1 + 10 ** ((rating_o - rating_f) / 400))
    expected_o = 1 - expected_f

    # Actual scores
    if result == 'W':
        actual_f, actual_o = 1, 0
    elif result == 'L':
        actual_f, actual_o = 0, 1
    elif result == 'D':
        actual_f, actual_o = 0.5, 0.5
    else:
        continue  # Skip if result is unknown

    # K-factor
    k_f = K_NEW if count_f < PROVISIONAL_MATCHES else K_ESTABLISHED
    k_o = K_NEW if count_o < PROVISIONAL_MATCHES else K_ESTABLISHED

    # Method multiplier logic
    if result == 'W':
        if 'adv' in method:
            multiplier = 0.8
        elif 'decision' in method:
            multiplier = 0.8
        elif 'pts' in method:
            multiplier = 1.0
        else:
            multiplier = 1.2  # treat as submission
    else:
        multiplier = 1.0  # default for loss/draw

    # Update ratings (apply multiplier only to winner's Elo change)
    ratings[fighter] = rating_f + k_f * (actual_f - expected_f) * multiplier
    ratings[opponent] = rating_o + k_o * (actual_o - expected_o) * (1.0 if result == 'W' else multiplier)

    # Update match counts
    match_counts[fighter] += 1
    match_counts[opponent] += 1

    # Record rating history
    rating_history[fighter].append({'Year': year, 'ID': match_id, 'Rating': ratings[fighter]})
    rating_history[opponent].append({'Year': year, 'ID': match_id, 'Rating': ratings[opponent]})

    # Track peak Elo and year for each fighter
    if ratings[fighter] > peak_elo[fighter]['Rating']:
        peak_elo[fighter]['Rating'] = ratings[fighter]
        peak_elo[fighter]['Year'] = year
    if ratings[opponent] > peak_elo[opponent]['Rating']:
        peak_elo[opponent]['Rating'] = ratings[opponent]
        peak_elo[opponent]['Year'] = year

# Export final ratings
with open('elo_ratings.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Fighter', 'Final_Rating', 'Matches']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for fighter, rating in sorted(ratings.items(), key=lambda x: -x[1]):
        writer.writerow({
            'Fighter': fighter,
            'Final_Rating': round(rating, 2),
            'Matches': match_counts[fighter]
        })

# Export rating history (optional)
with open('rating_history.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Fighter', 'Year', 'ID', 'Rating']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for fighter, history in rating_history.items():
        for entry in history:
            writer.writerow({
                'Fighter': fighter,
                'Year': entry['Year'],
                'ID': entry['ID'],
                'Rating': round(entry['Rating'], 2)
            })

# Export peak Elo and year
with open('peak_elo.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Fighter', 'Peak_Elo', 'Year']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for fighter, peak in sorted(peak_elo.items(), key=lambda x: -x[1]['Rating']):
        writer.writerow({
            'Fighter': fighter,
            'Peak_Elo': round(peak['Rating'], 2),
            'Year': peak['Year']
        })

print('Elo calculation complete. Results saved to elo_ratings.csv, rating_history.csv, and peak_elo.csv.') 