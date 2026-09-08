#!/usr/bin/env python3
"""Build defs/audience_catalog.json — every audience/segment/trait/persona the 2023 demo slides and
PersonasCHD.pdf need, in Heimdall 3.0 seed grammar (matrix.parse_term: '-term', 'term*w').

Two provenance classes, kept explicit on every entry:
  tableau  — translated MECHANICALLY from the Nov-2023 workbook formula (tableau_formula_to_seeds.py);
             anchors + weights + signs are the 2023 definition, not a re-interpretation.
  authored — the 2017-18 CHD workbook that carried the persona clusters is not on disk (only the
             social-topics workbook socialCHD.twb is), so the CHD segments/traits/personas are
             re-authored from the methodology decks: the 9 CSC dimensions (CHD Data Science
             PRESENTATION_012518 slide 43), the Risk Analysis inputs (slide 33), the Rising Generation /
             General Membership contrast (slides 3-5, 10-11), and the 12 persona names (slide 44).
             Each carries `basis` quoting the slide text it was built from.

Substitutions (called out, not hidden):
  * _Average Person used ten single-character anchor columns [A],[B],[C],[D],[E],[F],[I],[L],[M],[3]
    (people who search "a" or "3" = everyone). Those single characters ARE grounded in the live
    corpus, so the definition is kept verbatim — no substitution needed.
  * _Utahish (Utah share of volume) and _Ubiquity (sqrt(volume/average-person)) are DERIVED axes, not
    poles; they are computed client-side in recreate_charts.py from volume + the Average Person score.
  * _*Segment Contrast = segment*.22 − average_person*.75 : derived client-side.
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f"{HERE}/defs/audiences_from_tableau.json"))["Heimdall Nov 2023_Hopscotch.twb"]

def tab(name, tableau_key, role, note=""):
    d = T[tableau_key]
    seeds = [s["seed"] for s in d["seeds"] if "seed" in s and not s["term"].startswith("Calculation_")]
    return {"name": name, "provenance": "tableau", "tableau_name": tableau_key, "role": role,
            "seeds": seeds, "n_seeds": len(seeds), "constant": d["constant"],
            "dropped_refs": [s["term"] for s in d["seeds"] if s.get("unresolved_ref") or s["term"].startswith("Calculation_")],
            "note": note, "formula": d["formula"]}

def authored(name, role, seeds, basis, register, note=""):
    return {"name": name, "provenance": "authored", "role": role, "seeds": seeds, "n_seeds": len(seeds),
            "basis": basis, "register": register, "note": note}

cat = []
# ── 2023 demo slides: axes ────────────────────────────────────────────────────────────────
cat.append(tab("Political Spectrum (2023)", "_Political Spectrum", "axis:x",
               "X axis of 30 of the 34 slides. 8 left anchors (−) vs 8 right anchors (+); Mother Jones / Newsmax weighted 2×."))
cat.append(tab("Hopscotch SMB Banking Persona (2023)", "*Hopscotch", "axis:y",
               "Y axis ('*Hopscotch') of most slides. Persona for gohopscotch.com: small-business owners seeking loans / AR financing / "
               "online business banking; accountants, consumer-loan and SBA-disaster seekers subtracted."))
cat.append(tab("Income (2023)", "_Income", "axis",
               "Y of 'Phone Type', X2 of 'Political Spectrum + Income', color of 'Different Tab Customers'."))
cat.append(tab("Average Person (2023)", "_Average Person (full spectrum)", "baseline",
               "Ten single-character anchors [A]..[3]; correlation to 'everyone'. Feeds Ubiquity and Segment Contrast."))
# the Tableau translator dropped the [A]..[3] refs (they are column refs, not zn(avg()) calls) — restore verbatim
cat[-1]["seeds"] = ["a", "b", "c", "d", "e", "f", "i", "l", "m", "3"]; cat[-1]["n_seeds"] = 10; cat[-1]["dropped_refs"] = []
cat.append(tab("Small Business Owner (2023)", "*Small Business Owner", "segment", "Panel 1 of 'Different Tab Customers'."))
cat.append(tab("Tab Flow Potential Customer (2023)", "_Tab Flow Potential Customer", "segment", "Panel 2."))
cat.append(tab("Tab ABL Customer Persona (2023)", "*Tab ABL Customer Persona", "segment", "Panel 3."))
cat.append(tab("Tab Existing Business Customers (2023)", "_Tab Existing Business Customers", "segment", "Panel 4."))
cat.append(tab("Tabbank.com (2023)", "_Tab Customer (copy)", "segment", "Panel 5 ('Tabbank.Com')."))
cat.append(tab("Attorney/Law Persona (2023)", "*Attorney/Law Persona", "segment", "Law Landscape / Websites (4) / Paid Keywords slides (Clio)."))
cat.append(tab("Mormon Culture (2023)", "_Mormon Culture", "segment", "utah jazz + Provo + templesquare + Church."))
cat.append(tab("LDS Affinity (2023)", "_LDS", "segment", "lds.org/templesquare/Church; the '−Utahish' term (Utah volume share) is derived, dropped here."))
cat.append(tab("Female Contrast (2023)", "_Gender", "trait", "Female (+) vs male (−) indicators."))

# ── CHD 2017-18: segments, risk axis, traits, personas (authored from the methodology decks) ──
LDS_CORE = ["the church of jesus christ of latter-day saints", "lds.org", "churchofjesuschrist.org", "general conference",
            "book of mormon", "relief society", "temple recommend", "ward", "deseret book", "ksl.com", "lds temples"]
cat.append(authored("CHD General Membership", "segment",
    LDS_CORE + ["ministering", "home teaching", "family history", "familysearch", "lds primary", "elders quorum",
                "ensign magazine", "lds hymns", "come follow me", "stake conference", "temple square", "byutv"],
    "Slides 3-5: 'General LDS Membership — issues prominent among all Church members based on private web interest'.",
    "affinity", "Institutional + habitual membership vocabulary; adult program words (Relief Society, ministering, family history)."))
cat.append(authored("CHD Rising Generation", "segment",
    ["byu", "byu-idaho", "byu idaho", "utah valley university", "lds missionary", "preach my gospel", "mission call",
     "missionary training center", "mtc provo", "ysa ward", "young single adult", "lds institute", "lds seminary",
     "fsy conference", "efy", "mutual dating app", "lds dating", "byu football", "byu basketball", "byu housing",
     "temple marriage", "lds wedding", "returned missionary", "rm", "young women camp", "duty to god", "personal progress"],
    "Slides 3-5: 'Rising Generation — issues prominent among 15-35 (approx.) year old Church members'.",
    "affinity", "Life-stage vocabulary: seminary→mission→BYU→YSA→temple marriage. Contrast vs General Membership = the X axis of PersonasCHD.pdf."))
cat.append(authored("CHD Losing Faith - General", "axis:y",
    ["don't believe in god anymore", "i have doubts about god", "i don't believe in god", "losing my faith", "crisis of faith",
     "how to leave religion", "questioning my faith", "agnostic", "r/exchristian", "why i left the church", "deconstructing faith"],
    "Slide 33 Risk Analysis — sample inputs: 'Don't believe in God anymore', 'Have doubts', 'I don't believe'.", "topic"))
cat.append(authored("CHD Disaffected with LDS Church", "axis:y",
    ["leaving the lds church", "r/exmormon", "exmormon", "what mormons won't tell you", "crisis of faith lds", "ces letter",
     "letter for my wife", "how to resign from the lds church", "quitmormon", "mormon stories podcast", "john dehlin",
     "post mormon", "faith crisis lds", "lds church lies", "mormon church truth", "leaving mormonism", "exmo"],
    "Slide 33 Risk Analysis — sample inputs: 'Leaving the LDS Church', 'r/exmormon', 'What Mormons won't tell you', 'Crisis of faith LDS'.", "topic"))
cat.append({"name": "CHD Risk of Leaving", "provenance": "authored", "role": "axis:y", "composite_of": ["CHD Losing Faith - General", "CHD Disaffected with LDS Church"],
            "seeds": None, "basis": "Slide 33: 'Correlated each phrase to attributes Losing Faith - General and Disaffected with LDS Church'. Risk = mean of the two.",
            "note": "Computed client-side as the mean of the two attribute scores (both are registered poles)."})

# 9 CSC dimensions (traits) — slide 43 text quoted in `basis`
TRAITS = {
 "CHD Trait: Belief in Institution": (["only true and living church", "restoration of the gospel", "the restored church", "joseph smith first vision",
      "priesthood restoration", "living prophet", "follow the prophet", "russell m nelson", "sustain the prophet"],
      "Shows an interest and belief in the Restoration of the Church. Views the Church as the 'Only True and Living Church.'"),
 "CHD Trait: Church Attendance": (["sacrament meeting", "lds church near me", "ward building", "lds meetinghouse locator", "church calling", "sacrament meeting talk",
      "fast and testimony meeting", "stake conference", "sunday school lesson lds"],
      "Actively seeks to attend and participate in church meetings and callings."),
 "CHD Trait: Core Doctrine": (["atonement of jesus christ", "faith repentance baptism", "baptismal covenants", "plan of salvation", "gift of the holy ghost",
      "restoration of the priesthood", "enduring to the end", "grace lds", "articles of faith"],
      "Believes in Jesus Christ and actively tries to apply the Atonement through faith, repentance, honoring baptismal covenants. Believes in the restoration of the Priesthood."),
 "CHD Trait: Cultural Doctrine": (["mommy blog", "time out for women", "get out of debt dave ramsey", "cub scouts", "food storage", "72 hour kit", "family history",
      "familysearch", "canning recipes", "freeze dried food storage"],
      "Has a mommy blog, attends Time-Out for Women, wants to get out of debt, is an active scouter, has food storage, does family history, etc."),
 "CHD Trait: Diligence": (["ministering", "home teaching", "visiting teaching", "general conference talks", "temple attendance", "book of mormon reading chart",
      "lds temple schedule", "scripture study plan", "conference talk summaries"],
      "Does Home/Visiting Teaching, watches General Conference, serves in various callings, attends the Temple, and studies the BOM."),
 "CHD Trait: Conformity": (["avoid the appearance of evil", "modest dress lds", "for the strength of youth", "word of wisdom", "obedience is the first law of heaven",
      "missionary haircut", "modest swimsuits", "modest prom dresses", "garments lds"],
      "Seeks to be, or at least appear to be, compliant. 'Avoids the very appearance of evil.' Dresses like a missionary. Emphasizes the importance of obedience."),
 "CHD Trait: LDS Culture": (["studio c", "byutv", "is he mormon", "famous mormons", "mormon celebrities", "molly mormon", "zoobie", "lds memes", "the district lds",
      "jello salad", "funeral potatoes", "dirty soda", "swig soda"],
      "Watches Studio C on BYUtv, wants to know if ____ is a Mormon, likely to like person/company/celebrity primarily for LDS connection. 'Molly Mormon' or 'Zoobie.'"),
 "CHD Trait: Progressive": (["bloggernacle", "by common consent", "feminist mormon housewives", "ordain women", "lgbt mormon", "affirmation lgbtq mormons",
      "mormons building bridges", "climate change lds", "immigration lds church statement", "public transportation utah", "sunstone"],
      "Has 'Progressive' views regarding the environment, immigration, public transportation, feminism, and/or LGBT issues. Reads or participates in the 'Bloggernacle.'"),
 "CHD Trait: Tough Questions": (["mountain meadows massacre", "book of abraham", "blacks and the priesthood", "joseph smith polygamy", "kate kelly excommunication",
      "john dehlin excommunication", "general authority salary", "prop 8 lds church", "seer stone", "fanny alger", "mormon racism"],
      "Is aware of, has researched, or has asked questions about racism, polygamy, Mountain Meadows, Book of Abraham, Ordain Women, high profile excommunications, General Authority compensation, Prop 8, etc."),
}
for n, (seeds, basis) in TRAITS.items():
    cat.append(authored(n, "trait", seeds, "PRESENTATION_012518 slide 43 (9 Dimensions from CSC Big Data Study): " + basis, "affinity/topic"))

# 12 persona clusters (slide 44 names). Each persona is a KEYWORD CLUSTER: its dot is the mean of its
# members' scores and the sum of their volume — exactly how the Tableau chart aggregated.
PERSONAS = {
 "Active-ly Conflicted": (["gospel topics essays", "lds essays", "stay lds", "faith crisis lds", "i still believe lds doubts", "planted patrick mason",
     "faith is not blind", "lds doubts", "how to keep faith lds", "ces letter response"],
     "Active markers + doubt vocabulary: members inside the tent wrestling with the essays. Decks: 'Members who have markers of being active are at much more risk when presented with new/conflicting/troubling information.'"),
 "Willing to Ask Tough Questions": (["mountain meadows massacre", "book of abraham papyri", "blacks and the priesthood ban", "joseph smith wives", "kinderhook plates",
     "book of mormon dna", "book of mormon anachronisms", "adam god theory", "mark hofmann"],
     "The Tough Questions dimension asked directly and by name."),
 "Investigator/Pre-Testimony": (["what do mormons believe", "mormon church near me", "meet with missionaries", "free book of mormon", "mormon.org", "comeuntochrist.org",
     "how to become a mormon", "lds baptism requirements", "what is the book of mormon about", "mormon beliefs vs christian"],
     "Outsider register; the 'Investigator Flag' filter on the chart keeps this group. socialCHD.twb group 'Investigator/Outsider' (15,347 rows)."),
 "That's News to Me": (["joseph smith had multiple wives", "joseph smith seer stone in a hat", "lds church finances 100 billion", "ensign peak advisors",
     "brigham young adam god", "joseph smith married 14 year old", "did joseph smith use a seer stone", "lds church owns"],
     "Recent disclosures landing on members who had not heard them — the Church Finances/Transparency 'emerging trend' (slide 47)."),
 "Fact Checking": (["fairmormon", "fairlatterdaysaints", "is the ces letter true", "ces letter debunked", "lds apologetics", "book of mormon central",
     "mormon stories debunked", "jeremy runnells", "lds truth claims", "interpreter foundation"],
     "Members verifying claims from both sides — apologetics + critics side by side."),
 "Lots of Small Questions": (["why do mormons not drink coffee", "can mormons drink caffeine", "why is tithing 10 percent", "what is a temple recommend",
     "why do mormons wear garments", "can mormons dance", "do mormons celebrate christmas", "why do mormons have big families", "can mormons drink tea",
     "what happens in the temple"],
     "Slide 44 name; the 'Questioning' topic list (why tithing, why coffee, 13 essays)."),
 "Mormon Corridor": (["deseret news", "ksl news", "utah jazz", "byu football", "cafe rio", "swig", "dirty soda", "pioneer day", "utah county",
     "provo utah", "st george utah", "rexburg idaho", "mesa arizona temple"],
     "Regional-cultural cluster (Utah/Idaho/Arizona). '_Mormon Culture' 2023 formula used utah jazz + Provo; deck: 'Mormon Fan Club and Corridor are at a greater risk'."),
 "Mormon Fan Club": (["studio c", "famous mormons", "is he mormon", "lds celebrities", "book of mormon musical", "mormon tabernacle choir", "the piano guys",
     "lindsey stirling mormon", "david archuleta", "mormon youtubers", "byutv shows"],
     "LDS Culture dimension: likes the person/company/celebrity primarily for the LDS connection."),
 "Yeah, I Already Knew That": (["rough stone rolling", "saints volume 1", "joseph smith papers", "sunstone magazine", "dialogue journal mormon thought",
     "mormon history association", "richard bushman", "terryl givens", "no man knows my history", "juvenile instructor blog"],
     "Historically literate members — scholarly register (Bushman, Givens, JSP, Dialogue)."),
 "Confirming not Challenging": (["gospel topics", "come follow me", "conference talks on faith", "scripture citation index", "lds quotes on", "lds.org study helps",
     "gospel library app", "byu speeches", "lds talks on hope", "general conference quotes"],
     "Study to confirm: official study aids and talk lookups."),
 "What Does the Manual Say?": (["gospel principles manual", "handbook 2", "general handbook lds", "primary manual", "relief society lesson", "seminary manual",
     "institute manual", "lds lesson helps", "sunday school manual", "young women lesson", "preach my gospel chapter"],
     "Manual/lesson register: teachers and leaders preparing lessons."),
 "Deseret Book Platinum": (["deseret book", "seagull book", "time out for women", "lds bookstore", "lds art", "temple dress", "ctr ring", "lds gifts",
     "lds jewelry", "missionary gifts", "lds home decor", "greg olsen art"],
     "Retail/consumption of LDS lifestyle goods."),
}
for n, (seeds, basis) in PERSONAS.items():
    cat.append(authored("CHD Persona: " + n, "persona", seeds, "PRESENTATION_012518 slide 44 'Persona Asking These Questions' — " + basis, "mixed (cluster)",
                        "Persona = keyword cluster; chart dot = mean(x), mean(y) over members, size = Σ volume."))

json.dump(cat, open(f"{HERE}/defs/audience_catalog.json", "w"), indent=1, ensure_ascii=False)
print(f"{len(cat)} catalog entries → defs/audience_catalog.json")
for c in cat: print(f"  {c['provenance']:8s} {c['role']:9s} {c['name']:45s} seeds={c.get('n_seeds')}")
