# Ragnar deck — chart-by-chart qualitative audit (2026-09-05)

Ben: "you need to look at each with a qualitative lens. does the data make sense, is it similar
to these examples, do we have the seeds we need, what can we substitute if needed."

Reference example: TAB Bank Data Science Insights (Fluid 2022) pp. 13–45 — one curated
named-entity list per category, y = correlation with the segment pole, x = political spectrum,
size = volume, grey "Average" band; paired with a Key Insight written from the entities that
moved. Source data for every row below: `06_scheme_L_2026/phase1/reports/ragnar_deck_data.json`
(segment `audience:saved:ragnar-race-core`, cycle 20260828T183159).

| chart | does the data make sense? | like the TAB example? | seeds / substitutions | verdict |
|---|---|---|---|---|
| Geography | Utah 3.5σ, WA, MN, NH, AK, WY, CO, WI, VT, AZ — every one a Ragnar race market; under-index NJ/LA/OK/SC/MO/MS/NY/KS/TX/IN. Reads as the race calendar. | TAB p.14 "Geographic opportunity" used lookalike-vs-market; ours is the client's own footprint (better for a regional brand). | Fingerprint of the 3 brand terms; negatives not applied (compose_pole takes positives). | SHIP |
| Competitors & Races | Relays cluster at the top (Reach the Beach, Red Rock, STP, Hood to Coast, Speed Project), Zion Half + Wasatch Back = own markets; Ironman the lone strong negative — coherent (team vs solo endurance). | TAB "ABL firms / competitive landscape". | 19/38 charted. Marathons mostly absent as rows (Boston via "boston marathon date"); Bourbon Chase dropped (unvolumed row, −0.02 on a Ragnar race = untrustworthy). Rugged Maniac/Warrior Dash/Color Run not in corpus → queued. | SHIP, thinnest chart; re-cut when the runragnar.com crawl lands (216,931 units queued) |
| Running & Fitness | Strava/Peloton/F45/OTF/NRC top; mass shoe brands + Planet Fitness below band; Ironman negative again. Sensible: specialist, social, group. | TAB "Hobbies". | 34/42. Altra via "altra shoes", On via "on running shoes". Dropped "half marathon training plan 16 weeks" (−0.04 on 1,300 vol — plan-page noise). | SHIP |
| Hobbies & Outdoors | Skiing (+0.157, top of study), snowboarding, paddle boarding, cycling, kayaking, climbing, hiking over; crochet/hunting/sourdough/gardening/video games under. Political axis sanity: hunting far right, yoga/meditation left. | TAB "Hobbies". | 30/34; gravel/XC-ski/snowshoe not rows → queued. | SHIP — strongest chart |
| Cars & Vans | Subaru ×3, Thule, Yakima, Rivian, Sprinter over; every pickup/Jeep under. **15 passenger van rental −0.053** — contradicts the 08-22 anchor read; the searchers (church groups, big families) are not the segment. Kept and stated as a correction. | TAB "Cars" (Ford top, Tesla negative — ours is the mirror: Subaru/Rivian top, Ram/F-150 bottom). | 34/35; "honda cr-v" via "honda crv"; Tesla Model Y unvolumed but plausible, kept. | SHIP with the correction on the insight slide |
| Travel & Lodging | Zion, Moab, St George, Cape Cod, Tahoe, Bend, "road trip", "national parks" over; Hyatt/Marriott over, Hampton/Super 8/Holiday Inn/Booking.com under; Yellowstone negative (different tourist). Corrects 08-22's "3-star near me". | TAB "Travel" (budget brands over — ours inverted, and said so). | 38/40; Priceline dropped (unvolumed), Park City/RV rental unvolumed → dropped. | SHIP with the correction |
| Gear & Retail | Road Runner Sports, Backcountry, Big 5, Dick's, REI, Scheels over + Trader Joe's/Nordstrom; Walmart/Amazon/Shein/Etsy/Lowe's under; Hydro Flask + / Yeti −. | TAB "Retail/brands". | 38/38; Temu dropped (unvolumed −0.09 — directionally right but unverifiable). | SHIP |
| Sports | Endurance/global leagues over (triathlon, Tour de France, X Games, MLS, World Cup, Olympics, F1), NFL flagships under, home-market teams (Jazz, RSL, BYU, Twins) over. | TAB "Sports" (NFL>NHL>MLB; NBA n.s.). | 44/47; "college football live"/"ncaa basketball live" dropped (streaming-intent substitutes, both negative). | SHIP |
| Food & Drink | Nuun electrolytes top, Clif/Kodiak, fast-casual (Sweetgreen, Chipotle, Cava, Dutch Bros), Utah chains (Cafe Rio, Swig) over; Body Armor, bourbon, Waffle House, Chick-fil-A, Texas Roadhouse under. Endurance nutrition ≠ sports drink — coherent. | no TAB analogue; category added for aid-station/co-brand relevance. | 33/37; Celsius/Liquid IV/Coors/Michelob not rows. | SHIP |
| Family & Life | Mortgage rates +0.107, daycare, dog park/boarding, Disneyland over; pregnancy −0.121 and pediatrician −0.104 (two weakest in study). Reads as a life stage (house + dog + daycare-age kids). | TAB "Family" (+4% parents, Baby Shark). | 29/32; "toddler"/"baby names" zero-volume placeholders dropped. | SHIP, worded as life stage, not demographic |
| Social & Media | Outside, WSJ, Atlantic, MSNBC, NPR, CNN over; YouTube/Paramount+/Disney+/Netflix/Facebook/Snapchat/TikTok under; Instagram neutral; Fox negative. Matches 08-22 "not social-first". | TAB "Social media" (FB/YouTube 1.5×) — ours is the inverse and the insight says why (the TV-fandom sense was subtracted). | 35/40; "new york times" dropped (unvolumed variant at +0.136 — implausible outlier vs "nytimes" anchor read in August). | SHIP |
| Politics & News | Max |h| 0.04 (ACLU); Fox/Newsmax/Hannity mildly negative; nothing in the top tier of any category. Null result = the finding. | TAB "Politics" was the strongest signal; the contrast is the point. | 34/41; zero-volume politician placeholders (trump/biden/sanders/desantis/cox) dropped — their h≈0 is a placeholder artefact, not a measurement. | SHIP with the null finding |
| Tech & Devices | Google Maps, MyFitnessPal, AllTrails, Komoot, Noom, Headspace, iPad over; Cash App/PayPal/Zelle, Yahoo Mail, Android, Starlink under. Inverse of TAB's Android/Hotmail customer. | TAB "Technology". | 36/39; dropped substitutes that changed meaning ("apple pay wallet", "ring doorbell camera price", "apple maps app", "zelle app") and unvolumed "nest thermostat" +0.119 / "iphone". | SHIP, weakest of the shipped charts |
| Movies & TV | Wild, Survivor, Amazing Race, Ninja Warrior, Unbroken, Top Gun over; GoT, Stranger Things, Dune, Friends, Barbie under; "vikings" neutral (the subtraction working). | TAB "Movies" (Braveheart/Top Gun). | 27/34; "chariots of fire song", "ted lasso soundtrack" dropped (song rows). | SHIP |
| Disambiguation | Sign flips on 8/13 on-target anchors; Norse anchors fall — from docs/RAGNAR_AUDIENCE_20260905.md §3.3. | TAB had no analogue; this is the methodology's differentiator. | z-normalised rows, live cycle. | SHIP |

Global decisions: (1) y is the segment correlation, not "lift vs Average Person" — the
20-generic-row control is a popularity axis (creatine seg +0.000 / "lift" −0.315), so the
average is a band (middle half of all charted entities), as TAB drew it. (2) Unvolumed rows
are dropped when their value is an outlier for the category; kept when plausible (Tesla
Model Y, Oura). (3) Every substitution is in `scripts/ragnar_deck_data.py::SUBSTITUTES`;
every exclusion in `render_charts.py::EXCLUDE`, with the reason. (4) Entities not in the
corpus were queued for onboarding by the engine (117 units, interactive tier) and will be
rows on the next cycle — re-run `ragnar_deck_data.py` then to thicken Competitors.
