"""Text templates for seeded grievances and social posts (English, Hinglish, Hindi)."""

# subcategory -> category, weight, templates [(lang, text)]
TEMPLATES = {
    "delay_cancellation": ("flight", 22, [
        ("en", "{airline} flight {flight} from {city} was delayed by {hrs} hours with no announcement. PNR {pnr}. Please help."),
        ("en", "Flight {flight} cancelled at the last minute and no alternate arranged by {airline}. Stuck at {city} airport."),
        ("en", "Delayed {hrs} hours on the tarmac at {city}, no water or food served. {airline} {flight}."),
        ("hinglish", "{airline} ki flight {flight} {hrs} ghante late hai, koi announcement nahi. PNR {pnr}"),
        ("hi", "फ्लाइट {flight} में {hrs} घंटे की देरी हुई, कोई जानकारी नहीं दी गई"),
    ]),
    "refund": ("flight", 20, [
        ("en", "Refund not received for cancelled flight {flight}. PNR {pnr}. It has been {days} days, {airline} is not responding."),
        ("en", "Booked via OTA, airline cancelled the flight but my money back is still pending. PNR {pnr}."),
        ("en", "Refund for ticket {pnr} was credited only partially. Need full refund as per DGCA rules."),
        ("hinglish", "refund nahi mila abhi tak {days} din se, PNR {pnr}. paisa wapas chahiye {airline}"),
        ("hi", "रिफंड नहीं मिला, PNR {pnr}। कृपया मदद करें"),
    ]),
    "baggage_lost": ("flight", 9, [
        ("en", "My baggage is lost after {airline} flight {flight}. No update for {days} days. PNR {pnr}."),
        ("en", "Luggage missing at {city} baggage belt, airline staff not helpful. Flight {flight}."),
        ("en", "Lost baggage on {flight}: it contains my father's medicine, urgent help needed. PNR {pnr}"),
        ("en", "My daughter's admit card for tomorrow's exam was in the checked bag on {flight}, bag not received. Urgent!"),
        ("hinglish", "mera saman {city} airport par kho gaya, {airline} wale jawab nahi de rahe. PNR {pnr}"),
        ("hi", "मेरा सामान {city} एयरपोर्ट पर खो गया, कृपया मदद करें"),
    ]),
    "baggage_damaged": ("flight", 4, [
        ("en", "Suitcase damaged with a broken wheel after flight {flight} on {airline}. PNR {pnr}. Want compensation."),
        ("en", "Damaged baggage received at {city}, handle torn. {airline} refusing to accept the claim."),
    ]),
    "baggage_delay": ("flight", 3, [
        ("en", "Baggage delay of {hrs} hours at {city} for {flight}, belt completely empty."),
    ]),
    "staff_behaviour": ("flight", 3, [
        ("en", "Cabin crew on {airline} {flight} were rude and misbehaved with an elderly passenger."),
        ("en", "Rude staff at the {airline} counter in {city}, no proper answers given."),
    ]),
    "meals": ("flight", 2, [("en", "Food on flight {flight} was stale and the meal I paid for was not served. {airline}")]),
    "fare": ("flight", 2, [("en", "Air fare hike on the {airline} {city} route is ridiculous, ticket price tripled during the festival.")]),
    "denied_boarding": ("flight", 3, [
        ("en", "Denied boarding on {flight} despite a confirmed ticket, flight overbooked by {airline}. PNR {pnr}"),
        ("en", "Offloaded from flight {flight} at {city} without compensation. PNR {pnr}"),
    ]),
    "ticketing": ("flight", 2, [("en", "Web check-in failing for PNR {pnr} on {airline}, booking shows an error.")]),
    "hygiene": ("airport", 9, [
        ("en", "Washrooms at {city} airport terminal are very dirty and have no water."),
        ("en", "Cleanliness at {city} airport is poor, bad smell near the gates."),
        ("hinglish", "{city} airport par washroom bahut ganda hai, paani nahi hai"),
        ("hi", "एयरपोर्ट पर शौचालय बहुत गंदा है"),
    ]),
    "charging": ("airport", 3, [("en", "No working charging points near the gates at {city} airport.")]),
    "facilities": ("airport", 6, [
        ("en", "Drinking water not available and AC not working at the {city} terminal."),
        ("en", "Escalator and lift broken at {city} airport for a week."),
        ("en", "Overpriced food at the {city} food court, Rs 300 for a tea."),
    ]),
    "security": ("airport", 4, [
        ("en", "Security check queue at {city} is extremely long, took 90 minutes. CISF staff rude."),
        ("en", "Frisking at {city} security was handled badly, no privacy provided."),
    ]),
    "queue_checkin": ("airport", 5, [("en", "Check-in queue at {city} is very long for {airline}, only two counters open.")]),
    "parking_transport": ("airport", 3, [("en", "Parking fee at {city} airport is overcharged, ticket machine faulty.")]),
    "medical": ("airport", 1, [("en", "Passenger fainted at {city} airport, medical emergency, ambulance not available quickly.")]),
    "vip_movement": ("airport", 2, [("en", "Due to VIP movement at {city} all passengers were held for 40 minutes, almost missed my flight.")]),
    "wheelchair": ("ground", 7, [
        ("en", "Wheelchair assistance was not provided for my elderly mother at {city} airport, waited 1 hour."),
        ("en", "Special assistance for a disabled passenger was missing at {city} on {airline} {flight}."),
        ("hinglish", "wheelchair nahi mili mere dadi ko {city} par, madad chahiye"),
    ]),
    "taxi": ("ground", 3, [("en", "Prepaid taxi counter at {city} overcharged us and the cab driver demanded extra money.")]),
    "meet_greet": ("ground", 1, [("en", "Meet and greet service at {city} did not show up despite payment.")]),
    "stores": ("ground", 2, [("en", "Airport store at {city} is charging double MRP for water and snacks.")]),
    "customs": ("govt", 2, [("en", "Customs officers at {city} demanded unfair duty on my personal laptop.")]),
    "immigration": ("govt", 2, [("en", "Immigration queue at {city} is very slow, only two counters were open.")]),
    "malpractice": ("govt", 1, [("en", "A porter asked for a bribe at {city} airport, unfair demand for money.")]),
    "suggestion": ("other", 4, [("en", "Suggestion: add more seating and charging points near the gates at {city} airport.")]),
    "query": ("other", 3, [("en", "I need information about the process for lodging a grievance against an airline for a delayed flight.")]),
}

# Social post texts. {h} = airline handle, placeholders as above. (lang, text, kind)
SOCIAL_COMPLAINTS = [
    ("en", "{h} flight {flight} {city} delayed {hrs} hours, no announcements, no water. PNR {pnr}. Pathetic service! {tag}"),
    ("en", "{h} my refund for cancelled flight {pnr} is still not received after {days} days. @MoCA_GoI please intervene {tag}"),
    ("en", "@AAI_Official washrooms at {city} airport are filthy and there is no water. Please look into it {tag}"),
    ("en", "@DGCAIndia {h} denied boarding to us on {flight} despite confirmed tickets. Unacceptable! {tag}"),
    ("en", "{h} lost my baggage on {flight} from {city}. No response for {days} days. PNR {pnr} {tag}"),
    ("en", "Wheelchair assistance not available for my father at {city} airport, waited for an hour @AAI_Official {tag}"),
    ("en", "@CivilAviationMinister long queues at security check at {city}, 90 minutes wait. Please help {tag}"),
    ("en", "{h} cabin crew were rude to an elderly passenger on {flight}. Shameful behaviour {tag}"),
    ("en", "Stuck at {city} for {hrs} hours, no food, no water, flight {flight} cancelled by {h}. Help! {tag}"),
    ("en", "@AAI_Official escalator and lift not working at {city} airport for days, senior citizens suffering {tag}"),
    ("hinglish", "{h} bhai flight {flight} {hrs} ghante late hai, koi jawab nahi de raha. PNR {pnr} {tag}"),
    ("hinglish", "{h} mera saman {city} airport par kho gaya, {days} din se koi update nahi. madad chahiye {tag}"),
    ("hinglish", "@AAI_Official {city} airport par washroom bahut ganda hai aur paani nahi hai {tag}"),
    ("hinglish", "{h} refund nahi mila abhi tak, PNR {pnr}. paisa wapas kab milega? {tag}"),
    ("hi", "@AAI_Official मेरा सामान {city} एयरपोर्ट पर खो गया और उसमें दवाई थी। कृपया मदद करें {tag}"),
    ("hi", "{h} फ्लाइट {flight} में {hrs} घंटे की देरी हुई, कोई जानकारी नहीं दी गई। {tag}"),
    ("hi", "@MoCA_GoI रिफंड नहीं मिला, PNR {pnr}। कृपया मदद करें {tag}"),
]
SOCIAL_SPAM = [
    "Cheap flights to Goa! Use code FLY50 for 50% off, click here bit.ly/abc {h}",
    "Earn money from home! Work from home and win a free gift, follow back @AAI_Official",
    "Limited offer on flight tickets, book now at lowest fares, discount ends tonight {h} #flightdelay",
    "Giveaway! Win a free trip, subscribe and follow back #AirSewa",
]
SOCIAL_PRAISE = [
    "Thank you {h} for the smooth flight and lovely crew today, great service! #AirSewa",
    "Amazing experience at {city} airport, very helpful staff. Kudos @AAI_Official!",
    "Excellent boarding at {city} today, thanks {h}. Best airline experience in a while",
    "Loved the new terminal at {city}, super clean and polite staff. Thanks @AAI_Official",
]
SOCIAL_MEME = [
    "lol my flight is delayed so I became a travel influencer at the gate 😂 {h} #flightdelay",
    "airport food prices be like 😂😂 meme {h}",
]
SOCIAL_CHATTER = [
    "Just landed in {city}! The weather is lovely today",
    "Cricket match tonight, who is watching? #IPL",
    "Which phone should I buy this month? Suggestions please",
    "Monday blues again. Need a holiday!",
    "Traffic in {city} is crazy this evening",
]
SOCIAL_QUERY = [
    "What is the baggage allowance for {h} domestic flights?",
    "Is there a lounge at {city} airport open at night?",
]
