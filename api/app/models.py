from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, event)
from sqlalchemy.orm import relationship

from .core import Base


class Organisation(Base):
    __tablename__ = "organisations"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, index=True)
    name = Column(String(120))
    type = Column(String(30), index=True)  # airline|airport_operator|gsp|regulator|aai|ota|pacr
    handle = Column(String(60))  # official social handle
    has_crm = Column(Boolean, default=False)


class Airport(Base):
    __tablename__ = "airports"
    id = Column(Integer, primary_key=True)
    code = Column(String(4), unique=True, index=True)
    name = Column(String(120))
    city = Column(String(60))
    state = Column(String(60))
    operator_id = Column(Integer, ForeignKey("organisations.id"))
    major = Column(Boolean, default=False)
    handle = Column(String(60))
    row = Column(Integer, default=0)  # simple grid-map position
    col = Column(Integer, default=0)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    email = Column(String(160), index=True)
    mobile = Column(String(20), index=True)
    country_code = Column(String(6), default="+91")
    password_hash = Column(String(100))
    role = Column(String(20), index=True)  # passenger|redressor|nodal|agent|admin|manager
    user_type = Column(String(30), default="Passenger")
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    level = Column(Integer, default=1)  # redressor L1-L3
    access_type = Column(String(10), default="write")
    designation = Column(String(80))
    backup_email = Column(String(160))
    backup_mobile = Column(String(20))
    status = Column(String(12), default="active")  # active|suspended|disabled
    is_guest = Column(Boolean, default=False)
    consent_save = Column(Boolean, default=True)
    lang = Column(String(8), default="en")
    created_at = Column(DateTime)
    last_login = Column(DateTime)
    failed_logins = Column(Integer, default=0)
    org = relationship("Organisation", lazy="joined")


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    ticket_no = Column(String(20), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    contact_name = Column(String(120))
    contact_mobile = Column(String(20))
    contact_email = Column(String(160))
    category = Column(String(12), index=True)  # flight|airport|ground|govt|other
    subcategory = Column(String(40), index=True)
    description = Column(Text)
    description_en = Column(Text)
    lang = Column(String(10), default="en", index=True)
    airline_org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    airport_id = Column(Integer, ForeignKey("airports.id"), nullable=True, index=True)
    flight_no = Column(String(10))
    pnr = Column(String(10))
    service_request_no = Column(String(40), index=True)
    event_at = Column(DateTime)
    severity = Column(Integer, default=3, index=True)
    severity_reason = Column(String(300))
    status = Column(String(40), index=True)
    source_channel = Column(String(20), default="portal", index=True)  # portal|social_x|social_instagram|whatsapp|email|ivr|cpgrams|letter
    source_type = Column(String(20))
    social_post_id = Column(Integer, nullable=True)
    social_handle = Column(String(60))
    assigned_org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    extra_org_ids = Column(JSON, default=list)
    team = Column(String(60))
    level = Column(Integer, default=1)  # current escalation level: 1..3 staff, 4 nodal
    start_level = Column(Integer, default=1)
    stage = Column(Integer, default=0)  # SLA thresholds crossed
    pacr_escalated = Column(Boolean, default=False)
    queue = Column(String(12), default="redressor", index=True)  # redressor|pacr|committee
    sla_policy_id = Column(Integer, ForeignKey("sla_policies.id"), nullable=True)
    created_at = Column(DateTime, index=True)
    updated_at = Column(DateTime)
    due_at = Column(DateTime)
    sla_start = Column(DateTime)
    first_response_at = Column(DateTime)
    resolved_at = Column(DateTime)
    closed_at = Column(DateTime)
    breached = Column(Boolean, default=False, index=True)
    warned_stage = Column(Integer, default=-1)
    reopen_count = Column(Integer, default=0)
    escalation_count = Column(Integer, default=0)
    transfer_count = Column(Integer, default=0)
    csat = Column(Integer)
    sentiment = Column(Float, default=0.0)
    confidence = Column(Float)
    fcr = Column(Boolean, default=False)
    disputed = Column(Boolean, default=False)
    compliance = Column(JSON)  # last CAR check result
    resolution_text = Column(Text)
    resolution_code = Column(String(40))
    hold_reason = Column(String(300))
    parent_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    related_count = Column(Integer, default=0)
    downgrade_request = Column(JSON)
    extra = Column(JSON, default=dict)  # ticket_amount, block_time_hours, baggage_weight_kg, severity_keywords...
    assigned_org = relationship("Organisation", foreign_keys=[assigned_org_id], lazy="joined")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id], lazy="joined")
    airline = relationship("Organisation", foreign_keys=[airline_org_id], lazy="joined")
    airport = relationship("Airport", lazy="joined")


Index("ix_ticket_open", Ticket.status, Ticket.assigned_org_id)


class TicketEvent(Base):
    """Append-only audit trail for each ticket (immutable: updates/deletes are blocked)."""
    __tablename__ = "ticket_events"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), index=True)
    at = Column(DateTime)
    actor = Column(String(120))
    actor_role = Column(String(20))
    type = Column(String(30))
    from_status = Column(String(40))
    to_status = Column(String(40))
    note = Column(Text)
    data = Column(JSON)


@event.listens_for(TicketEvent, "before_update")
def _no_update(*_):
    raise ValueError("TicketEvent is immutable")


@event.listens_for(TicketEvent, "before_delete")
def _no_delete(*_):
    raise ValueError("TicketEvent is immutable")


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), index=True)
    filename = Column(String(200))
    stored = Column(String(200))
    mime = Column(String(60))
    size = Column(Integer)
    kind = Column(String(12), default="upload")  # upload|evidence
    at = Column(DateTime)


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), index=True)
    rating = Column(Integer)
    confirms = Column(Boolean)
    comment = Column(Text)
    at = Column(DateTime)


class AllocationRule(Base):
    __tablename__ = "allocation_rules"
    id = Column(Integer, primary_key=True)
    keyword = Column(String(80), index=True)
    category = Column(String(12))
    subcategory = Column(String(40))
    target_type = Column(String(30))  # org type to route to
    target_org_code = Column(String(20))  # optional fixed org
    weight = Column(Float, default=1.0)
    active = Column(Boolean, default=True)


class SeverityKeyword(Base):
    __tablename__ = "severity_keywords"
    id = Column(Integer, primary_key=True)
    keyword = Column(String(80), index=True)
    severity = Column(Integer)
    active = Column(Boolean, default=True)


class SlaPolicy(Base):
    __tablename__ = "sla_policies"
    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    category = Column(String(12), nullable=True)
    severity = Column(Integer, nullable=True)
    e1_hours = Column(Float, default=24)  # first TAT; breach -> escalate
    e2_hours = Column(Float, default=72)
    e3_hours = Column(Float, default=96)
    warn_pct = Column(Float, default=0.8)
    active = Column(Boolean, default=True)


class CarRule(Base):
    __tablename__ = "car_rules"
    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True)
    title = Column(String(200))
    subcategory = Column(String(40))
    rule_type = Column(String(30))  # refund_min|compensation_table|baggage_liability|evidence_only
    params = Column(JSON)
    active = Column(Boolean, default=True)


class Config(Base):
    __tablename__ = "config"
    key = Column(String(60), primary_key=True)
    value = Column(JSON)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    channel = Column(String(10))  # sms|email|inapp|whatsapp
    to = Column(String(160))  # stored masked
    subject = Column(String(200))
    body = Column(Text)
    at = Column(DateTime)
    read = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    at = Column(DateTime, index=True)
    actor = Column(String(120))
    action = Column(String(60))
    entity = Column(String(60))
    detail = Column(Text)


class ProductivityLog(Base):
    __tablename__ = "productivity_log"
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("users.id"), index=True)
    day = Column(String(10), index=True)
    shift = Column(String(10))  # A|B|C
    inbound = Column(Integer, default=0)
    outbound = Column(Integer, default=0)
    email = Column(Integer, default=0)  # email / ticket / social
    chat = Column(Integer, default=0)


# ---------------------------------- social / channels ----------------------------------
class SocialUser(Base):
    __tablename__ = "social_users"
    id = Column(Integer, primary_key=True)
    handle = Column(String(60), unique=True, index=True)
    name = Column(String(80))
    color = Column(String(10))
    lang = Column(String(10), default="en")
    bio = Column(String(200))
    is_official = Column(Boolean, default=False)
    org_code = Column(String(20))
    followers = Column(Integer, default=0)


class SocialPost(Base):
    __tablename__ = "social_posts"
    id = Column(Integer, primary_key=True)
    platform = Column(String(10), index=True)  # X|Instagram
    source_type = Column(String(14), index=True)  # post|reply|quote|comment|story_mention|dm
    author_handle = Column(String(60), index=True)
    author_name = Column(String(80))
    text = Column(Text)
    created_at = Column(DateTime, index=True)
    lang = Column(String(10))
    mentions = Column(JSON, default=list)
    hashtags = Column(JSON, default=list)
    media = Column(JSON, default=list)
    location = Column(String(60))
    parent_post_id = Column(Integer, index=True, nullable=True)
    target_handle = Column(String(60))  # DM recipient / account whose post was commented on
    likes = Column(Integer, default=0)
    reposts = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    url = Column(String(200))
    seeded = Column(Boolean, default=False)


class SocialNotification(Base):
    __tablename__ = "social_notifications"
    id = Column(Integer, primary_key=True)
    handle = Column(String(60), index=True)
    kind = Column(String(20))
    text = Column(Text)
    from_handle = Column(String(60))
    post_id = Column(Integer, nullable=True)
    ticket_no = Column(String(20))
    at = Column(DateTime)
    read = Column(Boolean, default=False)


class WatchItem(Base):
    __tablename__ = "watch_items"
    id = Column(Integer, primary_key=True)
    kind = Column(String(10))  # handle|hashtag|keyword
    value = Column(String(80), index=True)
    label = Column(String(80))
    active = Column(Boolean, default=True)


class Draft(Base):
    """A detected item from any channel awaiting agent review (or filtered, with reason)."""
    __tablename__ = "drafts"
    id = Column(Integer, primary_key=True)
    channel = Column(String(20), index=True)  # social_x|social_instagram|whatsapp|email|ivr|cpgrams|letter
    source_type = Column(String(14))
    post_id = Column(Integer, nullable=True, index=True)
    status = Column(String(10), index=True)  # pending|approved|rejected|filtered|grouped
    is_complaint = Column(Boolean, default=True)
    reason = Column(String(200))
    author_handle = Column(String(60))
    author_name = Column(String(80))
    original_text = Column(Text)
    text_en = Column(Text)
    lang = Column(String(10))
    category = Column(String(12))
    subcategory = Column(String(40))
    stakeholder = Column(String(80))
    stakeholder_org_id = Column(Integer, nullable=True)
    airport_id = Column(Integer, nullable=True)
    severity = Column(Integer, default=3)
    severity_reason = Column(String(300))
    sentiment = Column(Float, default=0)
    confidence = Column(Float, default=0)
    entities = Column(JSON, default=dict)
    media_note = Column(String(200))
    timings = Column(JSON, default=list)
    total_ms = Column(Float)
    parent_draft_id = Column(Integer, nullable=True, index=True)
    related_count = Column(Integer, default=0)
    engagement = Column(Integer, default=0)
    viral = Column(Boolean, default=False)
    priority_boost = Column(Boolean, default=False)
    dup_of_ticket_id = Column(Integer, nullable=True)
    dup_reason = Column(String(200))
    ticket_id = Column(Integer, nullable=True)
    ticket_no = Column(String(20))
    reply_text = Column(Text)
    reply_sent = Column(Boolean, default=False)
    handled_by = Column(String(80))
    created_at = Column(DateTime, index=True)
    seeded = Column(Boolean, default=False)
    payload = Column(JSON)  # raw non-social payload


class FlightInfo(Base):
    __tablename__ = "flight_subscriptions"
    id = Column(Integer, primary_key=True)
    flight_no = Column(String(10))
    contact = Column(String(160))
    channel = Column(String(10))
    at = Column(DateTime)
