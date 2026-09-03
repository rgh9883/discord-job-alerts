import json
import os
import time
import urllib.request
import urllib.error

LISTINGS_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json"
SEEN_FILE = "seen_ids.json"

# The repo's `category` field maps to one of these five buckets. A few legacy
# category strings show up on older entries, so normalize those too.
CATEGORY_MAP = {
    "Software": "SOFTWARE",
    "Software Engineering": "SOFTWARE",
    "AI/ML/Data": "AIML",
    "Data Science, AI & Machine Learning": "AIML",
    "Hardware": "HARDWARE",
    "Hardware Engineering": "HARDWARE",
    "Quant": "QUANT",
    "Product": "PRODUCT",
    "Product Management": "PRODUCT",
}

# One webhook secret per category, e.g. DISCORD_WEBHOOK_SOFTWARE. A category
# with no matching secret set is simply skipped.
WEBHOOKS = {
    key: os.environ[f"DISCORD_WEBHOOK_{key}"]
    for key in set(CATEGORY_MAP.values())
    if f"DISCORD_WEBHOOK_{key}" in os.environ
}

with urllib.request.urlopen(LISTINGS_URL) as resp:
    listings = json.load(resp)

active = [l for l in listings if l.get("active")]

if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen_ids = set(json.load(f))
else:
    seen_ids = set()

new_listings = [l for l in active if l["id"] not in seen_ids]
new_listings.sort(key=lambda l: l["date_posted"])


def post(webhook_url, listing):
    degrees = ", ".join(listing.get("degrees") or []) or "Not specified"
    embed = {
        "title": f'{listing["company_name"]} — {listing["title"]}',
        "url": listing["url"],
        "description": ", ".join(listing["locations"]) or "Location not specified",
        "color": 3066993,
        "fields": [{"name": "Degrees", "value": degrees, "inline": True}],
        "footer": {"text": ", ".join(listing["terms"])},
    }
    body = json.dumps({"embeds": [embed]}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "discord-job-alerts (github actions)"},
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        if e.code == 429:  # rate limited — back off and retry once
            time.sleep(5)
            urllib.request.urlopen(req)
        else:
            raise


posted = 0
for listing in new_listings:
    key = CATEGORY_MAP.get(listing.get("category"))
    webhook_url = WEBHOOKS.get(key)
    if not webhook_url:
        continue  # unrecognized category, or no webhook configured for it
    post(webhook_url, listing)
    posted += 1
    time.sleep(1)  # stay well under Discord's rate limit

# Mark every id currently in the feed as seen (active or not), so a listing
# that goes inactive before we ever post it doesn't resurface later.
all_ids = [l["id"] for l in listings]
with open(SEEN_FILE, "w") as f:
    json.dump(all_ids, f)

print(f"Posted {posted} new listing(s) across {len(WEBHOOKS)} configured channel(s).")