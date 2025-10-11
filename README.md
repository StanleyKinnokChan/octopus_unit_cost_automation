# Daily Electricity Rates Dashboard

This project generates a **static HTML dashboard** showing **daily electricity rates** (Octopus Energy Agile tariff) and the **next bin collection date** from a local ICS calendar file.

---

## Features

* **Electricity Rates:** Fetches half-hourly rates for the current day in BST (00:00–23:30) and displays them in two side-by-side tables (24 rows each) for tablet-friendly viewing.
* **Bin Collection Info:** Parses `events.en-GB.ics` to display the next bin collection date and type (e.g., *"13 Oct 2025 (Mon) — General waste"*).
* **Responsive Design:** Tables stay side-by-side on tablets (768px) and stack on phones (<400px).
* **Automated Updates:** Runs daily at **00:05 UTC** via GitHub Actions, also supports manual triggers.
* **Static Deployment:** Deploys automatically to **Vercel**.

---

## Example Output

**Title:** `Electricity Rates for 2025-10-11 (Sat)`
**Tables:** 48 half-hourly slots (00:00–23:30 BST) in p/kWh (inc. VAT)
**Bin Info:** `Next Bin Collection: 13 Oct 2025 (Mon) General waste`

---

## Setup

### Requirements

* Python 3.12
* Node.js 18 (for Vercel CLI)
* GitHub repository with Actions enabled
* Vercel account (free tier)
* Octopus Energy API key

### Installation

```bash
git clone https://github.com/StanleyKinnokChan/octopus_unit_cost_automation.git
cd ./octopus_unit_cost_automation.git
pip install -r requirements.txt
```

### Environment Variables (.env)

```env
OCTOPUS_API_KEY=your_octopus_api_key
OCTOPUS_PRODUCT_CODE=your_product_code  # e.g., AGILE-*-1
OCTOPUS_TARIFF_CODE=your_tariff_code    # e.g., E-1R-AGILE-FIXED-11M
```

### ICS File

Download from your local council website (e.g., Nottingham City Council):
https://www.nottinghamcity.gov.uk/information-for-residents/bin-and-rubbish-collections/check-my-bin-collection-day/


---

## Local Testing

```bash
python main.py
```

Generates `public/index.html`. Open it in a browser to verify:

* 48 rates (00:00–23:30 BST)
* Correct next bin event

---

## Deployment

### GitHub Actions Workflow (`.github/workflows/update-rates.yml`)

**Triggers:**

* Daily (cron: `5 0 * * *`)
* Manual push (excluding bot commits)
* Manual trigger via `workflow_dispatch`

**Steps:**

1. Check out code
2. Install dependencies
3. Run `main.py` to generate HTML
4. Commit and push results
5. Deploy to Vercel

**Secrets (GitHub → Settings → Secrets and variables → Actions):**

* `OCTOPUS_API_KEY`
* `OCTOPUS_PRODUCT_CODE`
* `OCTOPUS_TARIFF_CODE`
* `VERCEL_TOKEN`
* `VERCEL_ORG_ID`
* `VERCEL_PROJECT_ID`

### Vercel Setup

* **Framework Preset:** Static Site
* **Output Directory:** `public`
* **Build Command:** *(empty)*
* **Install Command:** *(empty)*

**Optional `vercel.json`:**

```json
{
  "buildCommand": "",
  "outputDirectory": "public",
  "routes": [
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```

---

## Files

* `main.py` — Fetches rates, parses ICS, generates `public/index.html`.
* `events.en-GB.ics` — Bin collection data.
* `requirements.txt` — Dependencies.
* `.env` — Local API config.
* `.github/workflows/update-rates.yml` — Automation & deployment.

---

## Customization

* **Tariffs:** Change `PRODUCT_CODE`/`TARIFF_CODE` for other regions.
* **Bin Calendar:** Replace `events.en-GB.ics` or adjust parsing for different formats.
* **Layout:** Edit CSS in `main.py`.
* **Timezone:** Default `Europe/London` (BST).

---

## Troubleshooting

* **404 on Vercel:** Ensure `public/index.html` exists.
* **Missing Rates:** Verify 48 slots and API access.
* **ICS Errors:** Check `events.en-GB.ics` format.
* **Bot Loop:** Ensure `github.actor != 'github-actions[bot]'`.

---

## License

MIT License

**Deployed at:** [octopus-unit-cost-automation.vercel.app](https://octopus-unit-cost-automation.vercel.app)
**Updates:** Generated daily at 00:05 UTC
