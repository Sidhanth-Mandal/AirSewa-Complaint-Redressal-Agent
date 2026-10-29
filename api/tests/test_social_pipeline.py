"""Relevance filter, language/translation, entity extraction, dedup (>= 20 sample social posts) - pure functions."""
import pytest

from app import reference as R
from app.adapters import registry
from app.modules import allocation as A
from app.modules import social as S

WATCH = ({h.lower() for h, _ in R.WATCH_DEFAULT_HANDLES}, {h.lower() for h in R.WATCH_DEFAULT_HASHTAGS}, ["airsewa"])


def rel(text, mentions=None, tags=None, parent=False):
    lang = registry.translator.detect(text)
    en = registry.translator.translate(text, lang)
    ment = mentions if mentions is not None else [m for m in __import__("re").findall(r"@\w+", text)]
    tg = tags if tags is not None else __import__("re").findall(r"#\w+", text)
    return S.relevance(text if lang == "en" else f"{text} {en}", ment, tg, WATCH, parent_is_complaint=parent)


# (text, expected_complaint, expected_reason_fragment)
SAMPLES = [
    ("@IndiGo6E flight 6E 204 delayed 4 hours, no water. Pathetic! #flightdelay", True, "Complaint"),
    ("@airindia my refund is still not received after 20 days @MoCA_GoI", True, "Complaint"),
    ("@AAI_Official washrooms at Delhi airport are filthy and dirty", True, "Complaint"),
    ("@DGCAIndia denied boarding on 6E 512 despite confirmed ticket. Unacceptable", True, "Complaint"),
    ("@AkasaAir lost my baggage, nobody is responding", True, "Complaint"),
    ("@MoCA_GoI wheelchair not provided to my father at BLR airport, stranded", True, "Complaint"),
    ("@flyspicejet cancelled my flight at the last minute #flightcancelled", True, "Complaint"),
    ("@AAI_Official मेरा सामान एयरपोर्ट पर खो गया और उसमें दवाई थी। कृपया मदद करें", True, "Complaint"),
    ("@airindia bhai flight 5 ghante late hai, koi jawab nahi de raha #AirSewa", True, "Complaint"),
    ("@airindia refund nahi mila abhi tak, PNR AB12CD", True, "Complaint"),
    ("Cheap flights to Goa! Use code FLY50 for 50% off, click here bit.ly/x @airindia", False, "spam"),
    ("Earn money work from home giveaway follow back @AAI_Official", False, "spam"),
    ("Thank you @AkasaAir for the smooth flight and lovely crew, great service! #AirSewa", False, "positive"),
    ("Amazing experience at Delhi airport, very helpful staff. Kudos @AAI_Official", False, "positive"),
    ("lol my flight is delayed so I became a travel influencer 😂 meme @IndiGo6E", False, "meme"),
    ("Just landed in Pune! Weather is lovely today", False, "Not relevant"),
    ("Cricket match tonight, who is watching? #IPL", False, "Not relevant"),
    ("What is the baggage allowance for @airindia domestic flights?", False, "informational"),
    ("Traffic is crazy this evening in the city", False, "Not relevant"),
    ("@AirSewa_Official stuck at airport for 6 hours with no food, kids crying, please help", True, "Complaint"),
]


@pytest.mark.parametrize("text,expected,fragment", SAMPLES)
def test_relevance_filter(text, expected, fragment):
    r = rel(text)
    assert r["complaint"] is expected, r
    assert fragment.lower() in r["reason"].lower()


def test_sample_count_at_least_20():
    assert len(SAMPLES) >= 20


def test_plus_one_reply_inherits_thread():
    r = rel("+1 same issue happened to me", mentions=[], tags=[], parent=True)
    assert r["complaint"] and r.get("plus_one")


def test_watch_list_hashtag_triggers_detection():
    r = S.relevance("so slow today #AirSewaDemo", [], ["#AirSewaDemo"], WATCH)
    assert r["relevant"]


# --- language detect / translate
def test_detect_languages():
    t = registry.translator
    assert t.detect("The flight is delayed") == "en"
    assert t.detect("मेरा सामान खो गया") == "hi"
    assert t.detect("mera saman kho gaya hai bhai") == "hinglish"


def test_hindi_translation_and_classification():
    t = registry.translator
    en = t.translate("मेरा सामान एयरपोर्ट पर खो गया और उसमें दवाई थी", "hi")
    assert "baggage" in en and "lost" in en and "medicine" in en
    c = A.classify(en, A.Ruleset.default())
    assert c.category == "flight" and c.severity == 1


def test_hinglish_translation_and_classification():
    t = registry.translator
    en = t.translate("mera saman kho gaya, refund nahi mila", "hinglish")
    assert "baggage" in en and "lost" in en
    assert A.classify(en, A.Ruleset.default()).category == "flight"


# --- entity extraction in posts
def test_social_entities():
    e = A.extract_entities("@IndiGo6E 6E 741 BLR-DEL delayed. PNR RK4P2M", A.Ruleset.default().handles)
    assert e["flight_no"] == "6E741" and e["pnr"] == "RK4P2M" and e["airline_code"] == "6E"


# --- dedup similarity
def test_jaccard_similarity_groups_near_duplicates():
    a = "flight 6E 741 delayed 3 hours no announcement bangalore"
    assert S.jaccard(a, "6E 741 bangalore flight delayed three hours no announcement again") > 0.4
    assert S.jaccard(a, "washroom dirty at lucknow airport") < 0.1


def test_image_stub_labels():
    assert "damaged baggage" in S.image_note([{"name": "damaged_bag.jpg"}])
    assert "boarding pass" in S.image_note([{"name": "my_boarding_pass.png"}])
    assert S.image_note([]) is None
