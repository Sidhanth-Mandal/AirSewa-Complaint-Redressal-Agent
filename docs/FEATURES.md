# AirSewa 3.0 + PACR: Feature Guide

This guide walks through every screen of the prototype with a screenshot of the running app. Screenshots were captured on 29 Oct 2026 from a live local instance using synthetic data (about 3,000 tickets and 300 simulated social posts). All external systems (SMS, e-mail, X, Instagram, WhatsApp, CPGRAMS, flight data, airline CRMs) are simulated and labelled **Simulated** in the UI.

Demo password for all accounts: `Demo@1234`. Passenger OTP: `123456`. See `README.md` for the full account list and `DEMO_SCRIPT.md` for a 10-minute walkthrough.

To regenerate the screenshots with the app running: `cd e2e && node shots.mjs` (then `node shots2.mjs` for the long pages).

## Contents

1. [Public pages](#1-public-pages)
2. [Passenger portal](#2-passenger-portal)
3. [Redressor and Nodal Officer console](#3-redressor-and-nodal-officer-console)
4. [AirSewa Agent (PACR) console](#4-airsewa-agent-pacr-console)
5. [Control Room Manager](#5-control-room-manager)
6. [MoCA / AAI Admin dashboard](#6-moca--aai-admin-dashboard)
7. [Admin configuration](#7-admin-configuration)
8. [Social simulator and live demo](#8-social-simulator-and-live-demo)
9. [Airline CRM webhook](#9-airline-crm-webhook)

---

## 1. Public pages

### 1.1 Home and portal chooser (`/`)
![Home](screenshots/01-home.png)

The landing page offers three quick actions (File a grievance, Track a flight, Track a grievance) and a card for each role: Passenger, Airline/Airport/Regulator staff, AirSewa Agent, MoCA/AAI Dashboard, Control Room Manager, and the Split-screen demo. A purple "Prototype - all external systems are simulated" banner and an English/Hindi language switch are on every page.

### 1.2 Login (`/login`)
![Login](screenshots/02-login.png)

Two login modes: mobile or e-mail with OTP (passengers) and password (staff and agents). The login page also has one-click fill buttons for the main demo accounts.

![OTP step](screenshots/02b-login-otp.png)

The OTP step. The OTP is simulated and shown in a dev toast.

### 1.3 Registration (`/register`)
![Register](screenshots/03-register.png)

Registration needs a role, full name, country code, mobile number or e-mail, and a password (at least 8 characters with upper-case, lower-case, digit and special character). "Send OTP" is simulated. Passengers can also continue as a guest, with a consent prompt to save details.

### 1.4 Track a flight or grievance (`/track`, no login)
![Track](screenshots/04-track-flight.png)

- **Flight status** takes a flight number and returns mock flight data.
- **Grievance status** takes a ticket ID and the last 4 digits of the registered mobile number, so a ticket can be checked without logging in.

### 1.5 Chatbot (on every page)
![Chatbot](screenshots/09-chatbot.png)

The round button at bottom-left opens a rule-based English/Hindi assistant. It answers FAQs (here, lost baggage guidance), offers quick actions (Track flight, File a grievance, Track ticket) and can hand off to an agent ("Talk to an agent"). It is labelled "Rule-based"; an LLM provider can be configured optionally.

---

## 2. Passenger portal

### 2.1 My grievances (`/passenger`)
![Passenger dashboard](screenshots/05-passenger-dashboard.png)

A card for each of the passenger's tickets, with ticket ID, status badge, description, priority badge (S1 Critical, S2 High, and so on), category, stakeholder and age. Navigation: My grievances, File a grievance, Track flight / ticket.

### 2.2 File a grievance (`/passenger/new`)
![Grievance form](screenshots/06-grievance-form.png)

- Five grievance types (FRS categories), each with its own mandatory fields. The response time for the chosen category is shown up front (24 h standard, 4 h for critical).
- Contact details are prefilled for logged-in users.
- **Fetch flight & PNR** looks up flight data (simulated).
- As the passenger types, the allocation engine shows a live **Detected** banner with the category and severity. Here "medicine" triggers **S1 Critical**, which is fast-tracked.
- Supporting documents: PDF, JPG or PNG, up to 10 MB each. Type and size are validated, including magic bytes.
- A privacy consent checkbox is required before submitting.

### 2.3 Submission confirmation
![Submitted](screenshots/07-grievance-submitted.png)

The passenger gets a unique ticket ID, the organisation and level it was routed to (Air India, L2), the priority with the matched reason, and the expected response time. A confirmation is sent by simulated SMS and e-mail.

### 2.4 Ticket view and tracking (`/tickets/[id]`)
![Passenger ticket view](screenshots/08-ticket-passenger-view.png)

The ticket page shows the status timeline from the immutable event log, the SLA deadline and the notification history. Passengers can add information when the ticket is On Hold, escalate, give feedback, **reopen** (maximum 2 times) and **dispute** a closure.

---

## 3. Redressor and Nodal Officer console

Redressors (L1, L2, L3) work the tickets of their own organisation. L1 sees S2-S4 tickets. L2 and above also see S1 tickets.

### 3.1 Queue (`/redressor`)
![Redressor queue](screenshots/10-redressor-queue.png)

Summary tiles show open tickets, critical open, SLA breached, resolved and average TAT. The queue has search by ID, PNR or text, and filters for status, priority, category and SLA state. It can be sorted by priority. Rows carry badges such as "SLA breach".

### 3.2 Ticket detail and actions (`/tickets/[id]`)
![Ticket detail](screenshots/11-ticket-detail-staff.png)

- Grievance details: category, escalation level, airline, flight, PNR, masked contact details, AI confidence and first response time.
- **Why this priority** explains the severity decision (here, matched keyword 'medicine').
- **SLA policy** panel with the deadline and time remaining.
- Status timeline: Under Assessment → Assigned → In-Progress → Provisionally Resolved → Resolved → Closed.
- Notification log of simulated SMS, e-mail and in-app messages.
- **Redressor actions**: add note, hold for passenger input, escalate.
- **Resolve** requires evidence (details, transaction reference, amount or an uploaded file). The CAR rule that applies (for example baggage liability) is shown, and the "Remedy complete" checkbox decides between Resolved and Provisionally Resolved.
- **Divert** or add a redressor, and **severity override** (an upgrade is immediate; a downgrade needs L3/Nodal approval).

### 3.3 Performance (`/redressor/performance`)
![Redressor performance](screenshots/12-redressor-performance.png)

Personal scorecard: assigned, open, resolved, average TAT, SLA breached, breach %, CSAT and reopened.

### 3.4 Nodal Officer queue (`/redressor`)
![Nodal queue](screenshots/13-nodal-queue.png)

The Nodal Officer sees the whole organisation's tickets, including escalated ones.

### 3.5 Staff accounts (`/redressor/staff`)
![Staff accounts](screenshots/14-nodal-staff.png)

The Nodal Officer creates redressor accounts (name, e-mail, phone, designation, access level L1-L3, read or write access). The Team table lets the Nodal Officer change a level, suspend, disable (exit) or reset a password.

---

## 4. AirSewa Agent (PACR) console

Agents handle multi-channel and social complaints, override decisions and run the committee queue.

### 4.1 Review queue and live social feed
![Agent review queue](screenshots/15-agent-home.png)
![Live social feed](screenshots/17-agent-social-feed.png)

Complaints detected from social posts arrive as drafts for the agent. Each row shows:

- platform, masked handle, severity badge, category, the stakeholder it routes to, sentiment, language and a confidence bar;
- **pipeline timings** in milliseconds: received → filtered → translated → classified → de-duplicated → draft created;
- **Viral** and "N related posts" markers, plus grouping under a parent ticket for duplicates.

The agent can approve, edit or reject. Rejecting requires a reason, and approving creates a ticket and an acknowledgment reply in the fake social app. A "Filtered (with reason)" tab shows what the relevance filter dropped (spam, praise and similar). S1 posts raise an alert toast and an optional alert sound.

### 4.2 All tickets (`/agent/tickets`)
![Agent all tickets](screenshots/16-agent-tickets.png)

A cross-organisation search over all tickets with bulk select. It supports severity override, reassignment, reclassifying, merging duplicates as parent and child, and re-verifying closures. Rows show SLA breach and PACR badges.

### 4.3 Other channels (`/agent/channels`)
![Channels](screenshots/18-agent-channels.png)

Simulated WhatsApp, e-mail, IVR transcript, CPGRAMS and scanned physical letter inputs feed the same detection pipeline. Sending the same PNR on WhatsApp and then e-mail shows cross-channel duplicate detection in the "Resulting drafts" panel.

### 4.4 Closure and committee (`/agent/closure`)
![Closure and committee](screenshots/19-agent-closure-committee.png)

Three tabs: **Committee queue** (disputed cases where the passenger disagreed even though the CAR check passed, or the reopen limit was reached), **Escalated to PACR (SLA)** and **Resolved - to verify**. The example ticket is Resolved, reopened once and disputed.

---

## 5. Control Room Manager

### 5.1 Seat and shift productivity (`/manager`)
![Control room](screenshots/20-control-room.png)

Implements the RFP 2.28 productivity and penalty model. Productivity Units (PU) are inbound call 1, outbound call 1, e-mail/ticket/social response 0.5, and chat 0.75. The target is 60 PU per operator per shift. Penalty slabs run from no penalty up to ₹1,500 per short shift. The monthly cap is 10% of the invoice.

You can edit the PU target, window and monthly invoice, and the tiles update. The page shows gross penalty, the cap, payable penalty and agents below target, a chart of average PU per agent, a penalty-by-agent table, and a shift-level table. It is marked as a penalty simulation.

---

## 6. MoCA / AAI Admin dashboard

### 6.1 Overview (`/admin`)
![Dashboard overview](screenshots/21-dashboard-overview.png)

- Export as CSV, XLSX or PDF, plus Refresh. Live updates arrive over SSE.
- Filters: period, airport, channel, category, priority, status, stakeholder and language.
- 12 KPI tiles: total, pending, resolved, reopened, SLA breach, escalation rate, FCR, CSAT, average TAT, sentiment, transfer rate, committee/PACR.
- Charts: category-wise complaints, daily trend, monthly volume with growth rate, status mix, the stakeholder-wise table (total, pending, resolved, breach %, average TAT), priority mix and the top 15 subcategories.

### 6.2 SLA & performance
![Dashboard SLA](screenshots/22-dashboard-sla.png)

TAT distribution, early/within-TAT/delayed split, breach % by stakeholder, volume vs SLA attainment, Pareto charts (by volume and by breaches), escalations by level, officer-wise pendency and an airline response-time comparison.

### 6.3 Geography
![Dashboard geography](screenshots/23-dashboard-geography.png)

A schematic grid map of airports coloured by grievance volume. A red border marks an SLA breach rate above 30%. A state-wise table shows grievances and breach %.

### 6.4 Social Media Pulse
![Dashboard social](screenshots/24-dashboard-social.png)

Complaints in 30 days, filtered posts and viral threads, volume by platform and source type, a sentiment trend, top airlines and airports by complaints, and trending hashtags.

### 6.5 Predictive
![Dashboard predictive](screenshots/25-dashboard-predictive.png)

A weekly ticket volume forecast (4-week moving average with a seasonal index), SLA-breach risk by category (High, Medium), and a what-if slider for the number of PACR seats. The slider estimates PU per seat, penalty and seat cost, using an illustrative model.

The remaining dashboard tabs (Live queue, Cohorts & watchlist, Quality & channels) are in the app but not shown here.

---

## 7. Admin configuration

### 7.1 Allocation rules and severity matrix (`/admin/rules`)
![Rules](screenshots/26-admin-rules.png)

The **Try the engine** box classifies any text. The tabs list the keyword → category → redressor rules (117) and the severity matrix S1-S4 (63). Rules can be added, edited or removed at runtime with no code change, and the same engine serves the portal, social posts and every PACR channel.

### 7.2 SLA policies and CAR rule base (`/admin/sla`)
![SLA and CAR](screenshots/27-admin-sla.png)

Multiple SLA policies (Critical S1, High S2, On-ground assistance, Government dept, Standard) define the hours before escalation L1→L2, L2→L3 and L3→Nodal, and a warning fraction. Below them is the CAR/DGCA compliance rule base (refund, denied boarding, delay compensation, baggage liability) as editable JSON parameters. The values are marked illustrative.

### 7.3 Social watch list (`/admin/watchlist`)
![Watch list](screenshots/28-admin-watchlist.png)

Monitored handles, hashtags and keywords for the simulated X and Instagram. Each entry can be paused or removed. Edits apply to the next post.

### 7.4 Demo clock (`/admin/clock`)
![Demo clock](screenshots/29-admin-clock.png)

Fast-forward the application clock by 1, 6, 12, 24, 48 or 72 hours, or a custom number of hours. SLA breach flags, near-breach warnings and automatic escalation (L1→L2→L3→Nodal→PACR) run right after each jump.

### 7.5 Users and masters (`/admin/users`)
![Users](screenshots/30-admin-users.png)

Create accounts for any role (with organisation, designation and backup delegate). The table lists staff with their organisation, role and level, and offers suspend, disable and reset-password actions. A second tab manages organisations and airports.

### 7.6 Settings (`/admin/settings`)
![Settings](screenshots/31-admin-settings.png)

- Business-rule flags: allow filing before TAT breach, and maximum reopens per ticket (2).
- Crisis banner, for example a fog advisory in English and Hindi, shown on every page.
- Social listening: minister handle, viral threshold, duplicate window and text-similarity threshold.
- Data retention, with **Apply retention now** and **Purge social data**.
- PACR commercials: monthly invoice and PU target.

### 7.7 Audit and notification log (`/admin/audit`)
![Audit](screenshots/32-admin-audit.png)

An append-only audit log (logins, ticket create and dispute, draft approve and reject) plus a second tab with the simulated SMS and e-mail log.

### 7.8 API sandbox (`/admin/api`)
![API sandbox](screenshots/33-admin-api-sandbox.png)

Issue API keys for integrations, try `GET /v1/tickets/{id}`, and view usage per key. The API has a rate limit of 30 requests per minute per key, and OpenAPI docs are at `localhost:8000/docs`.

---

## 8. Social simulator and live demo

### 8.1 Social Simulator (`/simulator`)
![Simulator](screenshots/34-simulator.png)

Two fake apps, X-style and Instagram-style, with no brand assets. Choose a persona, post a complaint that mentions a watched handle, and use "+1 same issue" to add duplicates. **Replay demo script** plays a scripted set of posts.

### 8.2 Split-screen demo (`/demo`)
![Demo](screenshots/35-demo-split-screen.png)

Post on the left and watch PACR detect it on the right. This capture shows an S1 Critical post detected, classified and grouped under an existing ticket, with the pipeline timings per stage. The header chip shows the last post-to-draft time (7 ms in this run). Features on screen: live counters, an S1 alert sound toggle, Viral badges and related-post counts.

---

## 9. Airline CRM webhook

### 9.1 Fake airline CRM (`/crm`)
![CRM](screenshots/36-crm-webhook.png)

Simulates an airline's own CRM receiving AirSewa's call-to-action webhook. For each ticket the CRM user can **Acknowledge** or **Resolve in CRM** (amount, transaction ID, note). The status syncs back to AirSewa and goes through the normal closure rules (evidence and CAR check).

---

## Notes

- The Next.js dev badge was hidden for the screenshots. Nothing else in the UI was changed.
- Ticket IDs, timestamps and counts in the screenshots come from the seed data and the run on 29 Oct 2026, so they will differ in a fresh run.
- The Hindi UI, the Live queue / Cohorts / Quality dashboard tabs, bulk actions, severity-downgrade approval and the OTP guest flow exist in the app but have no screenshots here.
