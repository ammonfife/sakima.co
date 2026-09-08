"""Chart specifications for the 34-slide 'Heimdall Nov 2023' deck + PersonasCHD.pdf.

Every entry names (a) the ROW SOURCE exactly as the 2023 workbook filtered it (a Tableau group name
from defs/nov2023_groups.json, or a regex over the corpus), (b) the axes as catalog audience names,
(c) LANDMARKS — a handful of dots read off the original slide with their relative placement, used
as a qualitative acceptance test ("does the recreated chart tell the same story?"), and (d) notes
on what changed between the 2023 corpus and today's engine.

Axis vocabulary:
  PS  = Political Spectrum (2023)           HOP = Hopscotch SMB Banking Persona (2023)
  INC = Income (2023)                        AVG = Average Person (2023)
  UBQ = derived: sqrt(volume / avg_person)   SC  = derived: (segment*.22 - avg_person*.75)*2
  UT  = derived: Utah z-score from the state fingerprint (fps_z.f32, geo_order index of 'Utah')
"""

PS, HOP, INC, AVG = ("Political Spectrum (2023)", "Hopscotch SMB Banking Persona (2023)",
                     "Income (2023)", "Average Person (2023)")

# landmarks: list of (term, expectation) with expectation in {"x+","x-","y+","y-","x+y+","x-y-","x+y-","x-y+"}
# meaning: this dot sat in that half of the ORIGINAL chart (relative to the chart's median).
CHARTS = [
 dict(id="02_social_media_sites_zoom", slide=2, title="Social Media Sites (2)", x=PS, y=HOP,
      rows={"group": "[_social media sites]"}, landmarks=[("pinterest.com","x+y+"),("snapchat.com","x+y+"),("tiktok.com","x+y+"),
      ("wechat.com","x-y-"),("linkedin.com","x-y-"),("instagram.com","x-"),("yelp.com","y+")],
      note="Zoomed copy of slide 5; same 40 sites."),
 dict(id="03_business", slide=3, title="Business", x=PS, y=HOP, rows={"group": "[_INC 5000 Companies (copy)]"},
      landmarks=[("SleepSafe Drivers","x+y+"),("Vanguard","x-"),("Cody","x-y-")],
      note="INC 5000 company names. Original: ~19k dots, strong positive x/y correlation (business-loan seekers lean right)."),
 dict(id="04_websites", slide=4, title="Websites", x=PS, y=HOP, rows={"regex": r"\.(com|net|org|gov|io|co|edu|mil|tv|us)$", "min_volume": 200000, "top": 400},
      landmarks=[("indeed.com","x+y+"),("usajobs.gov","x+y+"),("mycase.com","x-y-"),("bbc.com","x-y-"),("dell.com","y+"),("target.com","y+"),("npr.org","x-")],
      note="2023 filter was a TLD suffix over the whole corpus; recreated as TLD regex over Matrix rows, top-N by Google volume."),
 dict(id="05_social_media_sites", slide=5, title="Social Media Sites", x=PS, y=HOP, rows={"group": "[_social media sites]"},
      landmarks=[("pinterest.com","x+y+"),("snapchat.com","x+y+"),("linkedin.com","x-y-"),("wechat.com","y-"),("whatsapp.com","y-"),("meetup.com","x-")]),
 dict(id="06_google_ads_placements", slide=6, title="Google Ads Placements", x=PS, y=HOP, rows={"group": "[_Google Ads Placements]", "sample": 60000},
      landmarks=[("netstate.com","y+"),("copart.com","x+"),("google.co.uk","y-"),("linguee","x-")],
      note="126k Google Display placements; 40% grounded today (sampled 1,500). Original is a dense positively-correlated cloud."),
 dict(id="07_gads_intent_audiences", slide=7, title="Google Ads Intent Audiences", x=PS, y=HOP, rows={"gads": "user_interest"},
      landmarks=[("Toys & Games","x+y+"),("Refrigerators","y+"),("Power Adapters & Chargers","y+"),("Hockey Equipment","y-"),("Trips to Cuba","y-"),("Trips to Lisbon","x-")],
      note="Rows = Google in-market/affinity audiences (gads:user_interest:*), each placed at the weighted mean of its member keywords' scores — exactly how the 2023 workbook placed them (avg over the segment's rows). Members from the engine's published formulas; size = Σ member volume."),
 dict(id="08_gads_intent_topics", slide=8, title="Google Ads Intent Topics", x=PS, y=HOP, rows={"gads": "topic_constant"},
      landmarks=[("Handbags & Purses","x+y+"),("Virgin Islands","y+"),("Web Series","y-"),("Open Source","x-y-"),("Bangalore","x-y-")],
      note="Rows = Google topics (gads:topic_constant:*), each at the weighted mean of its member keywords' fingerprint-plane scores; size = Σ member volume."),
 dict(id="09_websites4_legal_saas", slide=9, title="Websites (4) — legal software keywords", x=PS, y=HOP,
      rows={"regex": r"(law|legal|attorney|lawyer|court|paralegal|immigration)\b.*\b(software|billing|management|crm|calendar|tracking)|\b(software|billing|management)\b.*\b(law|legal|attorney|lawyer|court)|clio|mycase|practicepanther|lawpay|smokeball|filevine", "top": 400},
      landmarks=[("Legal Billing Software?","y+"),("Tax Research Software","y+"),("Clio Software For Attorneys","y-")],
      note="Original rows were ~60 legal-software phrases (Title Case ad headlines from the Clio work — 0.4% of those literal strings are search terms). Recreated from every legal-software search phrase in today's corpus (regex over the 944k fingerprint keywords, top 400 by volume)."),
 dict(id="10_first_names", slide=10, title="First Names", x=PS, y=HOP, rows={"group": "[_First Names]"},
      landmarks=[], note="3,450 first names; original showed an orange (low-income-colored) cloud with a positive slope and no labels legible."),
 dict(id="11_movies", slide=11, title="Movies", x=PS, y=HOP, rows={"group": "[IMDB Top Movies List]"},
      landmarks=[("Pretty Woman","x-y-"),("Pretty Woman (1990)","x-y-")]),
 dict(id="12_law_landscape", slide=12, title="Law Landscape", x=PS, y=HOP, rows={"group": "[_Law Landscape]"},
      landmarks=[("law.justia.com","x+y+"),("casetext.com","x+y+"),("findlaw.com","x+"),("Ogletree, Deakins, Nash, Smoak & Stewart","y+"),
                 ("Fragomen","x-y-"),("Wilkie Farr & Gallagher","x-y-"),("Cravath, Swaine & Moore","x-y-"),("Mayer Brown","x-y-")],
      note="Big-law firm names sit left/low (blue-city professionals); legal self-help sites sit right/high."),
 dict(id="13_actors", slide=13, title="Actors", x=PS, y=HOP, rows={"group": "[_Actors]"},
      landmarks=[("Sean Hannity","x+y+"),("Quincy Fouse","x+y+"),("Taya Diggs","y+"),("Ryan Gosling","x-"),("Michael Pitt","x-y-"),("Arianna Huffington","x-y-"),("Hasan Minhaj","x-y-")]),
 dict(id="14_banks", slide=14, title="Banks and Financial Institutions", x=PS, y=HOP, rows={"groups": ["[Keyword Set 3]"], "regex_extra": r"bank", "min_volume_extra": 50000},
      landmarks=[("JPMorgan Chase Bank","x+y+"),("chime.com","x+y+"),("go2bank.com","x+y+"),("Deutsche Bank","x-y-"),("HSBC","x-y-"),("Goldman Sachs","x-y-"),("Barclays","x-"),("Wells Fargo","x+")]),
 dict(id="15_family_status", slide=15, title="Family Status", x=PS, y=HOP, rows={"group": "[_Gendered phrases]"},
      landmarks=[("babyboy clothes","x+y+"),("husband snores","x-y-")], note="'_Gendered phrases' group (husband/wife/son/daughter phrasing)."),
 dict(id="16_paid_keywords", slide=16, title="Paid Keywords (Clio)", x=PS, y=HOP, rows={"group": "[Set 12]"},
      landmarks=[("legal document preparation software","y+"),("law practice marketing","y-")],
      note="Set 12 '_AI Filtered' = Clio paid-search terms; original x ran -25..80%."),
 dict(id="17_phone_type", slide=17, title="Phone Type", x=INC, y=HOP, rows={"terms": ["Development", "Other", "iOS", "Android"]}, x2=PS, min_scored=3,
      landmarks=[("Android","y-"),("Other","y+")], note="Four device classes; left panel X=Income, right panel X=Political Spectrum."),
 dict(id="18_sports", slide=18, title="Sports Related", x=PS, y=HOP, rows={"group": "[_Sports]", "top": 400},
      landmarks=[("NFL Football","x+y+"),("NBA Basketball","x+y+"),("Los Angeles Lakers","y+"),("Dallas Cowboys","x+"),("Premier League","x-y-"),("MLB","x-y-"),("NHL Hockey","x-y-"),("NBA","x-y-")],
      note="Top-400 by volume of the 15.5k-term _Sports group (2023 chart showed ~150 leagues/teams)."),
 dict(id="19_technology_providers", slide=19, title="Technology Providers", x=PS, y=HOP, rows={"group": "[_social media sites (copy)]"},
      landmarks=[("directv.com","x+y+"),("yahoo.com","x+y+"),("att.com","x+y+"),("verizon.com","x+"),("google.com","y+"),("hotmail.com","x-y-"),("gmail.com","x-y-"),("finance.yahoo.com","x-y-"),("apple.com","x-")],
      note="Legacy ISPs/webmail (aol, att, directv) right/high; gmail/hotmail left/low."),
 dict(id="20_social_media_handles", slide=20, title="Social Media Handles", x=PS, y=HOP, rows={"group": "[Influencer List (copy)]", "sample": 40000},
      landmarks=[("@DIRECTV","x+y+"),("@Pinterest","x+y+"),("@LivDenman","x-y+"),("@NBA","x-y-"),("@Fitbit","x-y-"),("@CommunityGaming","x-y-")],
      note="52k handles, ~23% grounded today. Original: dense orange→green cloud, strong positive slope."),
 dict(id="21_news_and_politics", slide=21, title="News and Politics", x=PS, y=HOP, rows={"group": "[_News outlets]"},
      landmarks=[("foxnews.com","x+y+"),("washingtontimes.com","x+y+"),("espn.com","y+"),("Sean Hannity","x+y+"),("nytimes.com","x-y-"),("BBC News","x-y-"),("The Nation","x-"),("The New Republic","x-"),("theonion.com","x-")]),
 dict(id="22_news_and_politics_2", slide=22, title="News and Politics (2)", x=PS, y="SC", rows={"group": "[_News outlets]"},
      landmarks=[("foxnews.com","x+y+"),("Breitbart News","x+y+"),("nytimes.com","x-y-"),("FiveThirtyEight","x-y-")],
      note="Y = Comparison Segment set to Political Spectrum → the original is a diagonal; recreated Y = Segment Contrast of PS."),
 dict(id="23_fake_news", slide=23, title="Fake News", x=PS, y=HOP, rows={"group": "[_News outlets (copy)]"},
      landmarks=[("The Gateway Pundit","x+y+"),("InfoWars","x+"),("Zero Hedge","y+"),("Occupy Democrats","x-y-"),("Liberty Writers News","x-"),("The Onion","x-")]),
 dict(id="24_poi", slide=24, title="Points of Interest", x="UBQ", y=HOP, rows={"poi": True},
      landmarks=[("McDonald's","x+"),("Walmart","x+"),("Starbucks","x+")], note="POI universe via /api/explore sources=poi. X = Ubiquity."),
 dict(id="25_poi_3_zoom", slide=25, title="Points of Interest (3)", x="SC", y=HOP, rows={"poi": True}, landmarks=[], note="Zoom of POI(2) region y 70-83%."),
 dict(id="26_poi_4_utah", slide=26, title="Points of Interest (4) — Utah", x="UT", y=HOP, rows={"poi": True, "utah": True},
      landmarks=[("Deseret Book","x+"),("Maverik","x+"),("Harmons","x+")], note="X = Utah share (VOLUME Utah) → Utah z-score from the state fingerprint."),
 dict(id="27_poi_2", slide=27, title="Points of Interest (2)", x="UBQ", y="SC", rows={"poi": True}, landmarks=[("Wal-Mart Auto Center","y+"),("Nordstrom","y-")]),
 dict(id="28_political_spectrum_income", slide=28, title="Political Spectrum + Income", x=PS, y=HOP, x2=INC, rows={"corpus_sample": 150000},
      landmarks=[], note="Whole-corpus cloud, two panels (X=PS colored by PS; X=Income colored by Income)."),
 dict(id="29_auto", slide=29, title="Auto", x=PS, y=HOP, rows={"group": "[_discount (copy)]"},
      landmarks=[("landroverusa.com","x+y+"),("kbb.com","x+y+"),("cars.com","y+"),("dodge.com","x+"),("tesla.com","x-"),("bmwusa.com","x-y-"),("electrek.co","x-y-")]),
 dict(id="30_youtube_channels", slide=30, title="Youtube Channels", x=PS, y=HOP, rows={"group": "[Youtube Channels]"},
      landmarks=[("Tannerites","x+y+"),("Cartoon Network","x+"),("Kids Songs","y-"),("SmartFamily","x-y-")]),
 dict(id="31_subreddits", slide=31, title="SubReddits", x=PS, y=HOP, rows={"regex": r"^/?r/", "top": 3000},
      landmarks=[("/r/Conservative","x+"),("/r/politics","x-"),("/r/atheism","x-")], note="Slide 31 rendered EMPTY in the 2023 deck (filter mishap); recreated from every r/ row in the Matrix."),
 dict(id="32_different_tab_customers", slide=32, title="Different Tab Customers", y=HOP, color=INC, rows={"corpus_sample": 40000},
      panels=["Small Business Owner (2023)", "Tab Flow Potential Customer (2023)", "Tab ABL Customer Persona (2023)", "Tab Existing Business Customers (2023)", "Tabbank.com (2023)", AVG],
      landmarks=[], note="Six small multiples: X = each customer segment, Y = _Segment (Hopscotch), color = Income. The last panel (Average Person) slopes NEGATIVE in the original."),
 dict(id="33_consumer_finance_landscape", slide=33, title="Consumer Finance Landscape (2)", rows={"groups": ["[_Tab Broker Landscape (copy 4)]", "[_Tab Flow Landscape]"]},
      matrix=["SC", "Small Business Owner (2023)", HOP, PS], landmarks=[("dwolla.com","y-"),("viobank.com","y+"),("citibank.ae","y-")],
      note="Scatter matrix over fintech/bank domains (viobank, dwolla, exodus, icard, get.com)."),
 dict(id="35_chd_personas", slide="PersonasCHD.pdf", title="Personas — Contrast Rising Generation vs Risk of Leaving", chd=True,
      x=("CHD Rising Generation", "CHD General Membership"), y=("CHD Losing Faith - General", "CHD Disaffected with LDS Church"),
      landmarks=[("CHD Persona: Lots of Small Questions","y+"),("CHD Persona: Mormon Corridor","y+"),("CHD Persona: What Does the Manual Say?","y+"),
                 ("CHD Persona: Investigator/Pre-Testimony","y-"),("CHD Persona: Willing to Ask Tough Questions","x+y-"),("CHD Persona: That's News to Me","x+y-"),
                 ("CHD Persona: Deseret Book Platinum","x-y-"),("CHD Persona: Mormon Fan Club","x-")],
      note="12 persona keyword clusters. X = corr(Rising Generation) − corr(General Membership); Y = mean(Losing Faith, Disaffected). Dot = cluster mean, size = Σ volume. "
           "Original y range 25-60% ('Risk of Leaving' correlation), x −25..30%."),
]
