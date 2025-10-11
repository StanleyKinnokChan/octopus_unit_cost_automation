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

# Get today's date in UTC (October 11, 2025, as per provided date)
today = datetime.date.today()
# Start from previous day 23:00 UTC to include 00:00 BST today
previous_day = today - datetime.timedelta(days=1)
period_from = f"{previous_day.isoformat()}T23:00:00Z"  # 00:00 BST today
period_to = f"{(today + datetime.timedelta(days=1)).isoformat()}T00:00:00Z"  # 01:00 BST tomorrow

# Fetch rates (handles pagination)
base_url = f"https://api.octopus.energy/v1/products/{PRODUCT_CODE}/electricity-tariffs/{TARIFF_CODE}/standard-unit-rates/"
params = {'period_from': period_from, 'period_to': period_to}
auth = (API_KEY, '')
results = []

url = base_url
while url:
    response = requests.get(url, params=params, auth=auth)
    response.raise_for_status()
    data = response.json()
    results.extend(data['results'])
    url = data.get('next')
    params = {}

# Sort by valid_from ascending
results.sort(key=lambda x: x['valid_from'])

# Convert times to Europe/London using pytz
uk_tz = pytz.timezone('Europe/London')

def format_time(iso_str):
    dt = datetime.datetime.fromisoformat(iso_str.rstrip('Z'))
    dt = dt.replace(tzinfo=pytz.UTC).astimezone(uk_tz)
    return dt.strftime('%H:%M')

# Filter results for today's date in local time (00:00 to 23:59 BST)
filtered_results = []
for rate in results:
    dt_from = datetime.datetime.fromisoformat(rate['valid_from'].rstrip('Z')).replace(tzinfo=pytz.UTC).astimezone(uk_tz)
    if dt_from.date() == today:
        filtered_results.append(rate)

# Sort filtered results (should already be sorted, but ensure)
filtered_results.sort(key=lambda x: x['valid_from'])

# Debug: Print fetched and filtered rates with BST times
print(f"Total rates fetched from API: {len(results)}")
print(f"Filtered rates for {today} (BST): {len(filtered_results)}")
print("Filtered rates (BST times):")
for rate in filtered_results:
    from_time = format_time(rate['valid_from'])
    to_time = format_time(rate['valid_to']) if rate['valid_to'] else 'Ongoing'
    value = round(rate['value_inc_vat'], 2)
    print(f"From {from_time} to {to_time}: {value} p/kWh")

# Verify full 24 hours (should be 48 slots)
if len(filtered_results) != 48:
    print(f"Warning: Expected 48 slots for full day, got {len(filtered_results)}")

# Parse events.en-GB.ics for next bin collection
ics_file = 'events.en-GB.ics'
next_bin_collection = None
try:
    with open(ics_file, 'r') as f:
        cal = Calendar.from_ical(f.read())
    # Find the next event on or after today
    for event in cal.walk('VEVENT'):
        dtstart = event.get('DTSTART').dt
        if isinstance(dtstart, datetime.datetime):
            dtstart = dtstart.date()  # Convert to date if datetime
        if dtstart >= today:
            summary = event.get('SUMMARY', 'Unknown waste type')
            next_bin_collection = {
                'date': dtstart,
                'waste_type': summary
            }
            break  # Take the first event on or after today
    if not next_bin_collection:
        print("Warning: No bin collection events found on or after today")
        next_bin_collection = {'date': today, 'waste_type': 'None scheduled'}
except FileNotFoundError:
    print(f"Error: {ics_file} not found")
    next_bin_collection = {'date': today, 'waste_type': 'Error: ICS file missing'}
except Exception as e:
    print(f"Error parsing ICS file: {e}")
    next_bin_collection = {'date': today, 'waste_type': 'Error: Unable to parse ICS'}

# Format the next bin collection date as "DD MMM YYYY (Day)"
bin_date_str = next_bin_collection['date'].strftime('%d %b %Y (%a)')
bin_waste_type = next_bin_collection['waste_type']

# Map English waste types to Chinese translations
waste_type_to_chinese = {
    'General waste': '一般垃圾',
    'Garden* and recycling': '花園垃圾+回收',
    'Recycling': '回收'
}
# Get Chinese translation or fallback to '未知' for unknown types
bin_waste_type_chinese = waste_type_to_chinese.get(bin_waste_type, '未知')
# Combine English and Chinese for display
bin_waste_display = f"{bin_waste_type} ({bin_waste_type_chinese})"

# Split results into two halves (roughly 24 entries each for 48 total)
midpoint = len(filtered_results) // 2
first_half = filtered_results[:midpoint]
second_half = filtered_results[midpoint:]

# Generate HTML with two side-by-side tables and bin collection
html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    <h1>⚡️Electricity Rates for {today} ({weekday})⚡️</h1>
    <p>Rates in p/kWh (inc. VAT). Updated daily. Times in local UK time.</p>
    <div class="table-container">
        <table>
            <tr>
                <th>From</th>
                <th>To</th>
                <th>Rate (p/kWh)</th>
            </tr>
""".format(today=today.strftime('%Y-%m-%d'), weekday=today.strftime('%a'))

# First half table
for rate in first_half:
    from_time = format_time(rate['valid_from'])
    to_time = format_time(rate['valid_to']) if rate['valid_to'] else 'Ongoing'
    value = round(rate['value_inc_vat'], 2)
    html += f"""
            <tr>
                <td>{from_time}</td>
                <td>{to_time}</td>
                <td>{value}</td>
            </tr>
    """

html += """
        </table>
        <table>
            <tr>
                <th>From</th>
                <th>To</th>
                <th>Rate (p/kWh)</th>
            </tr>
"""

# Second half table
for rate in second_half:
    from_time = format_time(rate['valid_from'])
    to_time = format_time(rate['valid_to']) if rate['valid_to'] else 'Ongoing'
    value = round(rate['value_inc_vat'], 2)
    html += f"""
            <tr>
                <td>{from_time}</td>
                <td>{to_time}</td>
                <td>{value}</td>
            </tr>
    """

html += """
        </table>
    </div>
    <p class="bin-info">🚮Next Bin Collection 下次收垃圾:</p>
    <p class="bin-info"> {bin_date} {waste_type}</p>
</body>
</html>
""".format(bin_date=bin_date_str, waste_type=bin_waste_display)

# Write to public/index.html for Vercel (with UTF-8 encoding)
os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html)