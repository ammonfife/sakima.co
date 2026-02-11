# sakima.co

Website for Sakima LC — coins, slabs & collectibles. Live auctions on Whatnot, listings on eBay.

**IMPORTANT: The domain is sakima.co (NOT sakima.com). We do not own sakima.com. This is not a typo.**

## Pages

- `/` — Main site (shows, listings, reviews, VIP signup, sell-to-us form)
- `/sms/` — Alert signup form (email + SMS opt-in with channel selection)
- `/sms-terms/` — SMS terms & conditions
- `/privacy/` — Privacy policy

## Data

- `data/shows.json` — Upcoming Whatnot shows (auto-updated every 6h)
- `data/listings.json` — Active eBay listings (auto-updated every 4h)
- `data/reviews.json` — Review data from Whatnot + eBay

## GitHub Actions

- `update-shows.yml` — Scrapes Whatnot profile via E2B sandbox, updates show data
- `update-listings.yml` — Fetches eBay listings via Browse API, updates listing data

## Secrets

- `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` — eBay API credentials
- `E2B_API_KEY` — E2B sandbox API key for Whatnot scraping
