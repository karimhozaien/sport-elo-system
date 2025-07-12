import csv
from collections import defaultdict
import re
from typing import Dict, Tuple
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'old_scraper')))
from name_normalizer import normalize_fighter_name

# Elo parameters
INITIAL_RATING = 1500
K_NEW = 32  # K-factor for new fighters
K_ESTABLISHED = 16  # K-factor for established fighters
PROVISIONAL_MATCHES = 10  # Number of matches before a fighter is considered established

def clean_name(name):
    # Remove leading/trailing spaces, collapse multiple spaces, and fix repeated names
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)  # Collapse multiple spaces
    # Remove repeated names
    if len(name) % 2 == 0:
        half = len(name) // 2
        if name[:half] == name[half:]:
            name = name[:half]
    return name

def get_competition_multiplier(competition, result, event_multipliers=None):
    """
    Returns the competition multiplier for a given competition and result.
    event_multipliers: dict mapping event keyword (lowercase) to multiplier (applied only if result == 'W')
    """
    if event_multipliers is None:
        event_multipliers = {'adcc': 2.0}  # Default: ADCC 2x
    competition = competition.lower()
    if result == 'W':
        for event, multiplier in event_multipliers.items():
            if event in competition:
                return multiplier
    return 1.0

def get_stage_multiplier(competition, stage):
    competition = competition.lower()
    stage = stage.strip().upper()
    if 'adcc' or 'cji' or 'one fc' or 'ufc' in competition:
        if stage == 'F':
            return 2.5
        elif stage == 'SF':
            return 2.0
        elif stage == 'QF':
            return 1.25
        else:
            return 1.0
    else:
        if stage == 'SF':
            return 1.1
        elif stage == 'F':
            return 1.2
        else:
            return 1.0

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

# track rating history
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
    competition = match.get('Competition', '').strip().lower()
    stage = match.get('Stage', '').strip().upper()

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
            multiplier = 1.5  # treat as submission
    else:
        multiplier = 1.0  # default for loss/draw

    # Competition multiplier (only for winner)
    comp_multiplier_f = get_competition_multiplier(
        competition,
        result,
        event_multipliers={
            'adcc': 2.5,
            'world champ': 1.2,
            'one fc': 2.0,
            'ufc': 2.0,
            'cji': 2.5,
        }
    )
    comp_multiplier_o = 1.0  # Loser/opponent never gets the event multiplier

    # Stage multiplier
    stage_multiplier = get_stage_multiplier(competition, stage)

    # Update ratings (apply all multipliers)
    ratings[fighter] = rating_f + k_f * (actual_f - expected_f) * multiplier * comp_multiplier_f * stage_multiplier
    ratings[opponent] = rating_o + k_o * (actual_o - expected_o) * (1.0 if result == 'W' else multiplier) * comp_multiplier_o * stage_multiplier

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

# Export combined Elo ratings: name, peak elo, peak elo year, current elo, number of matches
combined = {}
for fighter, rating in ratings.items():
    normalized_name = normalize_fighter_name(clean_name(fighter))
    # For display, use a cleaned, title-cased version of the normalized name
    display_name = normalize_fighter_name(clean_name(fighter)).title()
    peak = peak_elo.get(fighter, {'Rating': rating, 'Year': None, 'Fighter': display_name})
    entry = {
        'Fighter': display_name,
        'Peak_Elo': round(peak['Rating'] if peak['Rating'] is not None else INITIAL_RATING, 2),
        'Peak_Elo_Year': peak['Year'],
        'Current_Elo': round(rating if rating is not None else INITIAL_RATING, 2),
        'Matches': match_counts[fighter]
    }
    # Only keep the record with the highest peak elo for each unique normalized name
    if normalized_name not in combined or entry['Peak_Elo'] > combined[normalized_name]['Peak_Elo']:
        combined[normalized_name] = entry

# Filter out fighters with less than 10 matches
MIN_MATCHES = 10
filtered_combined = {k: v for k, v in combined.items() if v['Matches'] >= MIN_MATCHES}

# Print filtering statistics
total_fighters = len(combined)
filtered_fighters = len(filtered_combined)
removed_fighters = total_fighters - filtered_fighters
print(f"Filtering fighters with less than {MIN_MATCHES} matches:")
print(f"Total fighters: {total_fighters}")
print(f"Fighters with {MIN_MATCHES}+ matches: {filtered_fighters}")
print(f"Fighters removed: {removed_fighters}")

with open('elo_ratings.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Fighter', 'Peak_Elo', 'Peak_Elo_Year', 'Current_Elo', 'Matches']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in sorted(filtered_combined.values(), key=lambda x: -x['Current_Elo']):
        writer.writerow(row)

# Export rating history
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

# After rating_history is built and before the final print
# Write out the top 3 Elo ratings at the end of each year to a CSV
year_end_elos: Dict[int, Dict[str, Tuple[int, float]]] = {}
for fighter, history in rating_history.items():
    for entry in history:
        try:
            year = int(entry['Year'])
            match_id = int(entry['ID'])
            elo = float(entry['Rating'])
        except (ValueError, TypeError):
            continue
        if year not in year_end_elos:
            year_end_elos[year] = {}
        prev = year_end_elos[year].get(fighter)
        # Only keep the last Elo for each fighter in each year
        if prev is None or (isinstance(prev, tuple) and len(prev) == 2 and isinstance(prev[0], int) and match_id > prev[0]):
            year_end_elos[year][fighter] = (match_id, elo)

with open('top3_by_year.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Year', 'Rank', 'Fighter', 'Elo']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for year in sorted(year_end_elos.keys()):
        # Grab all the (fighter, elo) pairs for this year
        fighter_elos = []
        for fighter, data in year_end_elos[year].items():
            if isinstance(data, tuple) and len(data) == 2 and isinstance(data[1], float):
                fighter_elos.append((fighter, data[1]))
        # Sort by Elo, highest first
        fighter_elos.sort(key=lambda x: -x[1])
        # Write out the top 3 for this year
        for rank, (fighter, elo) in enumerate(fighter_elos[:3], 1):
            writer.writerow({'Year': int(year), 'Rank': int(rank), 'Fighter': fighter, 'Elo': round(elo, 2)})

print('Elo calculation complete. Results saved to elo_ratings.csv, rating_history.csv, and top3_by_year.csv.')
print(f'Note: Only fighters with {MIN_MATCHES}+ matches are included in elo_ratings.csv.') 