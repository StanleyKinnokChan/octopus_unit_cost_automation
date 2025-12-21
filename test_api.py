import requests
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OCTOPUS_API_KEY')
PRODUCT_CODE = os.getenv('OCTOPUS_PRODUCT_CODE')
TARIFF_CODE = os.getenv('OCTOPUS_TARIFF_CODE')

today = datetime.date.today()
tomorrow = today + datetime.timedelta(days=1)
yesterday = today - datetime.timedelta(days=1)

# Test 1: Request yesterday to tomorrow (wide range)
print("=" * 60)
print("TEST 1: Wide range (yesterday to day after tomorrow)")
print("=" * 60)
period_from = f"{yesterday.isoformat()}T00:00:00Z"
period_to = f"{(tomorrow + datetime.timedelta(days=1)).isoformat()}T23:59:59Z"

print(f"Today: {today}")
print(f"Requesting from: {period_from}")
print(f"Requesting to: {period_to}")

url = f"https://api.octopus.energy/v1/products/{PRODUCT_CODE}/electricity-tariffs/{TARIFF_CODE}/standard-unit-rates/"
params = {'period_from': period_from, 'period_to': period_to}
auth = (API_KEY, '')

response = requests.get(url, params=params, auth=auth)
print(f"Status Code: {response.status_code}")
data = response.json()
print(f"Results returned: {len(data['results'])}")

if len(data['results']) > 0:
    print(f"\nFirst result: {data['results'][0]}")
    print(f"Last result: {data['results'][-1]}")
    
    # Show what dates we got
    dates = set()
    for rate in data['results']:
        dt = datetime.datetime.fromisoformat(rate['valid_from'].rstrip('Z'))
        dates.add(dt.date())
    
    print(f"\nDates available in response:")
    for date in sorted(dates):
        print(f"  - {date}")
else:
    print("\nNo results returned!")
    print(f"Response: {data}")

# Test 2: Request just tomorrow
print("\n" + "=" * 60)
print("TEST 2: Just tomorrow's date")
print("=" * 60)
period_from = f"{tomorrow.isoformat()}T00:00:00Z"
period_to = f"{(tomorrow + datetime.timedelta(days=1)).isoformat()}T00:00:00Z"

print(f"Requesting from: {period_from}")
print(f"Requesting to: {period_to}")

params = {'period_from': period_from, 'period_to': period_to}
response = requests.get(url, params=params, auth=auth)
data = response.json()
print(f"Results returned: {len(data['results'])}")
