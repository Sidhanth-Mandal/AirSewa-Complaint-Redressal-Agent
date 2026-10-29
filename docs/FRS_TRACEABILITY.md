# FRS traceability - Annexure-III (3.1 to 3.9)

Status legend: **Implemented** (working end to end in the prototype), **Partial** (works with a stated limitation), **Simulated** (works against a mock adapter, labelled "Simulated" in the UI), **Out of scope** (not built; see README "future scope").
"Where to see it" gives the page or API. Credentials are in the README.

## 3.1 User Registration Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1 | Stakeholder category list (Passenger, AAI, Airline, Airport Operator, BCAS, DGCA, ASG, FTO, Others) | Implemented | `/register` "I am a" |
| 2, 3 | Register with e-mail / mobile | Implemented | `/register` |
| 4 | OTP on e-mail/mobile | Simulated | `/login` OTP tab; OTP `123456` shown in a dev toast |
| 5 | Multi-factor authentication | Partial | OTP for passengers and password reset; staff use password only (no second factor) |
| 6 | Login with registered credentials | Implemented | `/login` Password tab |
| 7, 8 | Guest login with mobile / e-mail | Implemented | `/login` "Continue as guest" |
| 9 | Consent to save data and create account from guest login | Implemented | Guest tab checkbox |
| 10 | Password policy (length, complexity) | Implemented | `POST /auth/register`, pytest `test_otp_guest_login_and_password_policy` |
| 11 | Idle session expiry | Implemented | httpOnly JWT cookie, sliding 30 min (`SESSION_IDLE_MINUTES`) |
| 12 | Reset password via factor authentication | Implemented | `/register?reset=1` ("Forgot password") |
| 13-16 | Username = mobile or e-mail, auto-detect, 10-digit and e-mail validation | Implemented | login/registration forms, `detect_identifier()` |
| 17, 18 | International mobile, country code captured | Implemented | "Country code" field |
| 19 | Administrator creates Nodal Officer account | Implemented | `/admin/users` |
| 20 | Authorisation letter uploaded by administrator | Partial | File name recorded in the audit log; the letter file itself is not stored |
| 21 | Nodal Officer details (e-mail, phone, org, designation, backup delegate) | Implemented | `/admin/users` |
| 22 | Administrator resets Nodal Officer password | Implemented | `/admin/users` "Reset pwd" |
| 23 | Nodal Officer resets default password with factor auth | Implemented | Forgot-password flow works for all roles |
| 24, 25, 26 | Nodal Officer creates staff, resets password, captures details (L1-L3, read/write) | Implemented | `/redressor/staff` |
| 27 | Duplicate phone/e-mail error | Implemented | 409 error shown on the form |
| 28 | Organisation auto-filled | Implemented | `/redressor/staff` |
| 29, 30, 31 | Disable / suspend / release staff | Implemented | `/redressor/staff` |
| 32 | Staff reset default password with factor auth | Implemented | Forgot-password flow |
| 33 | Change access level | Implemented | `/redressor/staff` |
| 34 | Flight status by flight number without login | Simulated | `/track` (mock FlightProvider) |
| 35, 36 | Opt-in updates by notification/SMS/messenger/e-mail | Simulated | `/track` "Notify me"; message appears in the Notification Log only |

## 3.2 Grievance Registration Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1 | Category dropdown: Flight, Airport, On-ground, Government dept, Others | Implemented | `/passenger/new` |
| 2-8 | Flight form mandatory fields: contact, description, date/time, airline, service request no., PNR, flight no. | Implemented | `/passenger/new`; server validation in `grievance.validate_form` |
| 9 | Flight no. and PNR auto-fetched from airline + service request no. | Simulated | "Fetch flight & PNR" (mock booking lookup) |
| 10 | No duplicate grievance for a service request no. | Implemented | 409 error; pytest `test_duplicate_service_request_blocked` |
| 11, 25, 36, 51 | Block submission with mandatory fields missing | Implemented | form + API 422 |
| 12, 13, 26, 27, 37, 38, 52, 53 | PDF/JPG/PNG uploads, 10 MB limit | Implemented | extension + magic-byte check; pytest `test_upload_validation` |
| 14, 28, 39, 54 | Standard TAT shown after category selection | Implemented | blue banner on the form (from SLA policies) |
| 15 | TAT validation against service request logged time | Implemented (flagged) | Only enforced when `allow_pre_breach_filing` is OFF |
| 16, 18 | File only after TAT breach, except critical | Implemented (flagged) | Contradicts the rest of the RFP; default is permissive. See ASSUMPTIONS A-2 |
| 17, 29, 40, 55 | "Critical" tag from keywords in description | Implemented | live "Detected: S1 Critical" hint on the form; severity matrix |
| 19, 30, 41, 56 | Privacy-notice consent checkbox | Implemented | form; API rejects without consent |
| 20, 31, 42, 57 | Unique ticket ID | Implemented | `AS-2026-000123` format |
| 21-24 | Airport form mandatory fields | Implemented | `/passenger/new` (Airport category) |
| 32-35 | On-ground form mandatory fields | Implemented | `/passenger/new` |
| 43-50 | Government dept form (optional airport, PNR, flight no., passport no.) | Partial | Airport/PNR/flight optional and accepted via text; no dedicated passport-number field |
| 58-61 | "Others" category form | Implemented | `/passenger/new` (Others) |
| 62, 63 | Complainant submits additional information when asked | Implemented | ticket page, "Provide requested information" |
| 64, 65 | View status and resolution trail | Implemented | `/tickets/<id>` timeline |
| 66-68 | Feedback on resolution, redressor staff, AirSewa operator | Partial | Resolution rating + comment captured; separate staff/operator ratings not split |
| 69 onward (reopen, escalate) | Reopen (max 2), escalate | Implemented | ticket page; pytest `test_reopen_at_most_twice_then_dispute` |

## 3.3 Ticket Allocation Engine

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1 | Record grievance source (portal, e-mail, call, social, CPGRAMS) | Implemented | `source_channel` + `source_type` on every ticket |
| 2-5 | Assign to Airline / Airport / Ground Service Provider / Regulator by category | Implemented | `allocation.route()`; test `test_portal_ticket_classified_routed_and_visible` |
| 6 | Severity labelling from keywords | Implemented | `/admin/rules` severity matrix |
| 7 | Revised TAT for S1 / S2 | Implemented | SLA policies "Critical (S1)", "High (S2)" |
| 8, 9 | S1 to L2+, S2-S4 to L1 | Implemented | tests in `test_engines.py`, `test_acceptance.py` |
| 10, 11 | Airlines configure sub-category auto-routing / SPOCs | Partial | Rule editor routes by keyword to an organisation; per-airline self-service not built |
| 12-17 | Status lifecycle (Under Assessment, Assigned, In-Progress, On Hold, Provisionally Resolved, Resolved) | Implemented | state machine in `grievance.TRANSITIONS`; In-Progress is set when redressor opens the ticket |
| 18 | Preserve event log (routing, rerouting, resolution, staff, comments) | Implemented | immutable `ticket_events`; update/delete blocked |
| 19 | Detect language and auto-translate to English | Simulated | mock dictionary translator (Hindi, Hinglish) |
| 20 | Flag duplicates across channels | Implemented | `/agent/channels`, social pipeline |
| 21-31 | Ticket view shows timestamp, ID, severity, reason, sub-category, description, assignee org/team/staff, escalation level, SLA policy | Implemented | `/tickets/<id>` |
| 32, 33 | L2+ may override severity, upgrade only | Implemented | pytest `test_severity_override_rules` |
| 34, 35 | Downgrade needs L3 / Nodal approval | Implemented | ticket page "Severity override" |
| 36, 37 | Agent can upgrade and downgrade | Implemented | agent actions |
| 38 | Add additional redressors | Implemented | ticket page "Add redressor" |

## 3.4 Communication Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1 | OTP for login / guest / password change | Simulated | dev toast + Notification Log |
| 2, 3 | Notify on account registration / password change | Simulated | `/admin/audit` Notification log |
| 4-7 | Notify on submission (with ID), On Hold, Provisionally Resolved, Resolved | Simulated | ticket page "Notification log" |
| 8 | Rich text with variables | Partial | Plain templated text with variables |
| 9 | PII masked in communications | Implemented | recipients stored masked (`mask_mobile`, `mask_email`) |
| 10-13 | User notification preferences (mobile, e-mail, both, none) | Out of scope | Sent to every available contact |
| 14, 15 | Notify Nodal Officer / staff on account creation | Partial | Simulated e-mail written for created users |
| 16-18 | Daily summary reports by e-mail | Out of scope | Exports are on demand (`/dashboard/export`) |
| 19 | Notify Nodal Officer on unattended grievances beyond SLA | Implemented | near-breach and breach events, in-app notifications |
| 20-22 | Notify L2 / L3 / Nodal on escalation | Implemented | in-app notification to the new assignee |
| 23, 24 | Notify on second reopen | Partial | Second reopen is recorded in the event log; no dedicated alert |
| 25 | Agent triggers escalation notification | Implemented | agent "Escalate +1 level" |
| 26, 27 | Agent / staff ask user for additional information | Implemented | "Hold - need passenger input" (notifies the passenger) |
| 28-31 | Administrator views and preserves notification logs | Implemented | `/admin/audit` (Notification log) |
| 32-35 | Manuals / videos, chatbot and feedback for tech support | Partial | Rule-based chatbot (EN/HI) on every page; manuals/videos not built |

## 3.5 AirSewa Agent Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1, 2 | Bulk assessment, bulk severity override | Implemented | `/agent/tickets` |
| 3-5 | Bulk escalate L1→L2, L2→L3, L3→Nodal | Implemented | `/agent/tickets` "Escalate +1 level"; pytest `test_bulk_escalate_and_search_by_contact` |
| 6-9 | Merge duplicates, parent/child labels, related-grievance links | Implemented | ticket page "Merge as child"; `children` list on the parent |
| 10, 11 | Override auto-assignment and severity | Implemented | ticket page agent actions |
| 12, 13 | Workload per redressor staff / redressor | Implemented | `/redressor/performance` (nodal), officer pendency in `/admin` |
| 14-17 | Filter by type, sub-category, date/time, age | Implemented | `/agent/tickets` filters + sorting |
| 18 | Change status | Partial | Via reverify/reinstate and committee decisions; no free status picker |
| 19 | Add information after speaking to user | Implemented | "comment" action |
| 20 | Interactive dashboard | Implemented | `/admin` |
| 21-26 | Download history / lists by status, age, severity, category, redressor | Implemented | CSV / XLSX / PDF with the same filters (`/dashboard/export`) |
| 27 | Escalate L1→L2, L2→L3 on triage | Implemented | ticket page |

## 3.6 Redressor Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1-3 | Queue by type; L1 sees S2-S4, L2/L3/Nodal see S1-S4 | Implemented | `/redressor`; pytest checks L1 does not see S1 |
| 4-7, 28-31 | Search by ID, contact, PNR, service request no. | Implemented | queue search box |
| 8-12, 32-37 | Filter by type, sub-category, age, status, date, staff | Partial | Type, status, priority, SLA, sort-by-age; sub-category and staff-name filters not exposed |
| 13-15 | Set Provisionally Resolved / Resolved / On Hold | Implemented | ticket page |
| 16 | Trigger notification to seek inputs | Implemented | Hold action |
| 17 | Redressor reopen (RFP itself unsure) | Out of scope | See ASSUMPTIONS A-9 |
| 18, 19 | Proof required before Provisionally Resolved / Resolved | Implemented | transaction ID / reference / evidence upload; pytest `test_resolution_requires_evidence_and_car_compliance` |
| 20 | L2/L3/Nodal reassign | Implemented | "Divert" and "Assign to staff" |
| 21-25 | Nodal downloads by status, age, severity, category, redressor | Implemented | `/admin` export is available to Nodal (own organisation only) |
| 26 | Staff escalate L1→L2→L3 | Implemented | ticket page |
| 27 | Nodal views workload per staff | Implemented | `/redressor/performance` |
| 38, 39 | Nodal views staff feedback and average | Implemented | `/redressor/performance` (CSAT per staff) |

## 3.7 Redressor Administrator Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1-11, 18, 19 | Bulk assessment / actions, merge, parent-child, overrides | Implemented | `/agent/tickets` and ticket page (administrator has the same actions) |
| 12-17 | Workload and monitoring views | Implemented | `/admin` (officer/agency pendency, filters) |
| 20-26 | Dashboard and downloads | Implemented | `/admin` |
| 27 | Escalate on triage | Implemented | ticket page |
| 28, 29 | Feedback of redressor staff and AirSewa Operator | Partial | Staff CSAT shown; AirSewa operator (agent) feedback not captured |
| 30-32 | Monitor first response time, response time, reopen statistics | Implemented | `/admin` KPIs; fields `first_response_at`, `reopen_count` |
| 33, 34 | API integration; administrator solely controls API key | Simulated | `/admin/api` (keys issued only by admin, hashed, rate-limited), OpenAPI at `:8000/docs` |

## 3.8 SLA & Escalation Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1 | Multiple SLA policies in parallel | Implemented | `/admin/sla` |
| 2 | Auto-escalation L1→L2→L3 on breach | Implemented | `/admin/clock` fast-forward; pytest `test_demo_clock_escalates_l1_l2_l3_nodal` |
| 3 | Notify L3 and Nodal when approaching threshold | Implemented | near-breach event + in-app notifications |
| 4, 5 | Record first response time and response time | Implemented | `first_response_at`; SLA events |
| 6 | Record reopening statistics | Implemented | `reopen_count`, dashboard reopen rate and reasons |
| 7 | SLAs reconfigurable | Implemented | `/admin/sla`, `/admin/car-rules` |
| 8 | Resolution per rules for grievance type | Implemented | CAR rule base per sub-category |
| 9 | Refund ≥ CAR-computed refund | Implemented | pytest `test_refund_below_car_amount_fails` (rule values are illustrative) |
| 10, 11 | Quality of resolution assessment and rating of redressor | Partial | Passenger rating (CSAT) per redressor/airline in dashboards; no separate quality score |

## 3.9 MoCA Dashboard Module

| Rows | Requirement (short) | Status | Where to see it |
|---|---|---|---|
| 1 | Agent bulk assessment | Implemented | `/agent/tickets` |
| 2 (second "1") | MoCA views all related grievances under a parent | Implemented | parent ticket page, `children` and "N related posts" |
| RFP 2.5.13 widgets (1-48) | Category, stakeholder, trends, TAT, pendency, escalation, FCR, CSAT, sentiment, Pareto, map, cohorts, live queue, filters | Implemented | `/admin` tabs; see README mapping. Predictive widgets and the what-if slider are Simulated |

> Rows inside a theme that share one status are grouped; no row was left unassessed within the sections read in full (3.1, 3.3-3.9 and the first 57 rows of 3.2). In 3.2 the rows 58-61 and 69+ are grouped by theme because they repeat the earlier patterns.
