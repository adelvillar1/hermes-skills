# Compliance Decision Tables

Fast lookup. Load this when you need a quick answer; load the deeper reference
for the reasoning behind it.

## Applicability test — COPPA, in order

| # | Question | If YES | If NO |
|---|---|---|---|
| 1 | Commercial service, interstate commerce, collects/maintains PI from or about users? | Operator — continue | Not an operator; COPPA stops here |
| 2 | Directed to children (subject matter, visuals, audience, intended audience)? | In scope — go to 5 | Continue |
| 3 | Mixed audience? | Must age-screen neutrally before collecting beyond §312.5(c) purposes | Continue |
| 4 | **Actual knowledge** of collecting/maintaining PI **from** a child? | In scope — go to 5 | **Not in scope** (security/retention still good practice) |
| 5 | Data collected **from** the child, or **about** the child from an adult/school? | Consent required unless an exception applies | Argue prongs 2/4, not the data type |
| 6 | School authorized the collection for an educational purpose, no commercial use? | School-consent route (guidance) | Verifiable parental consent required |

## Where the answer comes from, by question asked

| Someone asks | Regime | Who owes the duty | Load |
|---|---|---|---|
| "Are you COPPA compliant?" | COPPA | **Vendor** | `coppa-framework.md` |
| "Are you CIPA compliant?" | CIPA | **School** (E-rate applicant) | `cipa-requirements.md` |
| "Are you FERPA compliant?" | FERPA | **School**; vendor via contract | `ferpa-interface.md` |
| "Do you need parental consent?" | COPPA §312.5 | Vendor, if in scope | `coppa-framework.md` |
| "Can the school consent for us?" | COPPA (guidance) | School, with conditions | `coppa-2025-amendments.md` |
| "What's your retention policy?" | COPPA §312.10 (+ contract) | Vendor | `the school-dismissal SaaS-assessment.md` |
| "Do you sell student data?" | FERPA contract / COPPA §312.4 | Vendor | `ferpa-interface.md` |
| "What happens on breach?" | Contract + state law | Vendor to school | `ferpa-interface.md` |

## the school-dismissal SaaS — verdict summary

| Regime | Applies? | Why | Residual work |
|---|---|---|---|
| **COPPA** | Almost certainly **no** | Not child-directed (staff-only users); no actual knowledge of collecting PI **from** a child — records entered by school staff | Written retention policy; online notice; verify Umami |
| **CIPA** | **No direct duty** | Binds schools/libraries as E-rate applicants | Answer district questionnaires by mapping platform controls to their duties |
| **FERPA** | **No direct duty** | Binds the school; vendor reached via school-official exception | DPA with direct-control + purpose-limitation terms |

## Feature-change triggers — when to re-run this analysis

Re-open the assessment if a change does any of the following. Each one can flip
a prong.

| Change | Risk it introduces |
|---|---|
| **Any student- or parent-facing login** | Creates child users → prong (b) actual knowledge, likely prong (a) too |
| **Parent/guardian accounts** | Introduces adult PI at scale; new notice obligations |
| **Photo, video, or audio capture** | §312.2(8) / (10) — image and voice are PI; biometrics are PI |
| **Geolocation** | §312.2(9) — PI at street/city granularity |
| **Student-facing messaging or chat** | Child-directed features; CIPA minors'-communications theme |
| **Public/unauthenticated display URL** | Turns an internal board into a public disclosure of minor names |
| **Advertising, profiling, or data sharing** | Destroys the "no commercial purpose" condition of the school-consent route |
| **New analytics or session-recording script** | Persistent identifiers; §312.8(c) third-party assurances; §312.4(d)(2) disclosure |
| **Third-party subprocessors** | §312.8(c) written assurances; DPA flow-down |
| **New optional student field** | Widens the dataset beyond the documented four fields |
| **Retention change** | Must match the written §312.10 policy |

## District questionnaire — stock answers

| Question | Answer shape |
|---|---|
| Are you COPPA compliant? | Our service is not directed to children and has no child users; all records are entered by school staff. We operate to COPPA's security and data-minimization standards regardless. |
| Are you CIPA compliant? | CIPA applies to schools and libraries as E-rate applicants, not vendors. Here is how our controls support your internet safety policy: [access control, audit trail, data minimization, no student-facing internet access]. |
| Are you FERPA compliant? | FERPA governs schools; we act as a school official under your direction, under contract terms establishing direct control and purpose limitation. |
| Do you sell student data? | No. No advertising, no profiling, no data sales — documented and contractual. |
| How long do you keep data? | Queue resets daily; roster retained while active; audit trail retained as the custody record. [Cite the written retention policy once it exists.] |
| Can we get data deleted? | Yes — on termination, per contract. Note: current in-app delete is a deactivation; align the answer with the retention policy. |
| Do you use third-party analytics? | Yes — Umami, cookieless, no personal data, no cross-site tracking. |
| Can you impersonate our users? | Yes, for support: 60-minute window, logged in your audit trail as `impersonation_started`, blocked from platform admin while active. |

## Date and citation cheat sheet

| Item | Value |
|---|---|
| COPPA statute | 15 U.S.C. 6501-6506 |
| COPPA Rule | 16 CFR Part 312 |
| 2025 amendments | 90 FR 16918, Apr. 22, 2025; RIN 3084-AB20 |
| Effective date | June 23, 2025 |
| Compliance deadline | April 22, 2026 (except §312.11(d)(1), (d)(4), (g)) |
| CIPA enacted | 2000; FCC rules 2001, updated 2011 |
| FERPA school official | 34 CFR 99.31(a)(1); 99.31(a)(1)(i)(B); 99.33(a) |
| COPPA "child" | Under 13 |
| CIPA "minor" | Under 17 |
| FTC ed-tech guidance | Schools may consent for parents — educational purpose only, no commercial purpose |
| Ed-tech codification | **Not finalized** — deferred pending possible DOE FERPA rulemaking |
