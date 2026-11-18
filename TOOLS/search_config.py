"""WHAT JOBS TO LOOK FOR. The one file that decides what scan.py, career_ops_feed.py and the board sweep keep.

The setup (START_HERE.md) rewrites this file from your answers. Change it any time by telling Claude, for example
"also search for project coordinator jobs" or "stop showing me call centre jobs". Claude edits this file, then runs
`python TOOLS/scan.py --test` to check it still loads.

Everything below is an EXAMPLE until the setup replaces it (example person: entry-level analyst work in Toronto or
remote in Canada, plus nearby retail and front-desk jobs).
"""
import re

# ---- Tracks -------------------------------------------------------------------------------------------------
# A track is one kind of job you want, with its own searches, filters, daily cap and follow-up timing
# (caps and follow-up days live in config/kit.json). Name them anything. The first one comes first in every list.
TRACKS = ["main", "nearby"]

# ---- LinkedIn guest search (no login, gives post age and the exact applicant count) ---------------------------
# (track, keywords, LinkedIn filters). f_WT: 1 on-site, 2 remote, 3 hybrid. f_E: 1 internship, 2 entry, 3 associate,
# 4 mid-senior. distance is in miles (LinkedIn's smallest is 5). Each search costs about 4 page loads, keep it under ~40.
MAIN_KEYWORDS = ["data analyst", "business analyst", "operations analyst", "reporting analyst", "junior analyst"]
NEARBY_KEYWORDS = ["cashier", "sales associate", "customer service representative", "receptionist", "front desk", "store associate"]
HOME = "Toronto, Ontario, Canada"   # LinkedIn place name for on-site searches
NEARBY_PLACE = "North York, Ontario, Canada"  # the neighbourhood the nearby track searches around
SEARCHES = (
    [("main", k, {"location": "Canada", "f_WT": "2", "f_E": "2,3"}) for k in MAIN_KEYWORDS]
    + [("main", k, {"location": HOME, "distance": "25", "f_WT": "1,3", "f_E": "2,3"}) for k in MAIN_KEYWORDS]
    + [("nearby", k, {"location": NEARBY_PLACE, "distance": "5"}) for k in NEARBY_KEYWORDS]
)
# How far back each track looks, in hours, at least (rare postings look back longer; seen.json stops repeats).
LOOKBACK_HOURS = {"main": 72, "nearby": 72}

# ---- Title filters ------------------------------------------------------------------------------------------
# A title must match its track's TITLE_OK and must not match NOT_FIT or BAD_TITLE.
TITLE_OK = {
    "main": re.compile(r"(analyst|analytics|reporting|business intelligence|\bbi\b|operations)", re.I),
    "nearby": re.compile(r"(cashier|clerk|associate|receptionist|front desk|customer service|retail|stock|greeter)", re.I),
}
NOT_FIT = {
    "main": re.compile(r"(\bsales\b|account (executive|manager)|marketing|\bintern\b|internship|co-op|bilingual|french|security|soc analyst)", re.I),
    "nearby": re.compile(r"(warehouse|driver|forklift|construction|cleaner|picker|packer|bilingual|french|\bintern\b|supervisor|commission only)", re.I),
}
BAD_TITLE = re.compile(r"\b(senior|sr\.?|staff|principal|director|manager|head of|vp|lead|architect|ii|iii)\b", re.I)
# Sort order inside a track: titles matching an earlier pattern come first.
TIER = [re.compile(r"data analyst|business analyst", re.I), re.compile(r"analyst", re.I)]

# ---- Place ----------------------------------------------------------------------------------------------------
HOME_AREA = re.compile(r"(toronto|scarborough|markham|pickering|ajax|mississauga|north york|vaughan|richmond hill|brampton|etobicoke|\bgta\b)", re.I)
REMOTE_COUNTRIES = re.compile(r"(canada|north america)", re.I)  # remote is fine when it is open to these
RELOCATE = None  # e.g. re.compile(r"(canada|ontario)", re.I) to also accept on-site jobs anywhere in Canada
COUNTRY_ONLY = re.compile(r"^\s*(canada|united states( of america)?|usa?|north america)\s*$", re.I)
NON_NA = re.compile(r"(\buk\b|united kingdom|london, (uk|england)|europe|emea|india|singapore|australia|apac|latam|brazil|mexico|ireland|germany|france|spain|"
                    r"netherlands|poland|israel|philippines|pakistan|nigeria|egypt|dubai|uae|china|japan)", re.I)


def place_ok(loc, title=""):
    """On-site or hybrid in HOME_AREA, remote open to REMOTE_COUNTRIES, or anywhere RELOCATE allows.
    A bare country ("Canada") passes: the run re-reads the posting before applying."""
    loc = loc or ""
    if HOME_AREA.search(loc) or COUNTRY_ONLY.search(loc):
        return True
    if RELOCATE and RELOCATE.search(loc):
        return True
    if not re.search(r"remote", loc, re.I):
        return False
    if NON_NA.search(loc):
        return bool(REMOTE_COUNTRIES.search(loc))
    return True


# ---- Company job boards read directly (no login, public JSON) --------------------------------------------------
# The board name is the part after boards.greenhouse.io/ , jobs.lever.co/ or jobs.ashbyhq.com/ . Jobs found here
# go to FEED_TRACK. Pick employers that hire for your main track in your area.
FEED_TRACK = "main"
GH = "wealthsimple hootsuite thinkific achievers ecobee geotab koho dialogue freshbooks jobber benevity d2l".split()
LV = "kinaxis".split()
ASHBY = []
YC = False  # True = also check freshly funded YC startups once a day (mostly US tech jobs)

# ---- Canada's Job Bank (public feed, good for nearby jobs) ----------------------------------------------------
# (track, keyword). The place word goes into the search text, because Job Bank's own location filter does not work.
JOBBANK = [("nearby", k) for k in ("cashier", "sales associate", "customer service", "receptionist", "clerk")]
JOBBANK_PLACE_WORD = "north york"
JOBBANK_PLACE = re.compile(r"(north york|toronto)", re.I)  # keep a Job Bank hit only when its location matches

# ---- Skips --------------------------------------------------------------------------------------------------
MAX_YEARS = 5              # skip postings that ask for more years of experience than this
MAX_APPLICANTS = 60        # skip LinkedIn postings with this many applicants or more
SKIP_FRENCH_REQUIRED = True
HEAVY_LIFTING_SKIP = {"nearby"}  # tracks where "lift 40 lbs or more" means skip
