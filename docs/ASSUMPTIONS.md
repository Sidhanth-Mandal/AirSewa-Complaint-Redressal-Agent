# Assumptions and RFP inconsistencies

Where the RFP contradicts itself the more permissive or user-friendly reading is implemented, behind a configuration flag where practical (Admin → Settings).

## RFP inconsistencies

| # | Inconsistency | Decision |
|---|---|---|
| A-1 | Concurrent users: 500 (some places), 600 (design principles), 50,000 (sizing text). | Prototype is single-node (SQLite). The architecture keeps stateless services behind an SSE/REST API, so the number only affects deployment sizing. No load target is claimed. |
| A-2 | FRS 3.2 rows 16/18: a complaint can be filed only after the TAT breach unless "critical", versus the general model (2.1.1, 2.5.x) where a passenger files immediately. | Immediate filing is the default. Flag `allow_pre_breach_filing` (Admin → Settings). When switched OFF, flight grievances need a "Service Request logged at" time older than the policy TAT unless the severity is S1. |
| A-3 | Technology refresh cycle 1-2 years in one place and 3-5 years in another. | Out of prototype scope (infrastructure). Nothing depends on it. |
| A-4 | Escalation timings "24 hours / 72 hours, etc." and "benchmarks defined by MoCA/AAI". | Configurable SLA policies (`/admin/sla`). Defaults: standard 24/72/96 h, S2 12/36/60 h, S1 4/12/24 h, on-ground 6/24/48 h, government dept 48/96/168 h. These are placeholders for MoCA sign-off. |
| A-5 | FRS 3.3 #12-17 lists six statuses, while 2.5.9 and the lifecycle in the brief add Reopened, Escalated and Closed. | All nine statuses exist. Escalated is set on any escalation and clears when staff pick the ticket up. Closed is set only after passenger confirmation, committee decision, or merge. |
| A-6 | FRS 3.4 #19 itself questions whether every SLA-breach notice is meaningful because grievances are filed only after breach. | Notifications are sent for near-breach and breach events of tickets that are open. |
| A-7 | FRS 3.5 #1 / 3.7 #1 are duplicated rows (bulk assessment appears twice). | Implemented once; traceability lists both. |
| A-8 | Annexure-II (July 2026) lists Twitter, Instagram, Facebook, Outbound, Inbound, YouTube; the requested simulator covers X and Instagram only. | Channel proportions in the seed follow Annexure-II for the social share (about 92% X, 4% Instagram of social posts). Facebook and YouTube are not simulated. |
| A-9 | FRS 3.6 #17 allows redressor to reopen a resolved grievance but the row itself says "need to check". | Not implemented. Only the passenger reopens (max 2) and agents can reinstate wrongful closures. |
| A-10 | RFP 2.5.9 says passengers can reopen up to 2 times but does not say what happens after. | After the second reopen the passenger can only "Dispute", which routes the ticket to the Case Closure Committee / PACR queue. |

## Other assumptions

- **Demo clock**: all SLA, escalation and ageing maths use an application clock (real UTC + admin offset). Social posts and live feed counters use real time. Fast-forwarding does not rewrite history.
- **SLA hold**: the SLA timer keeps running while a ticket is "On Hold - Awaiting passenger inputs" (no pause). Reopening restarts the SLA clock from the reopen time.
- **Escalation levels**: stage 1 (first threshold) moves one level up from the start level (L1→L2, or L2→L3 for S1), stage 2 moves up again, stage 3 reaches the Nodal Officer, and after the last threshold the ticket is also placed in the PACR queue.
- **CAR / DGCA rules** are an illustrative rule base (full refund of the ticket amount for airline cancellation, a block-time compensation table, Rs 350/kg baggage liability). Values are editable at `/admin/sla` and must be validated against current regulations before any real use. Compensation and baggage rules are checked only when a monetary amount is entered; non-monetary resolutions (bag located, meals) need evidence but no amount.
- **Social platforms** are fully simulated. Handles for real organisations (e.g. @IndiGo6E) are only watch-list strings; the "minister" handle is a placeholder (`@CivilAviationMinister`) and is configurable.
- **PII masking**: agents see full contact details; redressors, administrators, managers and all notification logs see masked data. Social handles are masked everywhere except for agents in the draft detail view.
- **Language support**: the UI is fully translated for English and Hindi on the passenger, navigation and form flows. Staff-facing analytics screens are English only; more languages can be added by dropping `messages/<code>.json` and extending `LOCALES`.
- **Retention**: seeded social tickets older than 30 days have no stored post (treated as already purged under the social retention setting).
- **Authentication**: staff use passwords (bcrypt), passengers can use OTP or password. The OTP is the fixed value `123456` in demo mode (`DEMO_MODE=true`).
- **Security**: file uploads are checked for extension, size and magic bytes; SQL is only issued through the ORM (parameterised); the JWT secret is generated locally into `api/.jwt_secret` (git-ignored) unless `JWT_SECRET` is set.
- **Seed data** is synthetic (about 3,000 tickets over 12 months, 20 airports, 8 airlines, AAI + 5 private airport operators, regulators, ground handlers and OTAs). No real passenger data is used.
