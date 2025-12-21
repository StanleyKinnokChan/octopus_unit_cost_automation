import requests
import datetime
import pytz
import os
from dotenv import load_dotenv
from icalendar import Calendar

# Load environment variables from .env file (for local development)
load_dotenv()

# Config from environment variables
API_KEY = os.getenv('OCTOPUS_API_KEY')
PRODUCT_CODE = os.getenv('OCTOPUS_PRODUCT_CODE')
TARIFF_CODE = os.getenv('OCTOPUS_TARIFF_CODE')

# Validate environment variables
if not all([API_KEY, PRODUCT_CODE, TARIFF_CODE]):
    raise ValueError("Missing required environment variables: OCTOPUS_API_KEY, OCTOPUS_PRODUCT_CODE, or OCTOPUS_TARIFF_CODE")

# Get tomorrow's date (since we run at 22:00 UTC to fetch next day's rates)
today = datetime.date.today()
tomorrow = today + datetime.timedelta(days=1)
yesterday = today - datetime.timedelta(days=1)

# Request a wider range to ensure we get data
period_from = f"{yesterday.isoformat()}T00:00:00Z"
period_to = f"{(tomorrow + datetime.timedelta(days=1)).isoformat()}T23:59:59Z"

print(f"Today: {today}")
print(f"Tomorrow: {tomorrow}")
print(f"Requesting rates from {period_from} to {period_to}")

# Fetch rates
base_url = f"https://api.octopus.energy/v1/products/{PRODUCT_CODE}/electricity-tariffs/{TARIFF_CODE}/standard-unit-rates/"
params = {'period_from': period_from, 'period_to': period_to}
auth = (API_KEY, '')
results = []

url = base_url
while url:
    print(f"Fetching from URL: {url}")
    response = requests.get(url, params=params, auth=auth)
    response.raise_for_status()
    data = response.json()
    print(f"API returned {len(data['results'])} results")
    results.extend(data['results'])
    url = data.get('next')
    params = {}

results.sort(key=lambda x: x['valid_from'])

uk_tz = pytz.timezone('Europe/London')

def format_time(iso_str):
    dt = datetime.datetime.fromisoformat(iso_str.rstrip('Z'))
    dt = dt.replace(tzinfo=pytz.UTC).astimezone(uk_tz)
    return dt.strftime('%H:%M')

# Filter tomorrow's results (preferred), fallback to today's if not available
filtered_results = []
target_date = tomorrow

for rate in results:
    dt_from = datetime.datetime.fromisoformat(rate['valid_from'].rstrip('Z')).replace(tzinfo=pytz.UTC).astimezone(uk_tz)
    if dt_from.date() == target_date:
        filtered_results.append(rate)

# Fallback: if tomorrow's rates aren't available yet, use today's
if len(filtered_results) == 0:
    print(f"Tomorrow's rates not available yet, falling back to today's rates")
    target_date = today
    for rate in results:
        dt_from = datetime.datetime.fromisoformat(rate['valid_from'].rstrip('Z')).replace(tzinfo=pytz.UTC).astimezone(uk_tz)
        if dt_from.date() == target_date:
            filtered_results.append(rate)

filtered_results.sort(key=lambda x: x['valid_from'])

# Identify 6 cheapest slots
sorted_by_price = sorted(filtered_results, key=lambda x: x['value_inc_vat'])
cheapest_slots = set(r['valid_from'] for r in sorted_by_price[:6])

print(f"Total rates fetched: {len(results)}")
print(f"Filtered rates for {target_date}: {len(filtered_results)}")

# Parse ICS file
ics_file = 'events.en-GB.ics'
next_bin_collection = None
try:
    with open(ics_file, 'r') as f:
        cal = Calendar.from_ical(f.read())
    for event in cal.walk('VEVENT'):
        dtstart = event.get('DTSTART').dt
        if isinstance(dtstart, datetime.datetime):
            dtstart = dtstart.date()
        if dtstart >= target_date:
            summary = event.get('SUMMARY', 'Unknown waste type')
            next_bin_collection = {'date': dtstart, 'waste_type': summary}
            break
    if not next_bin_collection:
        next_bin_collection = {'date': target_date, 'waste_type': 'None scheduled'}
except FileNotFoundError:
    next_bin_collection = {'date': target_date, 'waste_type': 'Error: ICS file missing'}
except Exception as e:
    next_bin_collection = {'date': target_date, 'waste_type': 'Error: Unable to parse ICS'}

bin_date_str = next_bin_collection['date'].strftime('%d %b %Y (%a)')
bin_waste_type = next_bin_collection['waste_type']

waste_type_to_chinese = {
    'General waste': '一般垃圾',
    'Garden* and recycling': '花園垃圾+回收',
    'Recycling': '回收'
}

bin_waste_type_chinese = waste_type_to_chinese.get(bin_waste_type, '未知')
bin_waste_display = f"{bin_waste_type} ({bin_waste_type_chinese})"

midpoint = len(filtered_results) // 2
first_half = filtered_results[:midpoint]
second_half = filtered_results[midpoint:]

# Build HTML safely using f-string (no .format with braces)
html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Daily Electricity Rates</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 10px; padding: 0; }}
h1 {{ text-align: center; font-size: 1.5em; margin: 10px 0; }}
p {{ text-align: center; font-size: 0.9em; margin: 5px 0; }}
.table-container {{ display: flex; flex-direction: row; justify-content: center; gap: 8px; max-width: 100%; }}
table {{ border-collapse: collapse; width: 48%; max-width: 250px; flex: 1; }}
th, td {{ border: 1px solid #ddd; padding: 3px; text-align: center; font-size: 0.8em; }}
th {{ background-color: #f2f2f2; }}
tr:nth-child(even) {{ background-color: #f9f9f9; }}
.bin-info {{ text-align: center; font-size: 0.9em; margin-top: 10px; }}
@media (max-width: 400px) {{
    .table-container {{ flex-direction: column; align-items: center; }}
    table {{ width: 100%; max-width: 100%; }}
}}
</style>
</head>
<body>
<h1>⚡️Electricity Rates for {target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%a')})⚡️</h1>
<p>Rates in p/kWh (inc. VAT). Updated daily at 22:00 UTC. Times in local UK time.</p>
<div class='table-container'>
<table>
<tr><th>From</th><th>To</th><th>Rate (p/kWh)</th></tr>
"""

# First table
for rate in first_half:
    from_time = format_time(rate['valid_from'])
    to_time = format_time(rate['valid_to']) if rate['valid_to'] else 'Ongoing'
    value = round(rate['value_inc_vat'], 2)
    suffix = '**' if rate['valid_from'] in cheapest_slots else ''
    html += f"<tr><td>{from_time}</td><td>{to_time}</td><td>{value}{suffix}</td></tr>\n"

html += "</table><table><tr><th>From</th><th>To</th><th>Rate (p/kWh)</th></tr>\n"

# Second table
for rate in second_half:
    from_time = format_time(rate['valid_from'])
    to_time = format_time(rate['valid_to']) if rate['valid_to'] else 'Ongoing'
    value = round(rate['value_inc_vat'], 2)
    suffix = '**' if rate['valid_from'] in cheapest_slots else ''
    html += f"<tr><td>{from_time}</td><td>{to_time}</td><td>{value}{suffix}</td></tr>\n"

html += f"""</table></div>
<p class='bin-info'>🚮Next Bin Collection 下次收垃圾:</p>
<p class='bin-info'>{bin_date_str} {bin_waste_display}</p>
</body>
</html>"""

os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
