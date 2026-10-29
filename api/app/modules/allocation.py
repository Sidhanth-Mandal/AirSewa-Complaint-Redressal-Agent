"""Rule-based Ticket Allocation Engine (RFP 2.5.35, FRS 3.3).
One engine is reused by the portal, social pipeline and every PACR channel.
Rules live in the DB (admin-editable, no code change). `classify` is pure and unit-testable."""
import re
from dataclasses import dataclass, field

from .. import reference as R

AIRLINE_CODES = ["6E", "AI", "QP", "SG", "IX", "S5", "9I", "I5", "UK", "G8", "2T"]
CITY_ALIASES = {"bangalore": "BLR", "bengaluru": "BLR", "bombay": "BOM", "mumbai": "BOM", "delhi": "DEL", "madras": "MAA", "chennai": "MAA",
                "calcutta": "CCU", "kolkata": "CCU", "hyderabad": "HYD", "ahmedabad": "AMD", "pune": "PNQ", "goa": "GOI", "cochin": "COK",
                "kochi": "COK", "trivandrum": "TRV", "thiruvananthapuram": "TRV", "jaipur": "JAI", "lucknow": "LKO", "guwahati": "GAU",
                "patna": "PAT", "chandigarh": "IXC", "bhubaneswar": "BBI", "indore": "IDR", "srinagar": "SXR", "varanasi": "VNS", "banaras": "VNS"}
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


@dataclass
class Ruleset:
    rules: list = field(default_factory=list)      # (keyword, category, subcategory, target_type, org_code, weight)
    severity: list = field(default_factory=list)   # (keyword, severity)
    handles: dict = field(default_factory=dict)    # '@indigo6e' -> ('airline', '6E')

    @staticmethod
    def default() -> "Ruleset":
        h = {}
        for code, _n, typ, handle, _c in R.ORGS:
            if handle:
                h[handle.lower()] = (typ, code)
        for a in R.AIRPORTS:
            h[a[6].lower()] = ("airport", a[0])
        return Ruleset(list(R.ALLOCATION_RULES), list(R.SEVERITY_KEYWORDS), h)


_cache: dict = {}


def invalidate():
    _cache.clear()


def load_ruleset(db) -> Ruleset:
    if "rs" in _cache:
        return _cache["rs"]
    from ..models import AllocationRule, Organisation, Airport, SeverityKeyword
    rs = Ruleset(
        rules=[(r.keyword.lower(), r.category, r.subcategory, r.target_type, r.target_org_code, r.weight or 1.0)
               for r in db.query(AllocationRule).filter(AllocationRule.active == True)],  # noqa: E712
        severity=[(s.keyword.lower(), s.severity) for s in db.query(SeverityKeyword).filter(SeverityKeyword.active == True)],  # noqa: E712
        handles={},
    )
    for o in db.query(Organisation):
        if o.handle:
            rs.handles[o.handle.lower()] = (o.type, o.code)
    for a in db.query(Airport):
        if a.handle:
            rs.handles[a.handle.lower()] = ("airport", a.code)
    _cache["rs"] = rs
    return rs


def _pattern(kw: str):
    if re.search(r"[\u0900-\u097f]", kw):
        return re.compile(re.escape(kw))
    return re.compile(r"(?<![a-z0-9])" + re.escape(kw) + r"(?:s|es|ed|d|ing)?(?![a-z0-9])", re.I)


_pat_cache: dict = {}


def match(kw: str, text: str) -> bool:
    p = _pat_cache.get(kw)
    if p is None:
        p = _pat_cache[kw] = _pattern(kw)
    return bool(p.search(text))


def sentiment(text: str) -> float:
    t = text.lower()
    toks = set(re.findall(r"[a-z']+", t))
    pos = len(toks & R.POSITIVE_WORDS) + sum(t.count(e) for e in ("😊", "👍", "❤", "🙏", "😍"))
    neg = len(toks & R.NEGATIVE_WORDS) + sum(1 for p in ("not received", "not working", "no one", "fed up") if p in t) + sum(t.count(e) for e in ("😡", "😠", "😤", "👎", "🤬"))
    neg += 1 if "!!" in t and pos == 0 else 0
    return round(max(-1.0, min(1.0, (pos - neg) / (pos + neg + 1.5))), 2)


def extract_entities(text: str, handles: dict | None = None) -> dict:
    ent: dict = {}
    codes = "|".join(AIRLINE_CODES)
    m = re.search(rf"\b({codes})[\s-]?(\d{{2,4}})\b", text, re.I)
    flight_span = None
    if m:
        ent["flight_no"] = f"{m.group(1).upper()}{m.group(2)}"
        ent["airline_code"] = m.group(1).upper()
        flight_span = m.span()
    p = re.search(r"\bPNR\s*(?:no\.?|number|is)?[:\s#-]*([A-Z0-9]{6})\b", text, re.I)
    if p:
        ent["pnr"] = p.group(1).upper()
    else:
        for c in re.finditer(r"\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{6}\b", text):
            if flight_span and c.start() >= flight_span[0] and c.end() <= flight_span[1] + 1:
                continue
            ent["pnr"] = c.group(0)
            break
    s = re.search(r"\b(?:srn|sr\s*no|service\s*request(?:\s*no)?)[\s:#.-]*([A-Z0-9-]{5,})", text, re.I)
    if s:
        ent["service_request_no"] = s.group(1).upper()
    low = text.lower()
    if "airline_code" not in ent:
        for code, names in R.AIRLINE_ALIASES.items():
            if any(re.search(rf"(?<![a-z0-9]){re.escape(n.strip())}(?![a-z0-9])", low) for n in names if len(n.strip()) > 2):
                ent["airline_code"] = code
                break
    if "airline_code" not in ent and handles:
        for h in re.findall(r"@\w+", text):
            t = handles.get(h.lower())
            if t and t[0] == "airline":
                ent["airline_code"] = t[1]
                break
    airport = None
    for h in re.findall(r"@\w+", text):
        t = (handles or {}).get(h.lower())
        if t and t[0] == "airport":
            airport = t[1]
            break
    if not airport:
        best = None
        for city, code in CITY_ALIASES.items():
            mm = re.search(rf"(?<![a-z]){city}(?![a-z])", low)
            if mm and (best is None or mm.start() < best[0]):
                best = (mm.start(), code)
        if best:
            airport = best[1]
    if not airport:
        known = {a[0] for a in R.AIRPORTS}
        for tok in re.findall(r"\b[A-Z]{3}\b", text):
            if tok in known:
                airport = tok
                break
    if airport:
        ent["airport_code"] = airport
    d = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text)
    if d:
        ent["date"] = d.group(0)
    else:
        d = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({'|'.join(MONTHS)})[a-z]*\b", low)
        if d:
            ent["date"] = d.group(0)
        else:
            for w in ("today", "yesterday", "tonight", "this morning"):
                if w in low:
                    ent["date"] = w
                    break
    return ent


@dataclass
class Classification:
    category: str
    subcategory: str
    target_type: str
    target_org_code: str | None
    severity: int
    severity_reason: str
    severity_keywords: list
    matched_keywords: list
    confidence: float
    sentiment: float
    entities: dict
    scores: dict

    def as_dict(self):
        return self.__dict__.copy()


def classify(text: str, rs: Ruleset | None = None, forced_category: str | None = None) -> Classification:
    rs = rs or Ruleset.default()
    low = text.lower()
    ent = extract_entities(text, rs.handles)
    cat_scores: dict = {}
    sub_scores: dict = {}
    sub_target: dict = {}
    matched = []
    for kw, cat, sub, ttype, ocode, w in rs.rules:
        if forced_category and cat != forced_category:
            continue
        if match(kw, low):
            matched.append(kw)
            cat_scores[cat] = cat_scores.get(cat, 0) + w
            sub_scores[(cat, sub)] = sub_scores.get((cat, sub), 0) + w
            if (cat, sub) not in sub_target or w > sub_target[(cat, sub)][2]:
                sub_target[(cat, sub)] = (ttype, ocode, w)
    if forced_category and forced_category not in cat_scores:
        cat_scores[forced_category] = 0.1
    # mention of a regulator/airport/airline handle nudges category
    for h in re.findall(r"@\w+", text):
        t = rs.handles.get(h.lower())
        if t and not forced_category:
            bump = {"airline": "flight", "airport": "airport"}.get(t[0])
            if bump:
                cat_scores[bump] = cat_scores.get(bump, 0) + 0.3
    if cat_scores:
        ranked = sorted(cat_scores.items(), key=lambda kv: -kv[1])
        category, top = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0
        subs = sorted(((s, v) for (c, s), v in sub_scores.items() if c == category), key=lambda kv: -kv[1])
        subcategory = subs[0][0] if subs else "other"
        ttype, ocode, _ = sub_target.get((category, subcategory), (None, None, 0))
        conf = min(0.98, 0.35 + 0.08 * len(matched) + 0.3 * (top - second) / (top + 0.01) + min(0.2, top / 15))
    else:
        category, subcategory, ttype, ocode, conf = "other", "query", "aai", None, 0.25
    ttype = ttype or {"flight": "airline", "airport": "airport_operator", "ground": "gsp", "govt": "regulator", "other": "aai"}[category]
    # severity matrix
    hits = [(kw, sv) for kw, sv in rs.severity if match(kw, low)]
    if hits:
        sev = min(s for _, s in hits)
        kws = sorted({k for k, s in hits if s == sev})
        reason = f"S{sev}: matched keyword(s) " + ", ".join(f"'{k}'" for k in kws)
    else:
        sev, kws, reason = 3, [], "S3: no priority keywords matched (default)"
    return Classification(category, subcategory, ttype, ocode, sev, reason, kws, matched[:12], round(conf, 2), sentiment(text), ent,
                          {k: round(v, 2) for k, v in cat_scores.items()})


def start_level_for(severity: int) -> int:
    """FRS 3.3 #8/#9: S1 -> redressor staff L2 and above, S2-S4 -> L1."""
    return 2 if severity == 1 else 1


def route(db, cls: Classification, airport_id=None, airline_org_id=None):
    """Resolve the concrete assignee organisation for a classification. Returns Organisation."""
    from ..models import Airport, Organisation
    q = db.query(Organisation)
    aai = q.filter(Organisation.code == "AAI").first()
    if cls.target_org_code:
        o = q.filter(Organisation.code == cls.target_org_code).first()
        if o:
            return o
    t = cls.target_type
    if t == "airline":
        code = cls.entities.get("airline_code")
        if airline_org_id:
            return db.get(Organisation, airline_org_id) or aai
        if code:
            o = q.filter(Organisation.code == code).first()
            if o:
                return o
        return aai  # unknown airline -> AAI/PACR triage
    if t == "airport_operator":
        ap = db.get(Airport, airport_id) if airport_id else None
        if not ap and cls.entities.get("airport_code"):
            ap = db.query(Airport).filter(Airport.code == cls.entities["airport_code"]).first()
        if ap and ap.operator_id:
            return db.get(Organisation, ap.operator_id)
        return aai
    if t == "gsp":
        gsps = q.filter(Organisation.type == "gsp").order_by(Organisation.id).all()
        code = cls.entities.get("airport_code") or ""
        return gsps[sum(map(ord, code)) % len(gsps)] if gsps else aai
    if t == "ota":
        return q.filter(Organisation.type == "ota").first() or aai
    return aai
