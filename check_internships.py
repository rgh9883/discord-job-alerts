import json
import os
import time
import urllib.request

LISTINGS_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json"
SEEN_FILE = "seen_ids.json"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

# Load listings
with urllib.request.urlopen(LISTINGS_URL) as resp:
    listings = json.load(resp)

# Load previously seen ids (empty set on first run)
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen_ids = set(json.load(f))
else:
    seen_ids = set()

new_listings = [l for l in listings if l["id"] not in seen_ids and l.get("active", True)]

# Post oldest-first so the channel reads chronologically
new_listings.sort(key=lambda l: l["date_posted"])

for listing in new_listings:
    embed = {
        "title": f'{listing["company_name"]} — {listing["title"]}',
        "url": listing["url"],
        "description": ", ".join(listing["locations"]) or "Location not specified",
        "color": 3066993,
        "footer": {"text": ", ".join(listing["terms"])},
    }
    body = json.dumps({"embeds": [embed]}).encode()
    req = urllib.request.Request(WEBHOOK_URL, data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)
    time.sleep(1)  # stay well under Discord's rate limit

# Update seen state with every id currently in the feed (not just active ones,
# so a listing that gets marked inactive before we ever post it doesn't resurface)
all_ids = [l["id"] for l in listings]
with open(SEEN_FILE, "w") as f:
    json.dump(all_ids, f)

print(f"Posted {len(new_listings)} new listing(s).")