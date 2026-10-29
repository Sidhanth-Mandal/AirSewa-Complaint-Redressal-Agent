# 10-minute demo script

Start the app with `npm run dev` (first run installs and seeds; see README), then open <http://localhost:3000>. All passwords are `Demo@1234`; passenger OTP is `123456`. Use two browser windows (or one normal and one private) so you can stay logged in as two roles.

The seed contains story tickets owned by `passenger@demo.in`: delayed refund (IndiGo), lost baggage with medicine (Air India, S1), airport washroom (Delhi), wheelchair assistance (Bengaluru), an SLA-breach ticket (SpiceJet), a disputed closure (Akasa Air, in the Case Closure Committee queue) and a resolved ticket awaiting feedback (Air India Express). The social stories (duplicate tweets from one flight, and a viral wheelchair thread) are waiting in the agent review queue.

## 0:00 - Landing and language (30 s)
1. Home page. Point out the tricolour header, the "Prototype / Simulated" badge and the language switcher. Switch to **हिन्दी** and back.

## 0:30 - Passenger files a grievance (2 min)
2. **Login** → OTP tab → mobile `9000000001` → *Send OTP* (a dev toast shows the simulated SMS and OTP) → *Verify*.
3. *File a grievance*. Category **Flight**. Choose *Air India*, enter any Service Request No. and leave the field: flight number and PNR are auto-fetched (Simulated).
4. Pick a date/time, then type: *"Air India lost my baggage and it has my father's medicine. Urgent help needed."* The live hint shows **S1 Critical** and the matched keyword "medicine". Tick the consent box and submit.
5. The confirmation shows the ticket ID (`AS-2026-…`), "Routed to Air India (L2)" and the severity reason. Open the ticket and show the status timeline and the *Notification log (Simulated SMS / e-mail)* with masked recipients.

## 2:30 - Redressor handles it (1.5 min)
6. In the second window log in as **ai.l2@demo.in** (Air India L2). The new ticket is at the top of the queue (S1 routes to L2 and above). Log in later as `ai.l1a@demo.in` to show L1 does not see it.
7. Open the ticket: status becomes **In-Progress**; contact details are masked. Try **Resolve** with no evidence → blocked. Add evidence "REF-1" and resolve.

## 4:00 - Closure rules and CAR check (1.5 min)
8. As **nodal.6e@demo.in** (IndiGo Nodal Officer) open the *delayed refund* story ticket (`passenger@demo.in` → My grievances → refund). Enter transaction `TXN-9` and amount **5000**: the AI/CAR check **fails** ("less than the CAR-computed refund Rs 8,500"). Re-enter **8500**: resolved.
9. Back as the passenger, on the same ticket choose *Not satisfied* → the ticket reopens (1 of 2). Show "Reopens used". Mention the third reopen is refused and leads to *Dispute*.
10. As **agent1@pacr.demo** open *Closure & committee*: the Akasa Air story ticket sits in the **Case Closure Committee** queue (compliant but disputed). Click *Uphold & close* or *Reinstate*.

## 5:30 - SLA breach and auto-escalation (1.5 min)
11. As **nodal.sg@demo.in** (SpiceJet) open the SLA story ticket (about 20 h old, L1).
12. As **admin@moca.demo** → *Demo clock* → **+6h**. The ticket shows *SLA breached*, escalates **L1→L2** (event in the timeline, new assignee). Jump **+50h** → L3, then **+30h** → Nodal + PACR queue. Reset the clock afterwards.

## 7:00 - MoCA dashboard (1 min)
13. *MoCA dashboard*: KPIs (SLA breach %, FCR, CSAT, reopen rate), category and stakeholder charts, TAT distribution, Pareto, grid map, breach cohorts, live inflow/outflow with ageing. Change filters (airport, channel, priority). Click **PDF / XLSX / CSV** to export. The new ticket appears live (SSE).

## 7:45 - Live social complaint on the split screen (2 min)
14. Open <http://localhost:3000/demo>. Click *Log in as demo agent*.
15. Left: Social Simulator, **X** tab, "Log in as" *Arjun Nair*. Post: *"@IndiGo6E flight 6E 981 DEL-BOM delayed 4 hours, my father's medicine is in the bag and no water. PNR ZK45LM #AirSewa"*.
16. Right: the row animates in within a fraction of a second: **Complaint detected**, platform/source type, masked handle, S1 chip with the reason, category, stakeholder (IndiGo), sentiment, confidence and the pipeline timeline in milliseconds. A red alert toast fires (enable the sound button for the beep). "Last post → draft ticket" shows the end-to-end time at the top.
17. Post a second tweet about flight 6E 981 from *Meera Iyer* (same flight) → it is **grouped** under the first with an "N related posts" counter. Click *+1 same issue* on the original post a few times: the viral threshold raises priority (🔥 VIRAL).
18. Switch the user to *Sunita Devi* and post in Hindi: *"@AAI_Official मेरा सामान एयरपोर्ट पर खो गया और उसमें दवाई थी। कृपया मदद करें"* → translated (Simulated), classified, S1. Post a spam tweet (*"Cheap flights! Use code FLY50 50% off click here @airindia"*) and a praise tweet (*"Thank you @AkasaAir for the smooth flight!"*) → filtered with a visible reason (see *Filtered* tab).
19. Switch to the **Instagram** tab and show the four paths: caption tag (Create), comment under an official post (Feed), story mention, DM (Inbox).

## 9:45 - Approve and acknowledge (45 s)
20. On the PACR side click *Review* on the S1 draft → *Approve → create ticket* (ticket ID appears, SLA timers start). Then *Send reply as @AirSewa_Official*.
21. On the left, switch the simulator user back to *Arjun Nair* → X **Notifications**: the official reply "We have registered your complaint, ticket AS-… Please DM details" is there.

## Optional extras (if time)
- **Replay**: click *Replay demo script* in the simulator header for a hands-free run of 10 scripted complaints (Hindi, Hinglish, spam, praise, wheelchair + a +1 reply, DM and story mention).
- **Other channels**: *Other channels* page → send a WhatsApp message, then an e-mail with the same PNR → cross-channel duplicate is detected; agent confirms the merge.
- **Control room**: log in as `manager@pacr.demo` → PU per agent per shift and the SLA penalty simulation with the 10% cap.
- **Watch list**: *Social watch list* → add a hashtag, post with it in the simulator, and show that it is detected from the next post.
- **Airline CRM (Simulated)**: file a grievance against IndiGo/Air India/Akasa, open `/crm`, press *Resolve in CRM* with amount and transaction ID: status syncs back and the closure rules run.
- **Crisis banner**: Admin → Settings → fog advisory sample → banner on all pages (English/Hindi).
