# FERPA and How the Three Regimes Interlock

Distilled from the DOE Student Privacy site (studentprivacy.ed.gov) and FTC
ed-tech guidance. FERPA is the regime districts actually operate under, and
the one through which vendor obligations normally arrive — by contract, not by
statute.

## FERPA in one paragraph

The Family Educational Rights and Privacy Act governs an educational agency or
institution's handling of **education records** — records directly related to a
student and maintained by the agency or institution (or by a party acting for
it). It gives parents (and eligible students) rights to inspect, amend, and
control disclosure. **FERPA applies to the school, not to the vendor.** There
is no "FERPA certification" a vendor can hold, and there is no FERPA
provision that directly regulates a software supplier.

## The school-official exception — the vendor's doorway

**34 CFR 99.31(a)(1)** permits disclosure of education-record PII without
consent to a **school official** with a **legitimate educational interest**.

**34 CFR 99.31(a)(1)(i)(B)** is the outsourcing limb that matters to vendors:
schools may **outsource institutional services or functions** involving
education-record disclosure to **contractors** who stand in the school's
shoes. Per DOE guidance and standard summaries, such a third party may be
treated as a school official where it:

1. **performs a function the school would otherwise perform itself**
   (outsourced institutional service or function);
2. **uses the data only for the reason it was shared** — the specified purpose,
   and no other; and
3. is **under the school's direct control** with respect to the use and
   maintenance of the data.

**34 CFR 99.33(a)** supplies the mechanics: the school official may use the
recorded information **only for the purpose for which the disclosure was made**,
and must not redisclose without consent (subject to the section's own
conditions).

"Direct control" is the load-bearing and most-litigated-in-spirit element. It
is ordinarily established **by contract** — the agreement is the instrument
that makes the vendor a school official rather than an unauthorized recipient.

## The practical posture this creates for a vendor

| Question | Reality |
|---|---|
| Is the vendor directly regulated by FERPA? | No |
| Then how does FERPA reach it? | Through the school, via the school-official exception and the contract |
| What makes the vendor's position defensible? | Written contract establishing direct control + purpose limitation |
| Who is accountable to parents? | The school; the vendor is accountable to the school |
| What happens if the vendor misuses data? | The school's FERPA posture is compromised, and the vendor breaches contract |

Because FERPA's vendor hook is contractual, the **DPA is the operative
document** — not a certification, not a self-assessment.

## How the three regimes compare

| | **COPPA** | **CIPA** | **FERPA** |
|---|---|---|---|
| Regulates | The **operator** (vendor) | **Schools/libraries** seeking E-rate funds | **Educational agencies/institutions** |
| Trigger | Child-directed service **or** actual knowledge of collecting PI **from** a child under 13 | Receipt of E-rate discounts for internet access / Category Two | Maintenance of **education records** |
| Age threshold | **Under 13** ("child") | **Under 17** ("minor") | No age limit; students of any age |
| Direct vendor duty? | **Yes** | No | No |
| Core mechanism | Notice + **verifiable parental consent** | Filter + internet safety policy + public hearing | Consent / **school-official exception** for disclosure |
| Enforced by | FTC | FCC / USAC (via E-rate funding) | DOE (via funding conditions) |
| Typical vendor artifact | Online notice, consent flow, retention policy | Nothing required of vendor | **DPA / contract with direct-control terms** |

## Where they overlap and why districts conflate them

- **Overlapping subject matter.** All three touch student/minor personal
  information, so any vendor review surfaces all three names at once.
- **The same fact pattern, three framings.** A roster of student names is:
  potentially "personal information from a child" under COPPA; "personal
  information regarding minors" under the school's CIPA policy; and PII from
  education records under FERPA.
- **FERPA does the daily work, COPPA sets the floor for vendor-collected kid
  data, CIPA gates the money.** A district's composite concern is "are we safe
  giving this vendor student data," and each statute answers a different slice.

## Where COPPA and FERPA specifically interact

This is the seam the FTC deliberately left open:

- The FTC's guidance allows **schools to consent on behalf of parents** for
  COPPA purposes, limited to a **school-authorized educational purpose** with
  **no other commercial purpose**.
- FERPA's **school-official exception** independently lets the school disclose
  education-record PII to a vendor performing an outsourced institutional
  function under direct control.
- Both routes depend on the **same underlying fact**: the school authorized
  the collection/use, and the vendor stays inside the purpose.

The 2025 COPPA amendments **declined to codify** the school-authorization
exception, citing DOE's stated intent to amend FERPA regs at 34 CFR 99 —
specifically to address non-consensual disclosures of PII from education
records to third parties. So the boundary between the COPPA school-consent
concept and the FERPA school-official concept is **currently unsettled and
interdependent**. Practical consequence: rely on guidance, document the school's
authorization, and keep the purpose limitation airtight in the contract.

## What belongs in a vendor DPA

Grounded in the direct-control and purpose-limitation requirements above:

1. **Purpose limitation** — data used only to provide the contracted service;
   expressly no secondary or commercial use.
2. **No sale, no advertising, no profiling** — state it explicitly; this is the
  single most common district ask.
3. **Direct control terms** — the school owns the data, directs its use, and
  can require return or deletion.
4. **Access limitation** — named/school-authorized personnel only; role
  separation; no cross-tenant access.
5. **Security controls** — encryption in transit and at rest; access control;
   breach notification with a defined timeline.
6. **Retention and deletion** — defined timeframes, and deletion/return on
  termination. (Aligns with COPPA §312.10 if COPPA is ever found to apply.)
7. **Subprocessor / third-party flow-down** — vendors must be capable of
  maintaining protections and provide assurances. Mirrors COPPA §312.8(c).
8. **Audit and transparency** — what records exist (audit logs), and the
  school's right to review them.
9. **Parent-rights cooperation** — how the vendor assists the school in
  responding to parent inspection/amendment/deletion requests.
10. **Breach notification** — to the school, with enough detail for the school
    to meet its own obligations.

## Anti-patterns

- **Selling a "FERPA certification."** None exists for vendors.
- **Treating a signed DPA as sufficient on its own.** Direct control is a
  substance requirement, not a paperwork one; the actual data practices have to
  match the terms.
- **Assuming the COPPA school-consent route is settled law.** It is guidance,
  and the FTC paused codification specifically because DOE may move first.
- **Writing a DPA that permits "service improvement" use of student data.**
  That is a secondary commercial purpose and undercuts both the FERPA
  purpose limitation and the COPPA school-authorization condition.
