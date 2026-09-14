---
name: cipa-coppa-school-platform
description: Navigate CIPA and COPPA duties for a school platform.
---

# CIPA & COPPA for a School Platform

Expert working knowledge of two different federal regimes that both get waved at
K-12 vendors, plus the analysis of how they land on **the school-dismissal SaaS** specifically.
It is not legal advice; it is a structured map so you can reason precisely,
answer district questionnaires, and know which obligations are actually
the platform's versus the school's.

The single most important distinction, and the one most people get wrong:

- **COPPA regulates the operator** (the vendor). It creates duties that can fall
on the school-dismissal SaaS directly.
- **CIPA regulates the school or library** as a condition of E-rate funding. It
creates **no direct duty on a vendor.** A district asking "are you CIPA
compliant?" is asking the wrong question; the correct answer explains what
CIPA requires of *them* and what the platform does or does not do that touches
those requirements.

Both regimes sit next to **FERPA**, which governs the school's handling of
education records and is the framework districts actually operate under day to
day. FERPA has no direct vendor liability either — it flows through the school
via the school-official exception and the vendor's contract.

## When to Use

- "Are we COPPA compliant?" / "Does COPPA apply to us?"
- "A district sent a security questionnaire asking about CIPA."
- "Do we need verifiable parental consent?"
- "Can the school consent on behalf of parents?"
- "What's our data retention policy?" / "How long do we keep student data?"
- "Is the display board a COPPA problem?" / "Is Umami analytics a COPPA problem?"
- Writing or revising `docs/SECURITY-PRIVACY.md`, a DPA, or a trust page.
- Adding any feature that collects a new field about a student.

## Prerequisites

None — this is a knowledge skill. All claims below are grounded in the source
documents listed under Verification; re-check the CFR with `web_extract`
before relying on any citation for an external commitment, because the COPPA
Rule was amended in 2025 and ed-tech provisions are in flux.

## How to Run

1. Read this file for the core mental models and the applicability test.
2. Load the specific reference you need with `skill loader`:
   `skill loader (name="cipa-coppa-school-platform", file_path="references/<file>")`
   re-verify the cited `file:line` against the current tree with
   `read_file`/`search_files` before quoting it to anyone.

## Quick Reference

| Question | Answer in one line | Detail |
|---|---|---|
| Who does COPPA regulate? | The **operator** — commercial website/service collecting PI from kids | `coppa-framework.md` |
| Does CIPA apply to the school-dismissal SaaS? | **No direct duty.** CIPA binds schools/libraries seeking E-rate funds | `cipa-requirements.md` |
| Can a school consent for parents? | Yes, per FTC guidance — school-authorized educational purpose, no commercial use | `coppa-framework.md`, `ferpa-interface.md` |
| Was that codified in the 2025 Rule? | **No** — FTC declined to finalize ed-tech/school provisions | `coppa-2025-amendments.md` |
| Compliance deadline for 2025 Rule | **April 22, 2026** | `coppa-2025-amendments.md` |

## Core Mental Models

### 1. COPPA's applicability is a two-prong test — and you need both to miss

COPPA §312.3 reaches an operator if **either**:

- (a) the service is a "website or online service directed to children" —
  judged by subject matter, visual content, animated characters, child-oriented
  activities and incentives, age of models, child celebrities, language,
  whether advertising is child-directed, plus empirical audience composition
  and intended audience; **or**
- (b) the operator has **actual knowledge** it is collecting or maintaining
  personal information **from** a child.

the school-dismissal SaaS misses both: it is staff-facing operational tooling (audience =
teachers and administrators, not children), and every record is created by an
authenticated school employee, not by a student. Children appear in the system
as *data subjects*, never as *users*.

The distinction that carries the analysis: COPPA's consent obligation attaches
to collecting personal information **from** a child. Data **about** a child,
entered **by** school staff, is a different posture. This is exactly why the
FTC has historically handled ed tech through the school-authorization framework
rather than direct vendor consent.

### 2. "Personal information" is broader than people expect

Under §312.2 it *expressly* includes **a first and last name**, and also
persistent identifiers (cookies, IP addresses, device serials), photos/video/
audio of a child, geolocation sufficient to identify street and city,
biometric identifiers, government IDs, and online contact information (which
as of 2025 includes mobile telephone numbers).

So the school-dismissal SaaS's roster data *is* "personal information about a child" — just
not collected *from* a child. Never argue "we don't collect personal
information"; argue the applicability prong instead. Getting this wrong makes
every other statement look uninformed.

### 3. Age is not a saving grace here — and that is fine

the school-dismissal SaaS serves Pre-K through 5th grade (canonical grades `PK, KG, 01-05`),
so effectively **every** student in the system is under 13 and therefore a
"child" under COPPA. There is no "some of our users are over 13" argument
available. The defense rests entirely on prongs (a) and (b), not on age.

### 4. CIPA is a funding condition on the school, not a product requirement

CIPA's obligations — filtering, an internet safety policy, monitoring minors'
online activity, internet-safety education, a public hearing — all bind the
**school or library** as an E-rate applicant. There is no certification a
vendor can hold. When a district asks, the useful answer shows you understand
their burden and describes how the platform's design supports it (access
controls, audit trail, data minimization, no student-facing internet access).

### 5. FERPA is the regime districts actually live in

FERPA has no direct vendor liability. Vendors are reached through the
**school-official exception** (34 CFR 99.31(a)(1)): a school may disclose
education-record PII to a contractor performing an institutional function the
school would otherwise perform, **under the school's direct control**, using
the data only for that purpose. That contractual posture — not a COPPA safe
harbor — is what the school-dismissal SaaS's school relationships rest on.

## Procedure — answering a compliance question

1. **Identify who is asking and what they need.** A district questionnaire, a
   procurement office, and an internal design review need different outputs.
2. **Determine which regime is implicated.** Vendor duty → COPPA. School
   funding condition → CIPA. School's records obligation → FERPA. Load the
   matching reference.
3. **For COPPA, walk the applicability test explicitly** and write down the
   conclusion for each prong. Do not skip to "we're fine."
4. **Re-verify every platform claim against the current code** with
   `search_files` / `read_file` before putting it in writing. Characterization
   of what the platform stores is the part most likely to have drifted.
5. **State the hedge.** Where the law is unsettled — notably the ed-tech and
   school-authorization provisions the FTC declined to finalize — say so
   plainly rather than asserting a clean bill of health.
6. **Separate legal duty from good practice.** Flagging something as "not
   legally required today, but cheap and worth doing" is more credible than
   claiming either full compliance or full exposure.

## Pitfalls

- **Saying "we don't collect personal information from children" on the basis
  that students aren't users.** The accurate statement is that the service is
  not directed to children and the operator lacks actual knowledge of
  collecting *from* a child. The roster data is still personal information
  *about* children.
- **Treating CIPA as a vendor certification.** It isn't one. There is no such
  thing, and claiming compliance signals confusion. Same for FERPA — there is
  no "FERPA certification" for vendors.
- **Assuming the 2025 amendments settled ed tech.** They pointedly did not.
  The FTC deferred the school-authorization provisions to avoid conflict with
  possible DOE FERPA rulemaking and said it will continue enforcing ed tech
  "consistent with its existing guidance" — i.e., guidance, not codified text.
- **Quoting the rule without checking the date.** 16 CFR Part 312 was amended
  effective June 23, 2025, with compliance due April 22, 2026. Pre-2025
  summaries of §§312.4, 312.8, and 312.10 are materially out of date.
- **Confusing "no direct duty" with "nothing to do."** CIPA and FERPA bind the
  school, but the school will flow those duties down by contract. Expect to
  answer for access control, retention, breach notice, and auditability.
- **Letting the retention answer be verbal.** If COPPA were ever found to
  apply, §312.10 requires a **written** data retention policy. Writing one
  costs little and is the single highest-leverage gap to close.

## Verification

Confirm the platform-side characterizations still hold before relying on them:

```bash
cd /path/to/the school-dismissal SaaS-saas-migrated
search_files pattern="class Student\\(" path="backend/app/models.py"
search_files pattern="parent_email|profile_picture_url|is_active" path="backend/app/models.py"
search_files pattern="umami|analytics" path="frontend/index.html"
search_files pattern="RequireAuth" path="frontend/src/main.jsx"
```

For the regulatory text, load `references/` first; if a citation is going into
an external document, re-fetch the section with `web_extract` on the eCFR
(`https://www.ecfr.gov/current/title-16/section-312.<n>`) to confirm it has not
changed.

## References

Load with `skill loader (name="cipa-coppa-school-platform", file_path="...")`.

| File | Load when |
|---|---|
| `references/coppa-framework.md` | You need the COPPA statute/Rule structure: who is an operator, what counts as personal information, the five core obligations, consent exceptions. Start here for any COPPA question. |
| `references/coppa-2025-amendments.md` | You need to know what changed in the 2025 Rule, the effective/compliance dates, and exactly what the FTC declined to finalize on ed tech and schools. |
| `references/cipa-requirements.md` | A district asks about CIPA or E-rate, or you need the school-side obligations, the filter rules, and what CIPA explicitly does *not* require. |
| `references/ferpa-interface.md` | You need the school-official exception, direct control, how FERPA/COPPA/CIPA interlock, and what belongs in a DPA. |
| `references/compliance-decision-tables.md` | You want the fast lookup: applicability tests, regime comparison, district-question-to-answer map, and feature-change triggers. |
