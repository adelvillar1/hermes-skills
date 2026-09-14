# CIPA — What It Requires, and of Whom

Distilled from the FCC consumer guide (last updated July 5, 2024) and USAC's
E-rate CIPA page. Enacted by Congress in **2000**; FCC implementing rules
issued **early 2001**, updated **2011**.

## The one-line framing

CIPA imposes requirements on **schools or libraries that receive discounts for
Internet access or internal connections through the E-rate program.** It is a
**funding condition**, not a product regulation. It creates **no direct
obligation on a vendor.**

When a district asks "is your product CIPA compliant?" the honest and more
credible answer explains what CIPA requires of *them*, and describes how the
platform's design fits — or does not fit — within those requirements. There is
no vendor certification to hold.

## Scope triggers

| Situation | CIPA applies? |
|---|---|
| School/library receiving E-rate discounts for **Internet access** | Yes |
| Receiving E-rate **Category Two** (internal connections, managed internal broadband, basic maintenance) | Yes |
| Receiving discounts for **telecommunications service only** | **No** — CIPA does not apply |
| Not participating in E-rate at all | No |

Note the asymmetry: a school taking only telecom discounts is outside CIPA
even though it is in E-rate.

## The three core requirements (four for schools)

### 1. Internet safety policy
Adopt **and enforce** an internet safety policy including a technology
protection measure that protects against access by **both adults and minors**
to visual depictions that are:

- **obscene**;
- **child pornography**; or
- with respect to computers used by minors — **harmful to minors**.

The policy must address all of:

- access by minors to inappropriate matter on the internet and World Wide Web;
- the **safety and security of minors when using electronic mail, chat rooms,
  and other forms of direct electronic communications**;
- unauthorized access, including "hacking" and other unlawful activities by
  minors online;
- unauthorized **disclosure, use, and dissemination of personal information
  regarding minors**; and
- measures designed to restrict minors' access to materials harmful to minors.

**"Minor" is defined as any individual under the age of 17** — note this is a
different line from COPPA's under-13 "child." A 14-year-old is a minor under
CIPA but not a child under COPPA.

### 2. Technology protection measure
A specific technology that **blocks or filters internet access**. The school or
library must enforce its operation during use of its computers with internet
access.

**Adult disablement:** an administrator, supervisor, or other person
authorized by the administrative authority may **disable** the measure during
use **by an adult**, to enable access for **bona fide research or other lawful
purpose.** The FCC's example is a library using a sign-in page where an adult
affirms intent to use the computer for bona fide research.

### 3. Public notice and hearing
Before adopting the internet safety policy, the authority must:

- provide **reasonable public notice**, and
- hold **at least one public hearing or meeting** to address the proposal.

For private schools, "public notice" means notice to their appropriate
constituent group. Per E-rate Central, this meeting is required **once, ever**
— not annually.

### 4. School-only: monitoring and education
Schools (not libraries) carry two additional certification requirements:

1. their internet safety policies must include **monitoring the online
   activities of minors**; and
2. as required by the **Protecting Children in the 21st Century Act**, they must
   provide for **educating minors about appropriate online behavior**,
   including interacting with others on social networking websites and in chat
   rooms, and **cyberbullying awareness and response**. (In effect as a
   certification item since **July 1, 2012**.)

## Definitions that matter

- **"Harmful to minors"** — CIPA uses the federal criminal definitions for
  obscenity and child pornography. "Harmful to minors" means any picture,
  image, graphic image file, or other visual depiction that (i) taken as a
  whole and with respect to minors, **appeals to a prurient interest in
  nudity, sex, or excretion**; (ii) depicts, describes, or represents in a
  **patently offensive way** an actual or simulated sexual act or sexual
  contact, actual or simulated normal or perverted sexual acts, or a lewd
  exhibition of the genitals; and (iii) taken as a whole, **lacks serious
  literary, artistic, political, or scientific value as to minors**.
- **Determination of what is inappropriate for minors** is made by the school
  board, local educational agency, library, or other responsible authority —
  not by the FCC and not by a vendor.

## What CIPA explicitly does NOT require

- It does **not** require **tracking** internet use by minors or adults.
  (Monitoring of minors' online activity is required for schools, but
  *tracking* is not.)
- It does **not** apply to entities receiving telecommunications-service-only
  discounts.
- It is **not** a vendor certification regime.

## Certification mechanics

The **Administrative Authority** — the authority responsible for administration
of the eligible school or library — must certify on **FCC Form 486** that
one of:

1. it has **complied** with CIPA's requirements;
2. it is **undertaking actions**, including any necessary procurement
   procedures, to comply; or
3. **CIPA does not apply**, because it receives discounts for
   telecommunications services only.

Applicants must certify **before** receiving E-rate funding.

### Records to retain (USAC)

- Documentation of the public notice and hearing/meeting.
- Evidence the technology protection measure was operational — e.g. archived
  samples of provider reports of blocked sites, or bills verifying the filter
  was operational; if self-filtered, archived logs from IT staff showing hours
  the filter was engaged.
- Copies of **FCC Form 479** and/or **FCC Forms 486**, as applicable.

### Correctable errors

USAC gives applicants a chance to correct **minor, immaterial** errors before
instituting recovery of E-rate funds. Two FCC-recognized examples:

- The school complied **in practice** but **inadvertently omitted** a
  requirement from its written policy → correct the policy (it was
  substantially compliant).
- No record of a public notice/hearing held **after August 2004** → correct by
  providing notice and holding a hearing or meeting.

## Why a school-privacy conversation drifts toward CIPA

CIPA's policy content includes "**unauthorized disclosure, use, and
dissemination of personal information regarding minors**" — which is exactly
the concern a district raises when evaluating any vendor holding student data.
So CIPA gets cited even where the operative duty sits with the school and the
vendor's actual exposure is contractual (FERPA school-official terms) plus
COPPA if the vendor is in scope.

The useful vendor response maps platform properties onto the school's CIPA
themes:

| School's CIPA concern | Platform property that answers it |
|---|---|
| Unauthorized disclosure/use/dissemination of minor PI | Server-enforced role separation; school-scoped data; no cross-school access |
| Who accessed what | Append-only audit trail |
| Data sitting around unnecessarily | Daily queue reset; data minimization |
| Unauthorized access | TLS in transit, encryption at rest, forced password change on first login |
| Monitoring/oversight | Audit log of sensitive actions, including impersonation |

## Contact

USAC answers E-rate questions at **1-888-203-8100**.

## Anti-patterns

- **Claiming a product is "CIPA compliant."** CIPA binds applicants; there is
  nothing for a vendor to be certified against. Claiming it signals you have
  not read the statute.
- **Conflating CIPA's "minor" (under 17) with COPPA's "child" (under 13).**
  They are different thresholds used for different purposes.
- **Treating the monitoring requirement as a tracking mandate.** Schools must
  monitor minors' online activity; CIPA expressly does not require tracking of
  internet use.
- **Re-litigating the hearing requirement annually.** It is a one-time
  obligation.
