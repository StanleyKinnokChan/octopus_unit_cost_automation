import requests
import datetime
import pytz
import os
from dotenv import load_dotenv

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
period_from = f"{today.isoformat()}T00:00:00Z"
period_to = f"{(today + datetime.timedelta(days=1)).isoformat()}T00:00:00Z"

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

# Generate HTML with escaped curly braces in CSS
html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Daily Electricity Rates</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ text-align: center; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 600px; margin: auto; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>Electricity Rates for {today} (Agile Tariff)</h1>
    <p style="text-align: center;">Rates in p/kWh (inc. VAT). Updated daily. Times in local UK time.</p>
    <table>
        <tr>
            <th>From</th>
            <th>To</th>
            <th>Rate (p/kWh)</th>
        </tr>
""".format(today=today.strftime('%Y-%m-%d'))

for rate in results:
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
</body>
</html>
"""

# Write to public/index.html for Vercel
os.makedirs('public', exist_ok=True)
with open('public/index.html', 'w') as f:
    f.write(html)