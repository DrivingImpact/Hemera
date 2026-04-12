# Credentials and Logos Research — Hemera

**Date:** 2026-04-12
**Purpose:** Identify which cybersecurity credentials and ESG framework logos Hemera can legitimately pursue and/or display on the landing page (hemera-nx8p.vercel.app) to build enterprise trust.
**Audience context:** Hemera is a UK-based ESG / carbon consultancy running a SaaS dashboard (Next.js + Python/FastAPI + Postgres + Clerk). Early stage. Enterprise UK buyers for ESG tooling commonly come from FTSE-adjacent supply chains, MoD-adjacent supply chains, public sector, and corporates under CSRD/SECR obligations.

> **Caveat on costs and timelines:** Ranges below reflect publicly cited figures from 2025–2026 sources. Actual quotes (especially for CE+, ISO 27001, SOC 2) always require a scoping call. Where a figure is not reliably sourced, it is flagged as "uncertain."

---

## Part A — Cybersecurity credentials

Ordered fastest → slowest to achieve.

| # | Credential | What it is / issuer | Cost (GBP unless stated) | Timeline | Effort | Worth it for Hemera? | Logo display? |
|---|---|---|---|---|---|---|---|
| 1 | **ICO registration (Data Protection Fee)** | Statutory annual fee paid to the UK Information Commissioner's Office; legally required of almost any UK org processing personal data. Not a "certification" — it's a licence/registration. | **Tier 1 (micro, <£632k turnover or <10 staff): £40/yr**. Tier 2 (SME): £60/yr. Tier 3: £2,900/yr. £5 discount if paid by direct debit. | **Same day** — online form. | Trivial (<1 hour). | **Mandatory, not optional.** Hemera almost certainly needs this now if it isn't already registered. | ICO does not provide a logo. You can state "Registered with the UK ICO" and link to the public register entry. |
| 2 | **GDPR "compliance" statement** | There is **no single formal UK GDPR certification** for general-purpose SaaS. UKAS and the ICO have approved only four niche schemes so far (ADISA ICT asset recovery, Age Appropriate Design, Age Check, Training/Qualifications). None apply to an ESG SaaS. | £0 for a self-published privacy notice + DPA template. | Days to weeks to author properly. | Low–medium (drafting privacy notice, DPA, DPIA, data map). | **Yes — necessary baseline.** The "credential" is a well-written privacy policy, DPA, sub-processor list, and being on the ICO register. | No logo. Best practice: publish "GDPR / UK GDPR compliant" language backed by the actual policy pages. Do **not** imply a third-party certification exists. |
| 3 | **Cyber Essentials (self-assessment)** | UK government-backed scheme run by IASME on behalf of NCSC. Five technical control areas (firewalls, secure config, user access, malware, patching). | Micro (0–9 staff): **£320 +VAT**. Small (10–49): £400 +VAT. Annual renewal at same cost. | **2–6 weeks** typical (6 months max window after registration). Self-assessment submitted then verified by an IASME-accredited body. | Low–medium. A named person at ~1 day/week for 2–3 weeks. | **Highly recommended — almost a baseline.** Cheap, fast, widely recognised in UK public sector / FTSE supplier questionnaires. Mandatory for most central-gov contracts handling personal/ICT data. | **Yes.** IASME provides an official Cyber Essentials badge/mark to certified orgs; display rules are in the IASME logo pack. Must be in-date to display. |
| 4 | **Cyber Essentials Plus** | Same five controls as CE, but independently **audited** (external vulnerability scan, authenticated patch audit, malware checks, MFA verification). Higher assurance tier. | Typically **£1,400–£3,000 +VAT** for small orgs; quoted individually. Most SMEs £1,500–£2,500. | **2–6 weeks after CE passes**, and **must be completed within 3 months of CE** or you start again. | Medium. Same prep as CE + one audit day on-site or remote. Remediation work can extend by 2–4 weeks. | **Recommended as step 2** after CE, especially if targeting MoD supply chain, NHS, or regulated buyers. Noticeably stronger signal than CE alone. | **Yes**, same IASME badge (Plus version). |
| 5 | **IASME Cyber Assurance (Level 1, verified self-assessment)** | IASME's broader standard — goes beyond CE's five controls into governance, risk, incident response, backups, training, physical security, GDPR overlap. Sometimes called "a lightweight ISO 27001 alternative for SMEs". Requires valid CE first. | Micro: **£320 +VAT**. Small: £440 +VAT. (On top of the CE fee.) | **~4–5 weeks** for Level 1 once CE is in place. | Medium. More documentation than CE — policies, asset register, risk register, training evidence. | **Maybe.** Good cheap middle-ground if ISO 27001 feels like overkill. Recognised by UK buyers but far less internationally visible than ISO 27001. Three-year cycle (L1 self-assessed yrs 1–2, full L2 audit in yr 3). | **Yes**, IASME provides a dedicated Cyber Assurance badge. |
| 6 | **SOC 2 Type I** | AICPA (US) attestation. A CPA auditor confirms that security controls are **designed** appropriately at a point in time. Common US enterprise ask. | Audit fee alone **US$5k–20k**; all-in (tools, prep, pen test, staff time) **US$15k–40k**. | **8–16 weeks** if security hygiene already decent. | Medium–high. Needs policies, access reviews, vendor management, ticket/change evidence, often a compliance-automation platform (Vanta/Drata). | **Only if targeting US buyers.** For a UK-first ESG SaaS it's lower priority than CE+/ISO 27001. A snapshot Type I is a stepping stone. | **Yes** — AICPA SOC logo, provided the current report is in hand. Terms are strict about implying AICPA endorsement. |
| 7 | **ISO 27001** | International ISMS standard from ISO. A UKAS-accredited certification body audits that you have a working Information Security Management System. The gold standard for UK/EU B2B SaaS sales. | Startup range **£6k–£15k** all-in (DIY toolkit + small audit). More realistically **£17k–£25k+** with a compliance SaaS (Vanta/Drata/Secureframe) and consultancy. Larger scopes £25k–£42k year 1. Annual surveillance audits ~£6–8k each. | **3–6 months** for a focused startup on a tight scope; 6–12 months is more typical. | High. Requires an ISMS, risk assessments, Statement of Applicability, internal audits, management reviews, evidence collection, often a dedicated owner. | **Worth pursuing within 12 months** if Hemera is selling to FTSE/enterprise. Becomes virtually table-stakes in B2B SaaS procurement questionnaires. | **Yes**, but: you can **only** display the logo of the **certification body** (e.g. BSI, LRQA) — not an "ISO 27001" logo per se. ISO itself restricts use of the ISO logo. Always pair with cert number and scope. |
| 8 | **SOC 2 Type II** | Same as Type I, but the auditor confirms controls were **operating effectively over time** — minimum 3-month observation window, typically 6–12. | Audit fee alone **US$7k–50k**; all-in first year **US$25k–80k+**, plus pen-test US$5k–25k. | **6–15 months** total (prep + observation + audit + report). | High, sustained. Evidence collection has to actually run for the whole observation window. | **Only if US enterprise sales are material.** Lower priority than ISO 27001 for a UK-first business. | **Yes**, with the same constraints as SOC 2 Type I. |

### Timeline banding (Part A)

- **Days:** ICO registration; GDPR self-publication (policy drafting).
- **Weeks (1–6):** Cyber Essentials, Cyber Essentials Plus (after CE), IASME Cyber Assurance Level 1.
- **Months (3–6):** ISO 27001 (aggressive timeline), SOC 2 Type I.
- **Year+:** ISO 27001 (realistic), SOC 2 Type II, IASME Cyber Assurance Level 2 (year 3 audit in the cycle).

### Other things UK ESG SaaS buyers commonly ask for

Not formal credentials, but frequently seen in security/procurement questionnaires:

- **Data Processing Agreement (DPA)** and named **sub-processor list** published on the website.
- **Privacy policy** + **cookie policy** compliant with UK PECR + UK GDPR.
- **DPIA** (Data Protection Impact Assessment) for ESG data processing.
- **Penetration test summary letter** (annual) — typically £3k–£8k from a CREST-accredited UK tester.
- **UK data residency statement** (where Postgres / Clerk / file storage physically sit).
- **Disaster recovery / business continuity statement** with RTO/RPO numbers.
- **Vulnerability disclosure policy** (security.txt on the domain).
- **Supplier questionnaires** — e.g. NCSC Supplier Assurance Questions, SIG Lite, or buyer-specific variants.
- **Signed Modern Slavery statement** (required if turnover passes £36m; a voluntary one is a trust signal before then).
- **Insurance evidence:** Professional Indemnity + Cyber Liability (≥£1m each is the usual ask).

---

## Part B — ESG / sustainability framework logos

| # | Logo | What it is | Can Hemera display it? | Requires membership / licence / approval? | Brand usage rules / notes |
|---|---|---|---|---|---|
| 1 | **SBTi** (Science Based Targets initiative) | Corporate climate target-setting + validation body. Partnership of CDP, UNGC, WRI, WWF, WeMeanBusiness. | **No — not by Hemera.** The SBTi logo is reserved for companies that have (a) **committed** (limited use) or (b) had **targets validated** by SBTi. A consultancy helping clients set SBTi targets is **not** licensed to display the SBTi logo to market itself. | Yes — only for SBTi-committed / validated companies, and only with full target language accompanying the logo. | Hemera may legitimately write copy like "Helps clients align with SBTi methodology" but must not display the SBTi mark on its own brand. [Source: SBTi Communications Guide](https://files.sciencebasedtargets.org/production/files/SBTi-communications-guide-for-organizations-taking-action.pdf) |
| 2 | **CDP** (Carbon Disclosure Project) | Global environmental disclosure platform. | **Conditional.** CDP has distinct logos: (a) a "discloser" stamp for companies that disclose, (b) A-List / Leader stamps for scored disclosers, (c) an **Accredited Solutions Provider (ASP)** mark for consultancies/software in CDP's partner programme. A generic "we use CDP frameworks" consultancy logo does **not** exist. | Yes. ASP status requires application, vetting, and (typically) an annual fee. Discloser stamps require completing a CDP disclosure. | Strict. Logos have minimum-size rules, a protection zone, and approved colour variants. Annual review cycle. [CDP Logo Guidelines 2022](https://cdn.cdp.net/cdp-production/comfy/cms/files/files/000/006/601/original/CDP_discloser_stamp_and_logo_guidelines_2022.pdf) |
| 3 | **GRI** (Global Reporting Initiative) | Global sustainability reporting standards body. | **Only as a GRI Certified Training Partner, GRI Community member, or GRI Software & Tools Partner.** Simply "using GRI standards" does not entitle a consultancy to display the GRI logo. | Yes — Community membership (annual fee) or Certified Training Partner status (certification process + annual licence). | [GRI Certified Training Partners](https://www.globalreporting.org/reporting-support/education/certified-training-partners/). Hemera can legitimately say "GRI-aligned reporting" without the logo; to display any GRI mark it needs formal partner status. |
| 4 | **TCFD** | Task Force on Climate-related Financial Disclosures (now effectively absorbed into ISSB/IFRS S2). | **No — not as a marketing logo.** TCFD terms-of-use forbid use of its marks in a way that implies endorsement or sponsorship. Reports and slides *describing* TCFD alignment are fine; displaying the logo on a consultancy's homepage as a credibility mark is not. | No formal membership to grant logo rights; the mark is simply restricted. | [TCFD Terms of Use](https://www.fsb-tcfd.org/terms-of-use/). Safer copy: "TCFD / ISSB S2-aligned reporting." |
| 5 | **GHG Protocol** | The core corporate carbon accounting standards (Corporate Standard, Scope 3 Standard, Product Standard). Co-managed by WRI + WBCSD. | **No generic "we use GHG Protocol" logo exists.** GHG Protocol launched a **"Built on GHG Protocol" mark** in 2024, but it's for **tools/guidance documents** that have been through a formal conformance review — not for consultancies generally. | Yes — the "Built on GHG Protocol" mark requires application and review. | [GHG Protocol — Built on GHG Protocol Mark](https://ghgprotocol.org/GHG-Protocol-Launches-the-Built-on-GHG-Protocol-Mark). Hemera may write "aligned with the GHG Protocol Corporate Standard" without a logo. Applying for the Built-on mark for HemeraScope specifically could be interesting medium-term. |
| 6 | **ISO 14064** | International standard for GHG quantification, reporting, and verification (3 parts). | **No direct consumer-facing logo.** ISO itself prohibits its logo being used by certified orgs. You can display the **certification body's** mark (e.g. BSI, LRQA, SGS, NQA) once Hemera or a client is verified. | Only via a UKAS-accredited verification body engagement. | Same model as ISO 27001 — refer to the standard in text; badge comes from the cert body if one exists. |
| 7 | **PAS 2060 / ISO 14068** (carbon neutrality) | PAS 2060 was BSI's carbon-neutrality spec, **superseded by ISO 14068-1** from 1 January 2025. | **Not by Hemera itself.** The recognised consumer-facing mark is the **BSI Kitemark for Carbon Neutrality**, awarded to **verified organisations/products**, not to consultancies advising them. | Yes — BSI assessment and licence for the Kitemark. | [BSI — ISO 14068-1](https://www.bsigroup.com/en-US/products-and-services/standards/pas-2060-carbon-neutrality/). Hemera can legitimately offer "ISO 14068-1 readiness support" in copy. |
| 8 | **SBTN** (Science Based Targets Network) | Sister initiative to SBTi, but for **nature** (land, freshwater, oceans, biodiversity) rather than climate. Launched pilot targets in 2023. | **Only via the Corporate Engagement Program.** Joining requires signed programme Terms of Use and a submitted company logo (SBTN uses your logo, not the other way round). No general-purpose "SBTN-aligned" logo for consultancies. | Yes — Corporate Engagement Program membership. | [SBTN Corporate Engagement Program](https://sciencebasedtargetsnetwork.org/company/join-engagement-program/). Still early-stage; lower near-term value than SBTi. |
| 9 | **UN Global Compact** | World's largest voluntary corporate sustainability initiative. Ten principles (human rights, labour, environment, anti-corruption). | **Yes, conditional on becoming a Participant.** Participants with active Communication on Progress (CoP) can request use of the **"We Support the UN Global Compact"** endorser logo. | Yes — must be an active Participant with an up-to-date CoP, and must request permission to use the logo. Annual contribution required (tiered by revenue; typically modest for small firms — figure uncertain without quote). | [UN Global Compact — Logo Policy](https://d306pr3pise04h.cloudfront.net/docs/about_the_gc/logo_policy/Logo_Policy_EN.pdf). Strict rules: must describe self as "participant" not "member"; logo must appear in isolation; minimum size 24mm / 68px; cannot appear inside a sentence. |
| 10 | **B Corp** | B Lab certification assessing legal accountability, environmental, worker, community, customer, and governance performance. | **Only after certification.** | Yes — full B Impact Assessment, verification, governance amendments to articles of association, minimum score, three-year recertification. | Cost: small-company annual fee **from US$500/year** (revenue-tiered), but realistic all-in first-time cost **US$8k–25k** including prep, legal, and consultant support. Timeline **6–12 months** typical. Since 2025, B Lab is phasing in V2 standards with minimum-requirements across seven topics. Strong brand halo for an ESG consultancy — arguably the highest-signal logo on this list, but the biggest lift. |

### Key distinction

- **Display-as-you-use (without logo):** GHG Protocol, GRI, TCFD, ISO 14064, ISO 14068, SBTi, CDP — Hemera can legitimately **describe methodology alignment in copy** for all of these. That alone is a significant trust signal.
- **Display with a logo, no friction:** *None.* Every logo in Part B requires either certification, partnership, or formal programme membership.
- **Display with a logo, achievable in months:** UN Global Compact Participant; CDP Accredited Solutions Provider (if Hemera wants to formally partner).
- **Display with a logo, achievable in 6–12 months:** B Corp (biggest payoff, biggest effort).
- **Display with a logo for Hemera's clients' reports (not Hemera's own site):** SBTi validated-target marks, CDP disclosure stamps, BSI Kitemark — these live on the client, not the consultancy.

---

## Recommended next 3 months

### Credentials to prioritise (2–3)

1. **ICO Data Protection Fee registration** — if not already done. Trivial, legally required, signals basic compliance. **Now. <1 hour. ~£40/year.**
2. **Cyber Essentials (self-assessment)** — the single highest ratio of trust-signal to cost/effort for a UK SaaS. Unlocks a large portion of UK public-sector and enterprise supplier questionnaires in one move. **~£320 + VAT. 2–6 weeks.** Note: v3.3 of requirements takes effect 27 April 2026 — either certify before then against v3.2, or plan for v3.3's stricter MFA and 14-day critical-patch rules.
3. **Publish a proper privacy + security page** — DPA template, sub-processor list (Clerk, Vercel, Postgres host, Anthropic if used, DEFRA/ONS data sources, etc.), data residency, DPIA summary, security contact. **Days of effort, £0.** This is what most enterprise buyers actually read before asking for a questionnaire.

### Logos to prioritise (3–5)

Order = signal × achievability for an early-stage ESG consultancy.

1. **"GHG Protocol-aligned" + "ISO 14064-compatible" + "SBTi methodology"** — as **text copy**, not logos. Zero cost, zero risk, legitimate, and these are the methodology brands enterprise buyers actually recognise. Ship on the landing page immediately.
2. **UN Global Compact Participant** — tractable within 3 months. Submit a letter of commitment, pay the (typically modest for SMEs) annual contribution, publish a short Communication on Progress. Yields a licensed logo ("We Support the UN Global Compact") that's immediately recognisable globally. Strong ESG-credibility signal for an ESG consultancy and costs less than B Corp by an order of magnitude.
3. **CDP Accredited Solutions Provider** — worth investigating as a **medium-term** play (3–6 months). If HemeraScope supports clients through CDP disclosure, this is the formal path to displaying the CDP partner mark and appearing in CDP's own partner directory — meaningful inbound channel.
4. **B Corp — begin the B Impact Assessment now** as a 6–12 month project. The assessment itself is free and the process of going through it will force through sustainability and governance improvements that will show up in the Year-1 audit anyway. Target certification in ~12 months; don't market as "B Corp" until certified.
5. **Do NOT put SBTi / TCFD / GRI / CDP logos on the landing page speculatively.** All four have active brand-protection policies, and an ESG consultancy displaying ESG logos it hasn't earned is a reputational own-goal in front of exactly the buyer persona Hemera is trying to win.

### Sequencing summary

- **Week 0–2:** ICO fee; publish privacy/security/DPA page; draft UN Global Compact letter of commitment.
- **Week 2–8:** Cyber Essentials (self-assess); submit UNGC application.
- **Month 2–4:** Cyber Essentials Plus; begin B Impact Assessment; start ISO 27001 gap analysis (use a compliance-automation SaaS if budget allows).
- **Month 4–12:** ISO 27001 certification; B Corp submission; decide on CDP ASP based on HemeraScope product-market fit.

---

## Sources

- [NCSC — Cyber Essentials overview](https://www.ncsc.gov.uk/cyberessentials/overview)
- [IASME — Cyber Essentials FAQs](https://iasme.co.uk/cyber-essentials/frequently-asked-questions/)
- [IASME — Cyber Assurance](https://iasme.co.uk/iasme-cyber-assurance/)
- [ICO — Data Protection Fee](https://ico.org.uk/for-organisations/data-protection-fee/)
- [ICO — UK GDPR Certification schemes](https://ico.org.uk/for-organisations/advice-and-services/certification-schemes/certification-schemes-a-guide/)
- [UKAS — UK GDPR new programmes](https://www.ukas.com/accreditation/about/developing-new-programmes/development-programmes/uk-gdpr/)
- [NCSC — Supplier assurance questions](https://www.ncsc.gov.uk/guidance/supplier-assurance-questions)
- [gov.uk — Supplier Assurance Questionnaire guide](https://www.gov.uk/government/publications/supplier-cyber-protection-service-supplier-assurance-questionnaire-workflow/cyber-security-model-supplier-assurance-questionnaire-saq-question-set-guide)
- [ISO 27001 cost breakdown — Hightable](https://hightable.io/iso-27001-certification-cost/)
- [ISO 27001 tech startup guide — Hightable](https://hightable.io/iso-27001-costs-tech-startups/)
- [SOC 2 Type 1 vs Type 2 — DSALTA](https://www.dsalta.com/resources/soc-2/soc-2-type-1-vs-type-2-timeline-cost-guide)
- [SOC 2 audit cost — Thoropass](https://www.thoropass.com/blog/soc-2-audit-cost-a-guide)
- [SBTi — Communications guide for companies](https://files.sciencebasedtargets.org/production/files/SBTi-communications-guide-for-organizations-taking-action.pdf)
- [SBTi — FAQs](https://sciencebasedtargets.org/faqs)
- [CDP — Logo guidelines 2022](https://cdn.cdp.net/cdp-production/comfy/cms/files/files/000/006/601/original/CDP_discloser_stamp_and_logo_guidelines_2022.pdf)
- [CDP — Brand Hub](https://www.cdp.net/en/brand-hub)
- [GRI — Certified Training Partners](https://www.globalreporting.org/reporting-support/education/certified-training-partners/)
- [TCFD — Terms of Use](https://www.fsb-tcfd.org/terms-of-use/)
- [GHG Protocol — Built on GHG Protocol Mark](https://ghgprotocol.org/GHG-Protocol-Launches-the-Built-on-GHG-Protocol-Mark)
- [BSI — ISO 14068-1 / carbon neutrality](https://www.bsigroup.com/en-US/products-and-services/standards/pas-2060-carbon-neutrality/)
- [SBTN — Corporate Engagement Program](https://sciencebasedtargetsnetwork.org/company/join-engagement-program/)
- [UN Global Compact — Logo Policy PDF](https://d306pr3pise04h.cloudfront.net/docs/about_the_gc/logo_policy/Logo_Policy_EN.pdf)
- [UN Global Compact — Participation](https://unglobalcompact.org/participation)
- [B Lab UK — Pricing](https://bcorporation.uk/b-corp-certification/the-certification-process/pricing/)
- [B Lab US/Canada — Process & Requirements](https://usca.bcorporation.net/process-requirements-fees/)
