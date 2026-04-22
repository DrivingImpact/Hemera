---
title: HemeraScope Legal Statements — Research & Drafts
date: 2026-04-12
status: DRAFT — requires qualified UK solicitor review before publication
---

> ## LEGAL CAVEAT — READ THIS FIRST
>
> **These are drafts prepared by a non-lawyer.** They summarise publicly available UK GDPR, PECR and ICO guidance as of April 2026, and are intended as a starting point only. They **must be reviewed by a qualified UK solicitor specialising in data protection and SaaS contracts** before being published on the Hemera Intelligence / HemeraScope website or agreed with any client.
>
> **Areas of particular legal risk requiring qualified review:**
>
> 1. **The anonymised supplier retention clause** (Part 2, Section 11 and Part 3, Section 6). Whether data is "truly anonymous" under UK GDPR Recital 26 is a fact-specific judgement. If a regulator or court finds the retained data is merely pseudonymised, Hemera would be processing personal data outside its stated lawful basis and outside the Privacy Policy.
> 2. **The limitation of liability cap** (Part 3, Section 10). Caps on liability are subject to the Unfair Contract Terms Act 1977 and, for B2C clients, the Consumer Rights Act 2015. A cap equal to 12 months' fees is market standard for UK SaaS but must be tested against the specific services Hemera delivers.
> 3. **The processor / controller classification** (Part 2, Section 1). Hemera's role is almost certainly split — processor for client-uploaded supplier lists, controller for analyst-generated outputs, and controller for its own website visitors. A solicitor should confirm this split before the Privacy Policy and DPA are finalised.
>
> Nothing in this document is legal advice. Do not publish without review.

---

# Table of contents

- [Part 1 — Legal statements checklist for the HemeraScope landing page](#part-1)
- [Part 2 — Draft Privacy Policy](#part-2)
- [Part 3 — Draft Terms and Conditions](#part-3)
- [Part 4 — Cookie statement and cookie table](#part-4)
- [Sources](#sources)

---

<a id="part-1"></a>

# Part 1 — Legal statements checklist

The table below lists every legal statement or notice a UK SaaS / consultancy combo like Hemera Intelligence should have in place before going live, whether each is **required** or **recommended**, the legal basis that demands it, and where it belongs on the website.

| # | Statement | Required / Recommended | Legal basis | Location on site |
|---|-----------|------------------------|-------------|------------------|
| 1 | **Privacy Policy / Privacy Notice** | **Required** | UK GDPR Articles 13 & 14 (right to be informed); ICO Privacy Notice Checklist | Footer link on every page; also linked from Clerk sign-up and any form that collects personal data |
| 2 | **Terms and Conditions (website T&Cs)** | Recommended (not strictly mandatory but universal) | Contract law; consumer protection where applicable | Footer link on every page |
| 3 | **Subscription / Service Agreement (MSA)** | **Required in practice** | Contract law; UK GDPR Art. 28 (requires a DPA where Hemera is processor) | Presented to clients at onboarding; referenced from footer |
| 4 | **Data Processing Agreement (DPA)** | **Required** wherever Hemera processes personal data on behalf of a client | UK GDPR Article 28(3) | Schedule / annex to the MSA |
| 5 | **Cookie Notice + PECR consent banner** | **Required** if any non-essential cookies or similar tech are used | Privacy and Electronic Communications Regulations 2003, reg. 6, as amended by the Data (Use and Access) Act 2025 | Banner on first visit; persistent "Cookie settings" link in footer; full cookie list on a dedicated page |
| 6 | **ICO data protection fee registration** | **Required** for any controller that is not exempt | Data Protection (Charges and Information) Regulations 2018 | Display the ICO registration number in the footer or Privacy Policy |
| 7 | **Modern Slavery Statement** | **Optional** for Hemera (turnover below £36m). Strongly recommended as a voluntary statement because Hemera's clients buy supply-chain assurance | Modern Slavery Act 2015, s.54 (mandatory only above £36m global turnover) | Dedicated page linked from footer; submit voluntarily to the UK Modern Slavery Statement Registry |
| 8 | **Accessibility Statement** | Required for public sector client-facing services; recommended otherwise | Public Sector Bodies (Websites and Mobile Applications) (No. 2) Accessibility Regulations 2018 | Linked from footer |
| 9 | **Complaints procedure** | Recommended; required in some regulated sectors | Good practice; UK GDPR Art. 77 (right to lodge a complaint with the ICO) | Section within Privacy Policy and / or a standalone page |
| 10 | **Company information (footer)** | **Required** | Companies Act 2006, s.1202 and the Companies (Trading Disclosures) Regulations 2008; EU e-Commerce Directive implementing regs | Footer of every page |
| 11 | **Sub-processor list** | Recommended; often contractually required by enterprise clients | UK GDPR Art. 28(2) and (4); client DPA | Dedicated Trust / Security page; linked from DPA |
| 12 | **Security / Trust page** | Recommended; expected by UK enterprise buyers | Best practice; supports UK GDPR Art. 32 | Linked from footer |
| 13 | **AI / methodology disclosure** | Recommended for an analytics product (buyers increasingly ask) | Best practice; pending EU AI Act obligations for providers | Product page, methodology docs |
| 14 | **Responsible disclosure / vulnerability policy (security.txt)** | Recommended | Best practice; ISO 27001 A.5.7 | `/.well-known/security.txt` |

## Notes on each item

### 1. Privacy Policy

UK GDPR Articles 13 and 14 set out the "right to be informed" — the controller must proactively tell individuals who they are, what data is collected, why, on what lawful basis, how long it's kept, who it's shared with, whether it's transferred outside the UK, and what rights the individual has. The ICO publishes a [Privacy Notice Checklist](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/checklists/) that should be followed line by line.

### 2. Terms and Conditions

UK law does not require a general website T&Cs page, but every UK SaaS has one — it sets the contractual framing for website use, clarifies IP, disclaims warranties for public-facing marketing content, and sits behind any "by using this site you agree…" clause.

### 3 and 4. MSA and DPA

Because HemeraScope ingests client-uploaded supplier records that may contain personal data (supplier contact names, buyer contact names, emails embedded in invoice lines), Hemera will be acting as a **processor** for that data. UK GDPR Article 28(3) requires that such processing be governed by a written contract that includes the six prescribed clauses. This is typically delivered as a DPA annexed to the Master Services Agreement.

### 5. Cookie notice and PECR

PECR (as updated by the Data (Use and Access) Act 2025, which came into force on 5 February 2026) requires prior consent for any cookie or similar technology that is not strictly necessary. The DUAA introduced three new exemption categories (statistical / audience measurement, appearance & functionality, and security / fraud prevention on a narrow basis), but all marketing and advertising cookies still require opt-in consent. Draft ICO guidance on the new exemptions is under consultation and the finalised version is expected in spring 2026 — watch for updates.

Key requirement: users must take an explicit affirmative action; withdrawal of consent must be as easy as granting it; fines under PECR were increased 35-fold under DUAA, so this is now high-stakes.

### 6. ICO data protection fee

Under the Data Protection (Charges and Information) Regulations 2018, every UK controller that is not exempt must pay an annual fee and register with the ICO. Tiers range from **£52 (Tier 1, micro)** to **£3,763 (Tier 3, large)**. Hemera, as a small controller, will almost certainly be on **Tier 1 (£52/year)** — the threshold is turnover up to £632,000 and no more than 10 staff. Failure to register can incur a penalty of up to £4,000.

**How to register:** via [ico.org.uk/for-organisations/data-protection-fee/register](https://ico.org.uk/for-organisations/data-protection-fee/register/). You'll receive a registration number within a few working days. Display the number in the footer or in the Privacy Policy (both is best).

Note that DUAA (June 2025) triggered a review of the fee regime — the ICO's guidance may change in 2026.

### 7. Modern Slavery Statement

Section 54 of the Modern Slavery Act 2015 requires a statement only from commercial organisations carrying on business in the UK with **total annual turnover of £36 million or more** (calculated globally, including subsidiaries). Hemera will not hit this threshold for a long time. However, the Home Office guidance actively encourages smaller organisations in the supply-chain assurance space to publish a voluntary statement, and Hemera's own clients are likely to ask for one during procurement. **Recommend publishing a voluntary statement** from day one and submitting it to the Modern Slavery Statement Registry — it's a low-effort trust signal that aligns with the product narrative.

### 8. Accessibility Statement

The Public Sector Bodies Accessibility Regulations 2018 only apply to public sector websites. Hemera is private, so it isn't mandatory. However, if Hemera sells to universities, NHS trusts, or local authorities (which it will), those buyers will expect a statement of WCAG 2.2 AA conformance during procurement. Treat it as effectively required.

### 9. Complaints procedure

No general statutory requirement, but UK GDPR Article 77 gives every data subject the right to lodge a complaint with the ICO, and ICO guidance says controllers should make their own complaints mechanism clear first. Include a "How to complain" section in the Privacy Policy.

### 10. Company information in the footer

Under the Companies Act 2006 s.1202 and the Companies (Trading Disclosures) Regulations 2008, every UK limited company must disclose the following on its website:

- Registered company name (including "Limited" or "Ltd")
- Registered company number
- Place of registration (e.g. "Registered in England and Wales")
- Registered office address
- If VAT-registered, VAT number (required on invoices and commonly shown in the footer)

Suggested footer block for HemeraScope:

> Hemera Intelligence Ltd, trading as HemeraScope. Registered in England and Wales, company number [########]. Registered office: [address]. VAT number [if applicable]. ICO registration number [########].

### 11. Sub-processor list

Enterprise buyers (universities, local authorities, large corporates) will refuse to sign a DPA without seeing Hemera's sub-processors. Maintain a page listing: Clerk (auth), hosting provider (e.g. Vercel / Railway / AWS region), database host, email provider, analytics provider, error monitoring. Commit to notifying clients of changes.

### 12. Security / Trust page

Not required by law. Required in practice to close enterprise deals. Cover encryption in transit and at rest, access controls, backup policy, incident response, hosting region, and your sub-processor list.

### 13. AI / methodology disclosure

HemeraScope's supplier risk scoring and carbon calculation methodology should be documented on a public page. UK GDPR Article 22 rights around automated decision-making apply if a risk score produces a legal or similarly significant effect on an individual supplier — unlikely in Hemera's case because outputs target organisations, but worth a sentence in the Privacy Policy confirming it.

### 14. security.txt

A `/.well-known/security.txt` file (RFC 9116) tells security researchers how to responsibly disclose vulnerabilities. Trivial to set up; ticks a box on every enterprise security questionnaire.

---

<a id="part-2"></a>

# Part 2 — Draft Privacy Policy

> **Placeholder format:** items in square brackets `[like this]` must be completed before publication.

## Hemera Intelligence Ltd — Privacy Policy

**Last updated:** [DATE]
**Version:** 1.0

### 1. Who we are and our role under UK data protection law

Hemera Intelligence Ltd ("**Hemera**", "**we**", "**us**", "**our**") is a company registered in England and Wales, company number [########], with its registered office at [address]. We trade under the product name "**HemeraScope**".

We operate in two distinct roles under the UK General Data Protection Regulation ("**UK GDPR**") and the Data Protection Act 2018:

- **Data controller.** We are a data controller for the personal data we collect directly — for example, personal data of visitors to our website, marketing contacts, job applicants, and the authorised user accounts our clients set up to access HemeraScope. This Privacy Policy explains how we handle that data.
- **Data processor.** When we process supplier and spend data that our clients upload into HemeraScope, we act as a data processor on behalf of the client (who is the controller). Our processing of that data is governed by the Data Processing Agreement in place with that client, not by this Privacy Policy. If you are the supplier or employee of a Hemera client and you want to exercise rights over data about you that appears in our client's account, please contact the relevant client first; they will contact us if needed.

We are registered with the Information Commissioner's Office (ICO) under registration number **[########]**.

### 2. What personal data we collect and why

| Category | Examples | Purpose | Lawful basis |
|----------|----------|---------|--------------|
| **Website visitor data** | IP address, browser, pages viewed, session timestamps | Operating and securing the site, measuring traffic, debugging | Legitimate interests (running and improving our website) |
| **Account data** | Name, work email, employer, role, password hash (handled by Clerk) | Creating and securing HemeraScope user accounts | Contract (to deliver the service you signed up for) |
| **Client contact data** | Name, work email, phone, company, role | Responding to enquiries, delivering the service, billing | Contract and legitimate interests |
| **Marketing data** | Email address, preferences | Sending the Hemera newsletter and product updates | Consent (PECR); legitimate interests for B2B direct marketing to existing contacts where consent is not required |
| **Support and correspondence** | Message content, attachments, call notes | Answering support requests and keeping a record | Legitimate interests |
| **Billing data** | Name, billing address, company, payment references (card data is held by our payment processor, not by us) | Taking payment and meeting tax / accounting obligations | Contract; legal obligation (tax records) |
| **Job applicant data** | CV, cover letter, contact details, right-to-work evidence | Recruitment | Legitimate interests; legal obligation (right-to-work checks) |

We do **not** knowingly process special category data (health, ethnicity, political opinion etc.) or criminal offence data in the ordinary course of running HemeraScope. If a client uploads documents that contain such data, we process it strictly as their processor, under their instructions and their lawful basis.

### 3. Where we get personal data from

Most of the personal data we hold comes directly from you — when you fill in a form on our website, sign up for an account, email us, meet us at an event, or engage us as a client.

We also collect:

- **Cookies and similar technologies** when you visit our website (see Part 4 / Cookies section below).
- **Public company registries** — Companies House, the Health and Safety Executive (HSE), the Science Based Targets initiative (SBTi), CDP, and similar public sources. We use these to build the supplier intelligence data in HemeraScope. This data is about **organisations**, not individuals. Where a registry lists a director or company secretary by name (for example on Companies House), that information is already public but we only use it for the purpose for which the registry publishes it and we do not use it for marketing.

### 4. Who we share personal data with

We share personal data only with:

- **Our sub-processors and service providers** — see the current list at [URL]. As of the last update, these include:
  - Clerk, Inc. (user authentication and account management; headquartered in the United States)
  - [Hosting provider, region]
  - [Database host]
  - [Email provider]
  - [Analytics provider, if any]
  - [Error monitoring, if any]
- **Professional advisers** — lawyers, accountants, auditors, insurers — under duties of confidentiality.
- **Authorities** where we are legally required to (for example in response to a valid court order or tax investigation).
- **Successors** in the event of a merger, acquisition or sale of Hemera's business, under appropriate confidentiality and data protection protections.

We do **not** sell personal data. We do not use client data to train general-purpose AI models.

### 5. International transfers

Some of our sub-processors — notably **Clerk, Inc.** (authentication) — are based in the United States. When personal data is transferred out of the UK we use a valid UK GDPR Article 46 transfer mechanism:

- the UK Extension to the EU–US Data Privacy Framework (DPF), where the recipient is DPF-certified; or
- the UK International Data Transfer Agreement (IDTA) or the UK Addendum to the EU Standard Contractual Clauses; and
- supplementary technical and organisational measures (encryption in transit and at rest; access controls; contractual commitments regarding law enforcement requests).

You can ask us for a copy of the safeguards in place for any specific transfer by contacting us at the address in Section 13.

### 6. How long we keep data

| Data | Retention |
|------|-----------|
| Active account data | For the duration of the contract, plus 12 months after termination for reactivation and dispute handling |
| Billing and tax records | 6 years from the end of the accounting period, per HMRC requirements |
| Support correspondence | 3 years from last contact |
| Marketing contacts | Until you unsubscribe, then a minimal suppression record is kept indefinitely |
| Job applicant data (unsuccessful) | 12 months, then deleted unless you consent to longer retention |
| Website analytics | Up to 26 months |
| Security logs | 12 months |

After the stated periods we delete or, where the data is no longer linkable to you, irreversibly anonymise it.

### 7. Your rights under UK GDPR

You have the right to:

- **access** the personal data we hold about you;
- **rectify** inaccurate data;
- **erase** data in certain circumstances ("right to be forgotten");
- **restrict** processing in certain circumstances;
- **data portability** — receive your data in a structured, commonly used format and/or ask us to send it to another controller;
- **object** to processing based on legitimate interests, including direct marketing (which you can object to at any time, no reason needed);
- **withdraw consent** at any time where we rely on consent;
- **not be subject to solely automated decisions** with legal or similarly significant effects — we do not make such decisions about individuals.

To exercise any of these rights, email **[dpo@hemera.xxx]** or write to our registered office. We'll respond within one month.

If you believe we have handled your personal data unlawfully you can complain to the ICO: [ico.org.uk/make-a-complaint](https://ico.org.uk/make-a-complaint/) — 0303 123 1113. We'd appreciate the chance to put things right first, so please contact us before going to the ICO if you can.

### 8. Cookies

We use cookies and similar technologies on our website. Full details are in our [Cookie Statement](#part-4) and you can manage your preferences at any time via the "Cookie settings" link in the footer.

### 9. Security

We take appropriate technical and organisational measures to protect personal data against accidental or unlawful destruction, loss, alteration, unauthorised disclosure or access (UK GDPR Article 32). This includes TLS encryption in transit, encryption at rest, role-based access controls, multi-factor authentication for staff, logging and monitoring, and regular backups. Our current security practices are summarised on our Trust page at [URL].

### 10. Children

HemeraScope is a B2B product not directed at children. We do not knowingly collect personal data from anyone under 16.

### 11. **Anonymised and aggregated data after termination**

When a client stops using HemeraScope, we delete or return the personal and client-identifiable data we hold as their processor, in line with our contractual commitments (see the DPA).

Separately, and **only after the data has been irreversibly anonymised and aggregated** so that it cannot be linked back to the client, any individual supplier, or any natural person, Hemera retains statistical information derived from the work. Examples of the kind of retained information:

- "UK universities in our benchmark have on average **12** transport-sector suppliers."
- "Across all professional-services clients, average modern-slavery risk score in the construction category is **2.3** out of 5."
- "Reported scope 3 emissions intensity for higher-education clients: **x tCO2e / £m spend**."

This retained information takes the form of aggregated statistics, distributions, medians, counts and methodological learnings. It does **not** include:

- the identity of any client (even indirectly — we apply a minimum cohort size before any figure leaves a client's dataset);
- supplier names, company numbers, contact details or any other direct or indirect identifier of a supplier;
- any personal data of any natural person.

We rely on UK GDPR **Recital 26**, which provides that the principles of data protection do not apply to anonymous information — that is, information that does not relate to an identified or identifiable natural person, or to personal data rendered anonymous in such a manner that the data subject is no longer identifiable. Before any supplier or client dataset is added to our aggregated benchmark we apply an anonymisation process designed to meet the "reasonably likely to be used" test in Recital 26, taking account of the means, cost, time and technology available.

Because this retained information is not personal data, it is **not** subject to access, rectification, erasure or portability rights under UK GDPR. Clients acknowledge and agree to this retention in the Terms and Conditions (Section 6) and the DPA.

If our anonymisation methodology changes materially, we will update this policy.

> **Note for the lawyer reviewing this draft:** the adequacy of Hemera's anonymisation technique is the key legal question. The policy wording above is defensive but the substance (minimum cohort size, what fields are stripped, whether any re-identification risk remains via combination with external data) needs to be documented in an internal Data Protection Impact Assessment (DPIA) and reviewed before go-live.

### 12. Changes to this policy

We may update this Privacy Policy. When we do, we will change the "Last updated" date at the top and, for material changes, notify account holders by email and / or in-product.

### 13. Contact us

- **Email:** [privacy@hemera.xxx]
- **Post:** Hemera Intelligence Ltd, [address]
- **Data protection lead:** [name / role] — Hemera does not currently meet the thresholds in UK GDPR Art. 37 requiring a statutory DPO, but [name] is our designated data protection lead.

---

<a id="part-3"></a>

# Part 3 — Draft Terms and Conditions

> These are draft Terms and Conditions for HemeraScope subscribers. They would typically sit as the "HemeraScope Subscription Terms" and be referenced by an order form or Master Services Agreement. A plain website Terms of Use is simpler and separate — see note at the end.

## HemeraScope Subscription Terms

**Last updated:** [DATE]
**Version:** 1.0

### 1. Definitions

- **"Hemera", "we", "us", "our"** — Hemera Intelligence Ltd, a company registered in England and Wales (company number [########]), whose registered office is at [address].
- **"Client", "you", "your"** — the organisation identified as the customer on the Order Form.
- **"Order Form"** — the document signed by you and us that identifies the subscription plan, fees, term and authorised users.
- **"Services"** — the HemeraScope software-as-a-service platform and any professional services described in the Order Form, including carbon footprint reporting, supplier intelligence reports, and related analyst work product.
- **"Client Data"** — any data, including supplier data, spend data, documents and credentials, that you or your authorised users upload to or enter into HemeraScope.
- **"Hemera Data"** — reference data, scores, methodologies, code, reports, analyses, benchmarks, and aggregated anonymous data generated or maintained by Hemera, including data sourced from public registries.
- **"Deliverables"** — reports, dashboards, analyses and other materials Hemera produces for you under the Order Form.
- **"DPA"** — the Data Processing Agreement annexed to these Terms.
- **"Subscription Term"** — the period specified on the Order Form, including any renewal.

### 2. The Services

2.1 Hemera will provide the Services in accordance with these Terms and the Order Form.

2.2 **What HemeraScope is.** HemeraScope is an analytics product that helps organisations understand the carbon footprint of their spend and the environmental, social and governance ("**ESG**") characteristics of their suppliers. Hemera combines Client Data with data from public registries (including Companies House, HSE, SBTi and CDP) and applies methodologies (such as DEFRA emission factors) to produce estimates, scores, and reports.

2.3 **What HemeraScope is not.** The Services do not constitute legal, financial, tax, investment or regulatory advice. Carbon figures produced by HemeraScope are **estimates** prepared using recognised but approximate methodologies and are **not** a substitute for independent verification or assurance required by specific regulatory regimes (for example SECR, CSRD, or mandatory disclosure frameworks requiring third-party audit). You are responsible for any onward use, disclosure, or reliance on the outputs.

2.4 Hemera will use reasonable endeavours to keep the Services available but does not guarantee continuous or error-free operation. Planned maintenance will be notified where practicable.

### 3. Your obligations

3.1 You will:

(a) upload only Client Data you are entitled to upload and have all necessary rights, consents and lawful bases to provide to Hemera for the purposes set out in these Terms;

(b) ensure that Client Data is accurate, complete and up to date to the best of your knowledge;

(c) keep account credentials secure and notify us promptly of any suspected unauthorised access;

(d) comply with the Acceptable Use Policy in Section 12;

(e) comply with all applicable laws, including UK GDPR, in your use of the Services.

3.2 You warrant that providing Client Data to Hemera and Hemera's processing of it under these Terms will not breach any third-party rights, confidentiality obligations, or applicable law.

### 4. Authorised users

4.1 The Order Form specifies the number of authorised users. You are responsible for the acts and omissions of your authorised users as if they were your own.

4.2 Each authorised user must have their own account. Credentials may not be shared.

### 5. Fees and payment

5.1 You will pay the fees set out on the Order Form in accordance with this Section.

5.2 **[Placeholder — fill in:** invoicing cadence (annual in advance / monthly), payment terms (e.g. 30 days from invoice), accepted payment methods, late payment interest (statutory rate under the Late Payment of Commercial Debts (Interest) Act 1998), VAT handling, currency.**]**

5.3 Fees are exclusive of VAT. We may increase fees on renewal by giving you not less than 60 days' notice before the end of the then-current Subscription Term.

### 6. Data ownership, licences, and anonymised retention

6.1 **Client Data.** As between you and us, you own and retain all right, title and interest in and to the Client Data. You grant Hemera a non-exclusive, worldwide, royalty-free licence to host, copy, transmit, display and process the Client Data solely as necessary to provide the Services and the Deliverables, and to comply with this Agreement.

6.2 **Hemera Data, methodology, and Deliverables.** As between you and us, Hemera owns and retains all right, title and interest in and to Hemera Data, Hemera's methodology, software, underlying models, reference datasets, and all intellectual property in Deliverables other than the Client Data embedded within them. On full payment of the fees, Hemera grants you a perpetual, non-exclusive, non-transferable licence to use the Deliverables internally for your own business purposes. You may not redistribute, resell, or publish the Deliverables, or the underlying Hemera Data, without our prior written consent.

6.3 **Aggregated anonymous data.** You acknowledge and agree that Hemera may, during and after the Subscription Term, create and retain aggregated and anonymised statistical information derived from Client Data and from the provision of the Services, provided that such information:

(a) is irreversibly anonymised so that it cannot be linked to you, to any individual supplier, or to any natural person;

(b) is aggregated across a cohort size large enough to prevent re-identification;

(c) does not include supplier names, company numbers, contact details, credentials, or other direct or indirect identifiers.

Hemera may use such aggregated anonymous information indefinitely for any lawful purpose, including benchmarking, research, methodology improvement, and publication of market trends. Because such information is not personal data under UK GDPR Recital 26 and is not Client Data, it is not subject to the return and deletion obligations in Section 14 or the DPA. Hemera's Privacy Policy contains additional detail on this practice.

### 7. Data protection

7.1 Each party will comply with its obligations under the UK GDPR and the Data Protection Act 2018.

7.2 To the extent Hemera processes personal data on your behalf in providing the Services, Hemera does so as your processor and the parties agree the Data Processing Agreement attached as Schedule 1 ("**DPA**"), which is incorporated by reference. In the event of conflict between these Terms and the DPA on matters of personal data, the DPA prevails.

7.3 To the extent Hemera processes personal data as a controller (for example, for its own account administration, marketing, or as described in Section 6.3), Hemera does so in accordance with its Privacy Policy.

### 8. Confidentiality

8.1 Each party will keep the other's Confidential Information confidential, use it only for the purposes of this Agreement, and disclose it only to personnel and advisers who need to know and are under equivalent duties of confidence.

8.2 Confidentiality obligations do not apply to information that is public, received lawfully from a third party, independently developed, or required to be disclosed by law or a regulator.

8.3 Confidentiality obligations survive termination for **five (5) years** or, for trade secrets, for as long as they remain trade secrets.

### 9. Warranties and disclaimers

9.1 Hemera warrants that it will perform the Services with reasonable care and skill.

9.2 **Except as expressly set out in this Agreement, all other warranties, conditions and terms — whether express, implied or statutory — are excluded to the fullest extent permitted by law.** In particular:

(a) Hemera does not warrant that the Services will be uninterrupted or error-free;

(b) carbon, ESG and risk figures produced by HemeraScope are estimates based on published methodologies and Client Data, and Hemera does not warrant that they are suitable for, or accepted by, any specific regulatory, financial reporting, or assurance regime;

(c) Hemera does not warrant the accuracy or completeness of data sourced from public registries or third-party sources.

### 10. Limitation of liability

10.1 Nothing in this Agreement limits or excludes either party's liability for: (a) death or personal injury caused by negligence; (b) fraud or fraudulent misrepresentation; (c) breach of sections 2 or 12 of the Sale of Goods Act 1979 or equivalent; or (d) any other liability that cannot be limited or excluded by law.

10.2 Subject to clause 10.1, neither party will be liable for:

(a) loss of profit;
(b) loss of revenue;
(c) loss of business, goodwill or anticipated savings;
(d) loss or corruption of data (except to the extent such loss is caused by Hemera's breach of the DPA);
(e) indirect or consequential loss.

10.3 Subject to clauses 10.1 and 10.2, each party's total aggregate liability in contract, tort (including negligence), breach of statutory duty or otherwise arising out of or in connection with this Agreement is limited to an amount equal to the **fees paid or payable by you to Hemera under the Order Form in the twelve (12) months immediately preceding the event giving rise to the claim.**

> **Note for legal review:** the 12-month fee cap is standard for UK SaaS but must be tested against the specific services Hemera delivers. If clients rely on Hemera output for regulatory reporting, the commercial risk may warrant a higher cap, a separate liability line for data protection breaches, and a specific carve-out for breaches of confidentiality.

### 11. Term, renewal, and termination

11.1 This Agreement starts on the Effective Date on the Order Form and continues for the Initial Term set out there.

11.2 The Agreement will automatically renew for successive renewal terms equal to the Initial Term unless either party gives written notice of non-renewal at least **sixty (60) days** before the end of the current term.

11.3 Either party may terminate the Agreement immediately on written notice if the other:

(a) commits a material breach that is not capable of remedy, or is capable of remedy but not remedied within 30 days of written notice;
(b) becomes insolvent, enters administration, liquidation or a similar process.

11.4 On termination:

(a) your right to use the Services ends;
(b) any fees already paid are non-refundable, except in the case of termination by you for Hemera's uncured material breach, in which case Hemera will refund fees pro-rata for the unused portion of the current term;
(c) the return and deletion obligations in the DPA apply to personal data;
(d) Hemera's rights under Section 6.3 (aggregated anonymous data) survive.

### 12. Acceptable use

12.1 You will not:

(a) use the Services to upload unlawful, infringing or defamatory content;
(b) attempt to reverse engineer, decompile, or access the source code of the Services, except to the extent permitted by law;
(c) probe, scan, or test the vulnerability of the Services without our prior written consent (please see our responsible disclosure policy);
(d) use the Services to build a competing product;
(e) upload malware.

### 13. Intellectual property

13.1 Nothing in this Agreement transfers ownership of any IP rights. Each party retains its pre-existing IP.

13.2 If you provide feedback about the Services, Hemera may use it freely, including incorporating it into the Services, without obligation to you.

### 14. Return and deletion of Client Data

14.1 For 30 days after termination, you may export your Client Data through the HemeraScope user interface or by written request.

14.2 After that period, Hemera will delete Client Data in accordance with the DPA, except for aggregated anonymous data retained under Section 6.3 and except for data Hemera is required by law to retain.

### 15. Force majeure

Neither party is liable for any failure or delay in performance caused by events beyond its reasonable control, including acts of God, war, terrorism, pandemic, flood, fire, labour disputes, industrial action affecting third-party infrastructure providers, or failure of the internet, provided the affected party promptly notifies the other and uses reasonable endeavours to mitigate.

### 16. Publicity

Hemera may identify you as a client in its marketing materials (for example, by displaying your logo on the HemeraScope website), unless you opt out in writing. Any case study or quotation will be subject to your prior written approval.

### 17. Governing law and jurisdiction

17.1 This Agreement and any dispute or claim (including non-contractual disputes or claims) arising out of or in connection with it or its subject matter or formation are governed by **the laws of England and Wales**.

17.2 The parties submit to the **exclusive jurisdiction of the courts of England and Wales**.

### 18. Dispute resolution

18.1 Before issuing proceedings, the parties will attempt to resolve any dispute through good-faith discussions between senior representatives within 30 days.

18.2 If unresolved, the parties will consider mediation through the Centre for Effective Dispute Resolution (CEDR) before litigation, save that either party may seek urgent injunctive relief at any time.

### 19. Notices

Notices must be given in writing to the addresses on the Order Form (or by email to the designated contact, for routine notices). Legal notices (breach, termination) must be sent by recorded delivery or email with read-receipt confirmation.

### 20. General

20.1 This Agreement, the Order Form and the DPA form the entire agreement between the parties and supersede any prior agreement on the same subject matter.

20.2 No variation is effective unless in writing and signed by both parties.

20.3 No waiver of any right is effective unless in writing.

20.4 If any provision is held to be invalid, the remainder continues in force.

20.5 Neither party may assign this Agreement without the other's prior written consent, except to a successor in a merger, acquisition or sale of substantially all the business.

20.6 Nothing creates a partnership, agency or employment relationship.

20.7 No third-party beneficiaries under the Contracts (Rights of Third Parties) Act 1999.

---

> **Website Terms of Use (separate, shorter document):** in addition to the Subscription Terms above, Hemera should also publish a short **Website Terms of Use** covering: permitted use of the public marketing site, IP in the site content, no warranty on marketing materials, use of cookies (linking to the cookie statement), and governing law. This is not a contract to deliver services; it just governs browsing the website.

---

<a id="part-4"></a>

# Part 4 — Cookie statement and cookie table

## Cookie banner copy

**Banner headline:** We use cookies

**Body:**

> We use cookies to run HemeraScope securely, remember you while you're signed in, and understand how our site is used so we can improve it. Some cookies are strictly necessary and are always on. You can accept or reject everything else, or fine-tune your choices.
>
> You can change your mind at any time via the "Cookie settings" link in the footer. See our [Cookie Statement](/cookies) and [Privacy Policy](/privacy) for full details.

**Buttons (all equally prominent, per PECR / ICO guidance):**

- `Accept all`
- `Reject all`
- `Manage settings`

**Settings panel categories:**

- Strictly necessary (on, cannot be disabled)
- Analytics (off by default)
- Marketing (off by default)

> **Important:** under PECR and ICO guidance, "Reject all" must be as easy and prominent as "Accept all". Do not hide it behind a "Manage settings" click.

## Cookie Statement

**Last updated:** [DATE]

This Cookie Statement explains what cookies and similar technologies Hemera Intelligence Ltd and HemeraScope use, why we use them, and how you can control them.

### What cookies are

Cookies are small text files stored on your device when you visit a website. Similar technologies include localStorage, sessionStorage, pixels and web beacons. Together we refer to them as "cookies".

### Legal basis

We use cookies only where we have a valid legal basis:

- **Strictly necessary cookies** are used under the exception in regulation 6(4) of the Privacy and Electronic Communications (EC Directive) Regulations 2003 ("**PECR**"): they are strictly necessary to provide the service you have requested.
- **All other cookies** require your consent, which you can grant or refuse via the cookie banner and change at any time via the "Cookie settings" link in the footer. We follow current ICO guidance on cookies and the changes introduced by the Data (Use and Access) Act 2025.

### The cookies we use

The table below lists the cookies set by HemeraScope. It is accurate as of the "Last updated" date above. Because some cookies (for example those set by Clerk) may change as the authentication provider updates its product, please check back for updates.

| Cookie / key | Type | Provider | Purpose | Duration | Strictly necessary? |
|---|---|---|---|---|---|
| `__session` | HttpOnly cookie | Clerk | Maintains your signed-in session with HemeraScope | Session (cleared when browser closes) or up to 7 days with "remember me" | Yes |
| `__client_uat` | Cookie | Clerk | Tracks authentication state across subdomains | Session | Yes |
| `__clerk_db_jwt` | Cookie | Clerk | Short-lived session JWT used for authenticated API calls | ~60 seconds, refreshed | Yes |
| `clerk-<id>` | localStorage | Clerk | Stores non-sensitive client state for the Clerk SDK | Persistent until sign-out | Yes |
| `csrf_token` | Cookie | HemeraScope | Cross-site request forgery protection on forms and API | Session | Yes |
| `cookie_consent` | Cookie | HemeraScope | Remembers your cookie preferences so we don't ask again | 12 months | Yes |
| `hs_theme` | localStorage | HemeraScope | Remembers light / dark mode preference | Persistent | Yes (user preference) |
| `_ga`, `_ga_<id>` | Cookie | Google Analytics (only if enabled) | Audience measurement | Up to 13 months | **No — requires consent** |
| `_plausible` (or equivalent) | Cookie / localStorage | [Analytics provider], if used | Privacy-friendly audience measurement | Session | **No — requires consent** |

> **Note:** the exact Clerk cookie names evolve. Before publishing, check the current Clerk documentation or inspect a live HemeraScope session in browser dev tools and update this table to match. If Hemera does not enable third-party analytics at launch, remove the Analytics rows.

### How to manage cookies

- Use the "Cookie settings" link in the HemeraScope website footer to change your choices at any time.
- All modern browsers let you block cookies or clear them. See your browser's help pages for instructions.
- Blocking strictly necessary cookies will break authentication and you will not be able to sign in.

### Third-country transfers

Some cookies are set by third-party providers that operate in the United States (for example Clerk, and Google Analytics if enabled). See the "International transfers" section of our [Privacy Policy](/privacy) for the safeguards that apply.

### Changes

When we change this Cookie Statement we will update the "Last updated" date at the top. Material changes will be notified via the cookie banner.

---

<a id="sources"></a>

# Sources

## ICO and UK government

- [Data protection fee | ICO](https://ico.org.uk/for-organisations/data-protection-fee/)
- [Guide to the data protection fee | ICO](https://ico.org.uk/for-organisations/data-protection-fee/data-protection-fee/)
- [ICO — how to register and pay the data protection fee](https://ico.org.uk/for-organisations/data-protection-fee/register/)
- [ICO — Data protection fee exemptions](https://ico.org.uk/for-organisations/data-protection-fee/data-protection-fee/exemptions/)
- [UK GDPR guidance and resources | ICO](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/)
- [ICO — What privacy information should we provide?](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/)
- [ICO — Right to be informed checklists](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/checklists/)
- [ICO — How do you determine whether you are a controller or processor?](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/controllers-and-processors/controllers-and-processors/how-do-you-determine-whether-you-are-a-controller-or-processor/)
- [ICO — What are 'controllers' and 'processors'?](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/controllers-and-processors/controllers-and-processors/what-are-controllers-and-processors/)
- [ICO — Cookies and similar technologies (PECR)](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/)
- [ICO — Guidance on the use of storage and access technologies](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-the-use-of-storage-and-access-technologies/)
- [ICO — PDF: Guidance on the use of cookies and similar technologies](https://ico.org.uk/media2/kz0doybw/guidance-on-the-use-of-cookies-and-similar-technologies-1-0.pdf)
- [GOV.UK — Publish an annual modern slavery statement](https://www.gov.uk/guidance/publish-an-annual-modern-slavery-statement)

## Legislation

- [UK GDPR (as retained) | legislation.gov.uk](https://www.legislation.gov.uk/eur/2016/679/introduction)
- [Modern Slavery Act 2015 — s.54 Transparency in Supply Chains regulations](https://www.legislation.gov.uk/ukdsi/2015/9780111138847)
- [Recital 26 — UK GDPR | Mishcon de Reya](https://www.mishcon.com/uk-gdpr/recital/no-26)
- [Article 4 GDPR — definitions](https://gdprhub.eu/Article_4_GDPR)

## Clerk (identified sub-processor)

- [Clerk — Data Processing Addendum](https://clerk.com/legal/dpa)
- [Clerk — Supplemental Notice For Residents Of The EEA, Switzerland, Or The UK](https://clerk.com/legal/gdpr)

## Context on recent changes (Data (Use and Access) Act 2025)

- [ICO Updates Cookie Consent Rules Under the Data (Use and Access) Act — Measured Collective](https://measuredcollective.com/ico-updates-cookie-consent-rules-under-the-data-use-and-access-act-what-organisations-need-to-do-now/)
- [UK ICO's updated guidance for new exceptions to cookie consents — Clifford Chance](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/09/uk-ico-s-updated-guidance-for-new-exceptions-to-cookie-consents-.html)
- [Cookie Consent: Unpacking the UK ICO's Proposed New Approach — Skadden](https://www.skadden.com/insights/publications/2025/08/cookie-consent)
- [Key Insights from the ICO's Updated Draft Cookies Guidance Following DUAA — Burges Salmon](https://www.burges-salmon.com/articles/102l7bs/key-insights-from-the-icos-updated-draft-cookies-guidance-following-duaa/)
- [UK ICO Publishes Guidance on Recognized Legitimate Interest Basis — Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/uk-ico-publishes-guidance-on-recognized-legitimate-interest-basis)

## Commentary on UK Modern Slavery Act (context)

- [UK Modern Slavery Act — Skadden](https://www.skadden.com/insights/publications/2024/09/uk-modern-slavery-act)
- [Section 54: the evolution from voluntary to mandatory? — Penningtons](https://www.penningtonslaw.com/insights/section-54-of-the-uks-modern-slavery-act-the-evolution-from-voluntary-to-mandatory/)

## Commentary on controller / processor

- [SaaS Providers: Data Protection — Em Law](https://emlaw.co.uk/saas-providers-data-protection-compliance-software-technology/)
- [ICAEW — UK GDPR Data Processor or Controller?](https://www.icaew.com/technical/tas-helpsheets/practice/gdpr-data-processor-or-data-controller)
