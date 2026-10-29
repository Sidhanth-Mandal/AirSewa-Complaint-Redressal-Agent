"""Reference/master data and default configuration rules (all editable at runtime from the admin UI)."""

CATEGORIES = {
    "flight": "Flight related (delay / cancellation / modification / baggage)",
    "airport": "Airport related (hygiene, charging points, facilities, security)",
    "ground": "On-ground (wheelchair, airport stores, taxi, meet & greet)",
    "govt": "Government department (Customs, Immigration, DGCA ...)",
    "other": "Others",
}

SUBCATEGORIES = {
    "flight": ["delay_cancellation", "refund", "baggage_lost", "baggage_damaged", "baggage_delay", "staff_behaviour",
               "meals", "fare", "modification", "ticketing", "denied_boarding", "other"],
    "airport": ["hygiene", "charging", "facilities", "security", "queue_checkin", "parking_transport", "medical",
                "vip_movement", "accessibility", "other"],
    "ground": ["wheelchair", "taxi", "meet_greet", "stores", "other"],
    "govt": ["customs", "immigration", "dgca", "bcas", "malpractice", "other"],
    "other": ["suggestion", "query", "other"],
}

STATUSES = ["Under Assessment", "Assigned", "In-Progress", "On Hold - Awaiting Passenger Inputs",
            "Provisionally Resolved", "Resolved", "Reopened", "Escalated", "Closed"]
OPEN_STATUSES = ["Under Assessment", "Assigned", "In-Progress", "On Hold - Awaiting Passenger Inputs", "Reopened", "Escalated"]
RESOLVED_STATUSES = ["Provisionally Resolved", "Resolved", "Closed"]

ORGS = [
    # code, name, type, handle, has_crm
    ("AAI", "Airports Authority of India", "aai", "@AAI_Official", False),
    ("MOCA", "Ministry of Civil Aviation", "regulator", "@MoCA_GoI", False),
    ("DGCA", "Directorate General of Civil Aviation", "regulator", "@DGCAIndia", False),
    ("BCAS", "Bureau of Civil Aviation Security", "regulator", "@BCAS_India", False),
    ("CISF", "Central Industrial Security Force (Airport Security)", "regulator", "@CISFHQrs", False),
    ("CUSTOMS", "Customs (Airport Commissionerate)", "regulator", None, False),
    ("IMMIG", "Bureau of Immigration", "regulator", None, False),
    ("DIAL", "Delhi International Airport Ltd (private)", "airport_operator", "@DelhiAirport", False),
    ("MIAL", "Mumbai International Airport Ltd (private)", "airport_operator", "@CSMIA_Official", False),
    ("BIAL", "Bangalore International Airport Ltd (private)", "airport_operator", "@BLRAirport", False),
    ("GHIAL", "GMR Hyderabad International Airport Ltd (private)", "airport_operator", "@RGIAHyderabad", False),
    ("CIAL", "Cochin International Airport Ltd (private)", "airport_operator", "@KochiAirport", False),
    ("6E", "IndiGo", "airline", "@IndiGo6E", True),
    ("AI", "Air India", "airline", "@airindia", True),
    ("QP", "Akasa Air", "airline", "@AkasaAir", True),
    ("SG", "SpiceJet", "airline", "@flyspicejet", False),
    ("IX", "Air India Express", "airline", "@AirIndiaX", False),
    ("S5", "Star Air", "airline", "@StarAirIN", False),
    ("9I", "Alliance Air", "airline", "@allianceair9I", False),
    ("I5", "AIX Connect (Flyingwheels)", "airline", "@flyaixconnect", False),
    ("SATS", "Air India SATS (Ground Handling)", "gsp", None, False),
    ("CELEBI", "Celebi Ground Handling", "gsp", None, False),
    ("BIRD", "Bird Group Ground Services", "gsp", None, False),
    ("MMT", "MakeMyTrip (OTA)", "ota", "@makemytrip", False),
    ("CLEAR", "Cleartrip (OTA)", "ota", "@Cleartrip", False),
    ("PACR", "Passenger Assistance Control Room", "pacr", "@AirSewa_Official", False),
]

# code, name, city, state, operator, major, handle, row, col (row/col = coarse north-south/west-east grid for the map)
AIRPORTS = [
    ("DEL", "Indira Gandhi International", "Delhi", "Delhi", "DIAL", True, "@DelhiAirport", 1, 3),
    ("BOM", "Chhatrapati Shivaji Maharaj Intl", "Mumbai", "Maharashtra", "MIAL", True, "@CSMIA_Official", 4, 1),
    ("BLR", "Kempegowda International", "Bengaluru", "Karnataka", "BIAL", True, "@BLRAirport", 6, 2),
    ("HYD", "Rajiv Gandhi International", "Hyderabad", "Telangana", "GHIAL", True, "@RGIAHyderabad", 5, 3),
    ("MAA", "Chennai International", "Chennai", "Tamil Nadu", "AAI", True, "@aaichnairport", 7, 3),
    ("CCU", "Netaji Subhas Chandra Bose Intl", "Kolkata", "West Bengal", "AAI", True, "@aaikolairport", 3, 5),
    ("AMD", "Sardar Vallabhbhai Patel Intl", "Ahmedabad", "Gujarat", "AAI", True, "@aaiahdairport", 3, 1),
    ("PNQ", "Pune Airport", "Pune", "Maharashtra", "AAI", False, "@aaipuneairport", 4, 2),
    ("GOI", "Manohar International", "Goa", "Goa", "AAI", False, "@aaigoaairport", 5, 1),
    ("COK", "Cochin International", "Kochi", "Kerala", "CIAL", True, "@KochiAirport", 7, 2),
    ("TRV", "Trivandrum International", "Thiruvananthapuram", "Kerala", "AAI", False, "@aaitvmairport", 8, 2),
    ("JAI", "Jaipur International", "Jaipur", "Rajasthan", "AAI", False, "@aaijaipurairport", 2, 2),
    ("LKO", "Chaudhary Charan Singh Intl", "Lucknow", "Uttar Pradesh", "AAI", False, "@aailkoairport", 2, 4),
    ("GAU", "Lokpriya Gopinath Bordoloi Intl", "Guwahati", "Assam", "AAI", False, "@aaiguwahati", 2, 6),
    ("PAT", "Jay Prakash Narayan Airport", "Patna", "Bihar", "AAI", False, "@aaipatnaairport", 3, 4),
    ("IXC", "Chandigarh International", "Chandigarh", "Chandigarh", "AAI", False, "@aaichandigarh", 0, 3),
    ("BBI", "Biju Patnaik International", "Bhubaneswar", "Odisha", "AAI", False, "@aaibbiairport", 4, 5),
    ("IDR", "Devi Ahilya Bai Holkar", "Indore", "Madhya Pradesh", "AAI", False, "@aaiindoreairport", 3, 2),
    ("SXR", "Srinagar International", "Srinagar", "J&K", "AAI", False, "@aaisrinagar", 0, 2),
    ("VNS", "Lal Bahadur Shastri Intl", "Varanasi", "Uttar Pradesh", "AAI", False, "@aaivaranasi", 2, 5),
]

AIRLINE_ALIASES = {
    "6E": ["indigo", "6e", "interglobe"], "AI": ["air india", "airindia", "ai "], "QP": ["akasa", "akasa air"],
    "SG": ["spicejet", "spice jet"], "IX": ["air india express", "airindiaexpress", "airindiax"],
    "S5": ["star air"], "9I": ["alliance air"], "I5": ["aix connect", "airasia india"],
}

# keyword -> category, subcategory, target org type, org code, weight
ALLOCATION_RULES = [
    ("delayed", "flight", "delay_cancellation", "airline", None, 1.0), ("delay", "flight", "delay_cancellation", "airline", None, 1.0),
    ("late", "flight", "delay_cancellation", "airline", None, 0.5), ("cancelled", "flight", "delay_cancellation", "airline", None, 1.5),
    ("cancellation", "flight", "delay_cancellation", "airline", None, 1.5), ("rescheduled", "flight", "modification", "airline", None, 1.0),
    ("diverted", "flight", "delay_cancellation", "airline", None, 1.2), ("fog", "flight", "delay_cancellation", "airline", None, 0.5),
    ("tarmac", "flight", "delay_cancellation", "airline", None, 1.0), ("hours late", "flight", "delay_cancellation", "airline", None, 1.5),
    ("refund", "flight", "refund", "airline", None, 2.0), ("money back", "flight", "refund", "airline", None, 1.5),
    ("not refunded", "flight", "refund", "airline", None, 2.0), ("chargeback", "flight", "refund", "airline", None, 1.0),
    ("baggage lost", "flight", "baggage_lost", "airline", None, 2.5), ("lost baggage", "flight", "baggage_lost", "airline", None, 2.5),
    ("lost luggage", "flight", "baggage_lost", "airline", None, 2.5), ("luggage lost", "flight", "baggage_lost", "airline", None, 2.5),
    ("bag lost", "flight", "baggage_lost", "airline", None, 2.5), ("baggage missing", "flight", "baggage_lost", "airline", None, 2.5),
    ("missing baggage", "flight", "baggage_lost", "airline", None, 2.5), ("missing luggage", "flight", "baggage_lost", "airline", None, 2.5),
    ("baggage not received", "flight", "baggage_lost", "airline", None, 2.5), ("baggage", "flight", "baggage_lost", "airline", None, 1.0),
    ("luggage", "flight", "baggage_lost", "airline", None, 1.0), ("suitcase", "flight", "baggage_lost", "airline", None, 1.0),
    ("damaged baggage", "flight", "baggage_damaged", "airline", None, 2.5), ("damaged bag", "flight", "baggage_damaged", "airline", None, 2.5),
    ("broken suitcase", "flight", "baggage_damaged", "airline", None, 2.5), ("broken wheel", "flight", "baggage_damaged", "airline", None, 2.0),
    ("baggage delay", "flight", "baggage_delay", "airline", None, 2.5), ("belt", "flight", "baggage_delay", "airline", None, 0.6),
    ("rude crew", "flight", "staff_behaviour", "airline", None, 2.0), ("cabin crew", "flight", "staff_behaviour", "airline", None, 1.2),
    ("misbehaved", "flight", "staff_behaviour", "airline", None, 1.5), ("rude staff", "flight", "staff_behaviour", "airline", None, 1.5),
    ("meal", "flight", "meals", "airline", None, 1.5), ("food on flight", "flight", "meals", "airline", None, 2.0),
    ("overpriced fare", "flight", "fare", "airline", None, 1.5), ("fare hike", "flight", "fare", "airline", None, 2.0), ("air fare", "flight", "fare", "airline", None, 1.5),
    ("ticket price", "flight", "fare", "airline", None, 1.0), ("denied boarding", "flight", "denied_boarding", "airline", None, 3.0),
    ("overbooked", "flight", "denied_boarding", "airline", None, 2.5), ("offloaded", "flight", "denied_boarding", "airline", None, 2.5),
    ("pnr", "flight", "ticketing", "airline", None, 0.5), ("web check-in", "flight", "ticketing", "airline", None, 1.0),
    ("booking", "flight", "ticketing", "airline", None, 0.5), ("airline", "flight", "other", "airline", None, 0.4),
    ("flight", "flight", "other", "airline", None, 0.4), ("boarding pass", "flight", "ticketing", "airline", None, 0.6),
    ("washroom", "airport", "hygiene", "airport_operator", None, 2.0), ("toilet", "airport", "hygiene", "airport_operator", None, 2.0),
    ("dirty", "airport", "hygiene", "airport_operator", None, 1.2), ("unclean", "airport", "hygiene", "airport_operator", None, 1.2),
    ("cleanliness", "airport", "hygiene", "airport_operator", None, 1.5), ("smell", "airport", "hygiene", "airport_operator", None, 1.0),
    ("charging point", "airport", "charging", "airport_operator", None, 2.5), ("charging", "airport", "charging", "airport_operator", None, 1.5),
    ("no water", "airport", "facilities", "airport_operator", None, 2.0), ("drinking water", "airport", "facilities", "airport_operator", None, 2.0),
    ("seating", "airport", "facilities", "airport_operator", None, 1.2), ("air conditioning", "airport", "facilities", "airport_operator", None, 1.5),
    ("ac not working", "airport", "facilities", "airport_operator", None, 2.0), ("lift", "airport", "facilities", "airport_operator", None, 1.0),
    ("escalator", "airport", "facilities", "airport_operator", None, 1.0), ("wifi", "airport", "facilities", "airport_operator", None, 1.2),
    ("trolley", "airport", "facilities", "airport_operator", None, 1.5), ("airport lounge", "airport", "facilities", "airport_operator", None, 1.0),
    ("overpriced food", "airport", "facilities", "airport_operator", None, 1.5), ("food court", "airport", "facilities", "airport_operator", None, 1.2),
    ("security check", "airport", "security", "regulator", "CISF", 2.0), ("security queue", "airport", "security", "regulator", "CISF", 2.0),
    ("frisking", "airport", "security", "regulator", "CISF", 2.0), ("cisf", "airport", "security", "regulator", "CISF", 1.5),
    ("long queue", "airport", "queue_checkin", "airport_operator", None, 2.0), ("check-in queue", "airport", "queue_checkin", "airport_operator", None, 2.5),
    ("queue", "airport", "queue_checkin", "airport_operator", None, 1.0), ("check-in counter", "airport", "queue_checkin", "airport_operator", None, 1.5),
    ("parking", "airport", "parking_transport", "airport_operator", None, 2.0), ("parking fee", "airport", "parking_transport", "airport_operator", None, 2.5),
    ("vip movement", "airport", "vip_movement", "airport_operator", None, 3.0), ("vip", "airport", "vip_movement", "airport_operator", None, 1.0),
    ("medical emergency", "airport", "medical", "airport_operator", None, 3.0), ("ambulance", "airport", "medical", "airport_operator", None, 2.0),
    ("first aid", "airport", "medical", "airport_operator", None, 2.0), ("airport", "airport", "other", "airport_operator", None, 0.4),
    ("terminal", "airport", "other", "airport_operator", None, 0.4), ("immigration", "govt", "immigration", "regulator", "IMMIG", 3.0),
    ("wheelchair", "ground", "wheelchair", "gsp", None, 3.0), ("wheel chair", "ground", "wheelchair", "gsp", None, 3.0),
    ("special assistance", "ground", "wheelchair", "gsp", None, 2.5), ("senior citizen", "ground", "wheelchair", "gsp", None, 1.0),
    ("disabled", "ground", "wheelchair", "gsp", None, 1.5), ("divyang", "ground", "wheelchair", "gsp", None, 1.5),
    ("ambulift", "ground", "wheelchair", "gsp", None, 2.5), ("taxi", "ground", "taxi", "gsp", None, 2.5), ("cab", "ground", "taxi", "gsp", None, 1.5),
    ("prepaid taxi", "ground", "taxi", "gsp", None, 3.0), ("overcharged", "ground", "taxi", "gsp", None, 1.0),
    ("meet and greet", "ground", "meet_greet", "gsp", None, 3.0), ("porter", "ground", "stores", "gsp", None, 1.5),
    ("airport store", "ground", "stores", "gsp", None, 2.0), ("shop", "ground", "stores", "gsp", None, 0.8),
    ("customs", "govt", "customs", "regulator", "CUSTOMS", 3.0), ("duty", "govt", "customs", "regulator", "CUSTOMS", 1.0),
    ("emigration", "govt", "immigration", "regulator", "IMMIG", 3.0), ("passport control", "govt", "immigration", "regulator", "IMMIG", 2.5),
    ("dgca", "govt", "dgca", "regulator", "DGCA", 2.0), ("bcas", "govt", "bcas", "regulator", "BCAS", 2.0),
    ("bribe", "govt", "malpractice", "regulator", "AAI", 3.0), ("malpractice", "govt", "malpractice", "regulator", "AAI", 3.0),
    ("unfair demand", "govt", "malpractice", "regulator", "AAI", 3.0), ("corruption", "govt", "malpractice", "regulator", "AAI", 3.0),
    ("suggestion", "other", "suggestion", "aai", None, 1.5), ("feedback", "other", "suggestion", "aai", None, 0.8),
    ("information", "other", "query", "aai", None, 0.6),
]

# keyword -> severity (1 = critical). Highest (lowest number) match wins.
SEVERITY_KEYWORDS = [
    ("medical emergency", 1), ("medicine", 1), ("medicines", 1), ("insulin", 1), ("dawai", 1), ("dawa", 1), ("दवा", 1), ("दवाई", 1),
    ("life saving", 1), ("oxygen", 1), ("heart attack", 1), ("unconscious", 1), ("fainted", 1), ("seizure", 1), ("ambulance", 1),
    ("admit card", 1), ("exam", 1), ("hall ticket", 1), ("एडमिट कार्ड", 1), ("organ", 1), ("transplant", 1), ("dialysis", 1),
    ("critical patient", 1), ("infant formula", 1), ("baby milk", 1), ("bomb", 1), ("fire", 1), ("emergency", 1),
    ("safety", 2), ("unsafe", 2), ("harassment", 2), ("molest", 2), ("assault", 2), ("stolen", 2), ("theft", 2), ("lost passport", 2),
    ("wheelchair", 2), ("senior citizen", 2), ("elderly", 2), ("pregnant", 2), ("disabled", 2), ("child alone", 2), ("stranded", 2),
    ("overnight", 2), ("no food", 2), ("no water", 2), ("misbehaved", 2), ("bribe", 2), ("discrimination", 2), ("passport", 2),
    ("denied boarding", 2), ("offloaded", 2), ("cancelled", 2), ("refund not received", 2), ("visa", 2),
    ("suggestion", 4), ("feedback", 4), ("information", 4), ("query", 4), ("wifi", 4), ("charging", 4), ("minor", 4), ("seating", 4),
]

# name, category, severity, e1, e2, e3
SLA_POLICIES = [
    ("Critical (S1) - emergency", None, 1, 4, 12, 24),
    ("High (S2)", None, 2, 12, 36, 60),
    ("On-ground assistance", "ground", None, 6, 24, 48),
    ("Government dept", "govt", None, 48, 96, 168),
    ("Standard", None, None, 24, 72, 96),
]

# Illustrative simplified CAR rule base (labelled as such in the UI). Values are config, editable at runtime.
CAR_RULES = [
    ("CAR-3M-II-REFUND", "CAR Sec 3 Series M Part II - refund of ticket on airline cancellation/delay: full refund of ticket amount",
     "refund", "refund_min", {"percent_of_ticket": 100, "refund_within_days": 21}),
    ("CAR-3M-IV-COMP", "CAR Sec 3 Series M Part IV - compensation for denied boarding / cancellation (block time based)",
     "denied_boarding", "compensation_table", {"table": [[1, 5000], [2, 7500], [999, 10000]], "cap": "basic_fare_plus_fuel"}),
    ("CAR-3M-IV-DELAY", "CAR Sec 3 Series M Part IV - cancellation / long delay: compensation or refund",
     "delay_cancellation", "compensation_table", {"table": [[1, 5000], [2, 7500], [999, 10000]], "cap": "basic_fare_plus_fuel"}),
    ("CAR-BAG-LIAB", "Carriage by Air Act liability for lost/damaged baggage - Rs 350 per kg (assumed illustrative)",
     "baggage_lost", "baggage_liability", {"per_kg": 350, "default_kg": 20}),
    ("CAR-BAG-DMG", "Damaged baggage - repair or compensation up to Rs 350 per kg (assumed illustrative)",
     "baggage_damaged", "baggage_liability", {"per_kg": 350, "default_kg": 20}),
]

CONFIG_DEFAULTS = {
    "allow_pre_breach_filing": True,   # RFP inconsistency flag (FRS 3.2 #16 vs #18)
    "max_reopens": 2,
    "retention_days": 365,
    "social_retention_days": 90,
    "viral_threshold": 5,
    "dedup_window_hours": 72,
    "dup_similarity": 0.55,
    "minister_handle": "@CivilAviationMinister",
    "crisis_banner": {"active": False, "text": "", "text_hi": ""},
    "session_idle_minutes": 30,
    "monthly_invoice_inr": 5000000,
    "pu_target": 60,
    "pacr_seats": 12,
    "demo_mode": True,
}

# Hinglish / Hindi mock dictionary (pluggable translator default). Longest phrases matched first.
HI_PHRASES = {
    "kho gaya": "lost", "kho gayi": "lost", "khoya": "lost", "nahi mila": "not received", "nahi mili": "not received",
    "nahi aaya": "not received", "nahi aayi": "not received", "late hai": "is delayed", "late ho gayi": "delayed", "देर से": "delayed",
    "refund nahi": "refund not received", "paisa wapas": "refund money", "paise wapas": "refund money", "paise nahi": "money not",
    "bahut gandi": "very dirty", "bahut ganda": "very dirty", "gande": "dirty", "ganda": "dirty", "gandi": "dirty",
    "kaam nahi kar": "not working", "kaam nahi": "not working", "madad chahiye": "need help", "help chahiye": "need help",
    "व्हीलचेयर": "wheelchair", "सामान": "baggage", "खो गया": "lost", "खो गई": "lost", "नहीं मिला": "not received",
    "नहीं मिली": "not received", "रिफंड": "refund", "फ्लाइट": "flight", "देरी": "delay", "रद्द": "cancelled",
    "दवाई": "medicine", "दवा": "medicine", "शौचालय": "washroom", "गंदा": "dirty", "गंदी": "dirty", "एयरपोर्ट": "airport",
    "बैग": "bag", "टिकट": "ticket", "पैसे": "money", "वापस": "back", "मेरा": "my", "मेरी": "my", "मुझे": "me", "कृपया": "please",
    "कर्मचारी": "staff", "बदतमीज़": "rude", "बदतमीज": "rude", "रिश्वत": "bribe", "बुजुर्ग": "elderly", "मदद": "help",
    "चेक-इन": "check-in", "लाइन": "queue", "सुरक्षा": "security", "खाना": "food", "पानी": "water", "नहीं": "not", "है": "",
    "में": "in", "का": "of", "की": "of", "को": "to", "और": "and", "से": "from", "पर": "on", "था": "was", "गया": "", "गई": "",
}
HI_WORDS = {
    "mera": "my", "meri": "my", "mere": "my", "mujhe": "me", "hai": "", "hain": "", "ho": "", "tha": "was", "bag": "bag", "saman": "baggage",
    "samaan": "baggage", "bhai": "", "yaar": "", "kya": "what", "kab": "when", "kyun": "why", "nahi": "not", "nhi": "not", "bahut": "very",
    "ghanta": "hour", "ghante": "hours", "ghanton": "hours", "se": "since", "ka": "of", "ki": "of", "ko": "to", "ke": "of", "par": "on",
    "pe": "on", "mein": "in", "me": "in", "aur": "and", "dawai": "medicine", "dawa": "medicine", "paisa": "money", "paise": "money",
    "wapas": "back", "abhi": "still", "tak": "until", "kharab": "bad", "bekar": "useless", "bakwas": "rubbish", "wala": "", "wali": "",
    "kripya": "please", "sunwai": "hearing", "dhoka": "cheating", "log": "people", "sab": "all", "koi": "no one", "jawab": "reply",
    "uttar": "reply", "tang": "harassed", "pareshan": "troubled", "dikkat": "problem", "samasya": "problem", "ticket": "ticket",
    "udaan": "flight", "udan": "flight", "hawai": "air", "adda": "airport", "rd": "", "dekho": "look", "karo": "do", "kar": "do", "do": "give",
    "diya": "gave", "gaya": "went", "gayi": "went", "hua": "happened", "hui": "happened", "raha": "", "rahi": "", "rahe": "", "toh": "", "bhi": "also",
    "ek": "one", "teen": "three", "char": "four", "paanch": "five", "chhe": "six", "saat": "seven", "aath": "eight", "ghar": "home",
    "bacchon": "children", "bachche": "children", "bacche": "children", "budhe": "elderly", "dadi": "grandmother", "dada": "grandfather",
}
HINGLISH_MARKERS = {"hai", "nahi", "nhi", "mera", "meri", "kya", "kab", "bhai", "yaar", "ho", "gaya", "gayi", "mujhe", "kripya", "paisa", "ghante",
                    "ghanta", "hain", "toh", "abhi", "bahut", "aur", "mein", "wapas", "kho", "saman", "samaan", "dawai", "ka", "ki", "ke", "se", "tha"}

POSITIVE_WORDS = {"great", "excellent", "amazing", "awesome", "wonderful", "thank", "thanks", "thankyou", "kudos", "appreciate", "smooth", "best",
                  "love", "loved", "fantastic", "superb", "impressed", "helpful", "polite", "lovely", "happy", "good"}
NEGATIVE_WORDS = {"worst", "terrible", "horrible", "pathetic", "awful", "disgusting", "unacceptable", "bad", "useless", "rude", "angry", "fed up",
                  "ridiculous", "shameful", "harassed", "cheated", "fraud", "scam", "never", "no one", "nobody", "waiting", "stuck", "lost", "delayed",
                  "dirty", "broken", "damaged", "missing", "not received", "not working", "poor", "disappointed"}
COMPLAINT_SIGNALS = {"delayed", "delay", "cancelled", "lost", "missing", "refund", "damaged", "rude", "dirty", "broken", "not working", "waiting",
                     "stuck", "no one", "nobody", "help", "complaint", "worst", "pathetic", "terrible", "unacceptable", "harass", "cheated",
                     "not received", "overcharged", "queue", "denied", "offloaded", "medicine", "stranded", "no response", "not responding", "fed up",
                     "bribe", "unfair", "ignored", "pls", "please", "need", "urgent", "demand", "wheelchair", "poor", "disappointed", "mishandled",
                     "hours", "no water", "unclean", "smell", "mismanagement", "unprofessional"}
SPAM_PATTERNS = ["buy now", "% off", "discount", "click here", "click the link", "limited offer", "giveaway", "follow back", "free gift",
                 "crypto", "earn money", "work from home", "promo code", "use code", "dm for promo", "win a", "bit.ly", "sale ends", "cheap flights",
                 "book now at", "subscribe", "loan approved", "casino", "lottery"]
MEME_PATTERNS = ["meme", "lol", "lmao", "rofl", "😂", "🤣", "joke", "funny", "trending sound", "reel"]
AVIATION_KEYWORDS = ["flight", "airport", "airline", "baggage", "luggage", "pnr", "boarding", "refund", "terminal", "runway", "check-in", "checkin",
                     "wheelchair", "cabin crew", "departure", "arrival", "immigration", "customs", "security check", "gate", "ticket", "plane",
                     "aircraft", "lounge", "trolley", "cisf", "layover", "air india", "indigo", "akasa", "spicejet", "vistara", "delay", "cancelled",
                     "washroom", "taxi", "parking"]
WATCH_DEFAULT_HANDLES = [
    ("@MoCA_GoI", "Ministry of Civil Aviation"), ("@AAI_Official", "Airports Authority of India"), ("@DGCAIndia", "DGCA"),
    ("@BCAS_India", "BCAS"), ("@CivilAviationMinister", "Minister (configurable)"), ("@AirSewa_Official", "AirSewa"),
    ("@IndiGo6E", "IndiGo"), ("@airindia", "Air India"), ("@AkasaAir", "Akasa Air"), ("@flyspicejet", "SpiceJet"), ("@AirIndiaX", "Air India Express"),
    ("@DelhiAirport", "Delhi Airport"), ("@CSMIA_Official", "Mumbai Airport"), ("@BLRAirport", "Bengaluru Airport"),
    ("@RGIAHyderabad", "Hyderabad Airport"), ("@KochiAirport", "Kochi Airport"), ("@CISFHQrs", "CISF"),
]
WATCH_DEFAULT_HASHTAGS = ["#AirSewa", "#AirSewaDemo", "#flightdelay", "#lostbaggage", "#airportcomplaint", "#refund", "#flightcancelled", "#wheelchair"]

