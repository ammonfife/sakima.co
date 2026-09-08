# CHART_AUDIT.md — Vacation Races (Heimdall correlation deck)

Status: PRE-ENGINE TEMPLATE. Every "Observed" field is empty by design. Fill after the scoring pass; do not edit the "Expected" or "Drop/Merge rule" fields after the fact without noting the change.

## Global gates (apply to every category before the per-category rules)

| Gate | Threshold | Action if failed |
|---|---|---|
| Entities resolved in corpus | >= 20 of the named list | Drop category, or merge into nearest sibling if >= 12 resolve |
| Median |r| across resolved entities | >= 0.05 | Drop as "flat" unless the flatness itself is the story (note it) |
| Spread (top-5 mean r minus bottom-5 mean r) | >= 0.10 | Merge with sibling; a chart with no spread teaches nothing |
| Entities with volume below floor | <= 25% of resolved | Grey them out on the chart; exclude from ranking text |
| Sense contamination | 0 entities whose top co-terms are from a declared negative sense | Re-run with stronger negative seeds before charting |
| Sign sanity | Seed-adjacent entities (Zion NP, Garmin, Hoka) must be positive | If negative, the pole is inverted or collapsed; stop and fix the segment |

Chart form for every category: horizontal bar, entities sorted by r, positive right / negative left, volume as bar opacity, baseline zero line, top 15 and bottom 5 shown, remainder in appendix table.

---

## 1. running_footwear_apparel — Running Shoe & Apparel Brands

Expected: Hoka, Altra, Salomon, Brooks, La Sportiva, Topo at the top. Nike/Adidas near zero (everyone searches them). Lululemon, Gymshark, Under Armour slightly negative. Sock brands (Darn Tough, Injinji, Balega) positive and a good "niche proof" talking point.
Story if it lands: "This audience shops trail-first brands; the fashion-athleisure money is wasted on them."
Drop if: spread < 0.10 or Nike/Adidas top the chart (means the pole collapsed into generic running).
Merge with: outdoor_retail, if both are thin; combined title "Where They Shop and What They Wear."
Observed: ___ resolved / median r ___ / spread ___ / verdict ___

## 2. outdoor_retail — Outdoor & Sporting Goods Retailers

Expected: REI, Backcountry, Fleet Feet, Running Warehouse, Public Lands strongly positive. Walmart, Target, Amazon near zero or negative. Regional shops (Salt Lake Running Co, Boulder Running Co, Scheels) positive but low volume; grey-out likely.
Story if it lands: "REI co-op partnership is the single highest-leverage retail relationship."
Drop if: only national chains resolve and they all cluster near zero.
Merge with: running_footwear_apparel.
Observed: ___

## 3. national_parks_public_lands — National Parks & Public Lands

Expected: Very strong positives across the board because park names are in the seeds; this is partly circular. The useful signal is the RANK ORDER of parks with no Vacation Races event (Arches, Canyonlands, Olympic, Rainier, Acadia, Joshua Tree, Big Bend). Iceland sites (Thingvellir, Vatnajokull) positive but low volume.
Story if it lands: "Expansion list: parks this audience already searches where you have no race."
Drop if: never; but if circularity dominates (every park > 0.3 with no rank separation), re-score with event-name seeds removed from the pole and chart that version instead. Note the re-score in this file.
Merge with: adventure_activities if the activities chart is thin.
Observed: ___

## 4. race_series_competitors — Race Series & Competing Events

Expected: Revel, Rock 'n' Roll, runDisney, St. George Marathon, Big Sur, Ragnar positive (same buyer). Boston/Chicago/NYC positive but weaker (aspirational). Spartan/Tough Mudder near zero or negative. Ironman near zero. Ultras (Western States, Leadville, UTMB) mildly positive; if strongly positive, the segment drifted toward ultrarunners and the persona page must say so.
Story if it lands: "Your real competitive set is Revel and runDisney, not Ironman."
Drop if: fewer than 20 events resolve (many are regional and low-volume). Likely the thinnest category by volume.
Merge with: none; if thin, keep as a 10-entity mini-chart inside the competitive-set strategy page rather than a standalone.
Observed: ___

## 5. travel_booking_platforms — Travel Booking & Trip-Planning Platforms

Expected: Airbnb, VRBO, Recreation.gov, Hipcamp, AllTrails, Roadtrippers, Outdoorsy, Escape Campervans positive. Expedia, Priceline, Trivago near zero. Cruise-adjacent and Costco Travel negative or zero (negative-sense check on "vacation").
Story if it lands: "They book direct and stay in rentals; OTA display is the wrong channel, Airbnb/VRBO co-marketing is the right one."
Drop if: everything clusters near zero (booking platforms are searched by everyone; low spread is a real risk).
Merge with: lodging_hospitality into "How They Book and Where They Stay."
Observed: ___

## 6. airlines_ground_transport — Airlines & Ground Transportation

Expected: Southwest, Delta, Alaska, Icelandair positive; Spirit/Frontier near zero or negative; rental cars uniformly positive; SLC/LAS/JAC/BZN/FCA airports positive. TSA PreCheck / Global Entry / Clear positive (frequent-traveler signal).
Story if it lands: "Icelandair and Southwest are the two airline partnership conversations worth having."
Drop if: airline spread < 0.10 (airlines are broadly searched). Airports and rental cars will likely carry the chart.
Merge with: travel_booking_platforms if airlines are flat; keep airports + rental cars as the surviving sub-chart.
Observed: ___

## 7. lodging_hospitality — Lodging, Camping & Hospitality Brands

Expected: Gateway properties (Zion Lodge, Cable Mountain, Tenaya, Jackson Lake Lodge, Under Canvas, KOA, Ruby's Inn) strongly positive but low volume. Mid-scale chains (Hampton, Holiday Inn Express, Best Western, La Quinta) positive. Luxury (Four Seasons class; none named, Ahwahnee proxies it) mixed. Motel 6 / Super 8 near zero.
Story if it lands: "Race-weekend room blocks belong at Hampton/Best Western tier plus glamping, not luxury."
Drop if: gateway properties fail volume floor AND chains are flat. Likely partial: keep chains + Under Canvas/KOA, appendix the rest.
Merge with: travel_booking_platforms.
Observed: ___

## 8. fitness_tech_wearables — Fitness Tech, Wearables & Training Apps

Expected: Garmin, Strava, COROS, Suunto, TrainingPeaks, Runna, Gaia GPS, onX, Garmin inReach, Shokz strongly positive. Peloton, Zwift, Noom, Calm negative or zero. Apple Watch near zero (too broad). GoPro/Insta360 positive.
Story if it lands: "Garmin + Strava are the audience's operating system; a Strava club challenge is a near-free acquisition channel."
Drop if: never expected to fail; this should be the cleanest chart in the deck. If it is flat, the pole is broken.
Merge with: none.
Observed: ___

## 9. nutrition_hydration — Sports Nutrition & Hydration

Expected: GU, Maurten, Tailwind, Skratch, Nuun, LMNT, Honey Stinger, Spring Energy, Precision positive. Gatorade near zero. Premier/Quest/Orgain near zero or negative. Hydration vests (Nathan, Salomon, CamelBak, Osprey) positive. Stanley Cup near zero (mass fad).
Story if it lands: "Course nutrition sponsor shortlist: Tailwind, Honey Stinger, Skratch, LMNT."
Drop if: gel/electrolyte brands fail volume floor (niche brands are low-volume). If only Gatorade/Liquid IV/Celsius resolve, drop.
Merge with: running_footwear_apparel as a "Gear and Fuel" page.
Observed: ___

## 10. adventure_activities — Adjacent Outdoor Activities & Trip Add-Ons

Expected: Hiking, Angels Landing, The Narrows, Half Dome Permit, canyoneering, hot springs, stargazing, dark sky, backpacking, glamping, Utah Mighty 5, Ring Road, Northern Lights positive. Golf, spa, wine tasting near zero or negative. Skiing mixed by season.
Story if it lands: "Sell the trip, not the race: the add-on itinerary is the conversion lever."
Drop if: generic words (hiking, camping, road trip) dominate with no spread among specifics; then re-score using only the named specifics (Angels Landing, Half Dome, Blue Lagoon) and chart those.
Merge with: national_parks_public_lands.
Observed: ___

## 11. media_content_community — Running & Outdoor Media, Podcasts, Creators

Expected: Runner's World, iRunFar, Trail Runner Mag, Outside, Believe in the Run, Ginger Runner, Courtney Dauwalter, Sally McRae, Dirtbag Diaries, Bearfoot Theory, Dirt in My Shoes, Earth Trekkers, r/nationalparks positive. Huberman, Rich Roll mildly positive. Yes Theory / Kara and Nate mixed. Sports-talk (none named) absent by design.
Story if it lands: "Media plan: podcast reads on SWAP / Nobody Asked Us, creator partnerships with park-itinerary bloggers."
Drop if: individual creators and podcasts fail volume floor en masse. Likely partial: publications and Reddit survive, individual creators go to appendix.
Merge with: none; if thin, fold surviving entities into the creative-direction strategy page.
Observed: ___

## 12. causes_charities — Causes, Charities & Conservation

Expected: National Park Foundation, NPCA, Leave No Trace, park-specific conservancies (Yosemite Conservancy, Yellowstone Forever, Zion Forever), Protect Our Winters, Access Fund, Trail Sisters, Girls on the Run positive. Susan G. Komen, Relay for Life, Wounded Warrior near zero. Team in Training / St. Jude Heroes mildly positive.
Story if it lands: "Cause-marketing partner should be a park conservancy, not a disease charity."
Drop if: park conservancies fail volume floor and only the big-name charities resolve at zero. Plausible failure; conservancies are small.
Merge with: national_parks_public_lands (conservancies map 1:1 to parks).
Observed: ___

## 13. vehicles_gear_haul — Vehicles, Roof Boxes & Road-Trip Gear

Expected: Subaru Outback/Forester/Crosstrek, 4Runner, Tacoma, Rivian, Bronco, Sprinter, Thule, Yakima, Roofnest, iKamper, Yeti Cooler, Goal Zero, Dometic strongly positive. Tesla Model Y, Telluride, Palisade near zero. F-150, Costco Tires, Discount Tire near zero. Airstream/Winnebago mildly positive.
Story if it lands: "Subaru and Rivian are viable title-sponsor conversations; Thule/Yakima are viable expo sponsors."
Drop if: vehicle models resolve but rooftop/camping gear does not; then trim to a vehicles-only chart. If Subaru is NOT positive, question the pole before publishing anything.
Merge with: none.
Observed: ___

## 14. life_stage_household — Life-Stage & Household Signals

Expected: Empty nest, college tours, high school graduation, anniversary trip, girls trip, multigenerational trip, Chase Sapphire, Amex Platinum, Southwest Companion Pass, REI Mastercard, Costco Membership, dog friendly trails, Rover positive. Baby registry, daycare, babymoon, bachelor party negative or zero. Mortgage/refinance near zero.
Story if it lands: "Household is 35-55, no infants, travels as a couple or friend group, premium travel card in wallet."
Drop if: spread < 0.10; life-stage phrases are broadly searched and this is the most likely category to be flat. If flat, drop the chart but keep the persona language as qualitative.
Merge with: none; this is persona support, not a standalone insight if weak.
Observed: ___

---

## Geo pass (not a category, but audited the same way)

Expected: UT, CO, ID, WY, MT top the per-capita state list; CA, WA, OR, AZ, NV, TX, MN next. DMA level: Salt Lake City, Denver, Boise, Boulder (in Denver DMA), Bozeman, Missoula, Las Vegas, Phoenix, Seattle, Portland, Minneapolis. Deep South and Northeast lower except Boston and DC.
Drop if: raw volume, not per-capita, is what came back; re-normalize before charting.
Watch for: Iceland or any non-U.S. geo appearing as a source; suppress.
Observed: ___

## Expected final shape

Planned 14 categories. Expected to publish 10-11 standalone charts: predicted drops or merges are race_series (thin volume), life_stage (flat), causes (merge into parks), airlines (merge into travel). If more than 4 categories fail, the pole is under-specified; revisit seeds before rebuilding charts.

## Change log

| Date | Change | Reason |
|---|---|---|
| 2026-09-05 | Template created, pre-engine | Planning pass |
