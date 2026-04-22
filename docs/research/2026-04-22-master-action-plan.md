# HemeraScope — Action Plan

Nico (CTO), Tom (COO). Last updated 2026-04-22.

Companies House is with Tom — everything below can be done independently. When the company number arrives, Claude fills all 25 placeholders in one commit.

---

## Do now (doesn't need Companies House)

### 1. Test the website
Open hemerascope.com and go through everything:
- Landing page loads, all sections, footer links work
- Sign in/up works (if not: add hemerascope.com in Clerk dashboard → Domains)
- Dashboard: client queue, suppliers page, bin, upload, QC cards, Excel export
- If API calls fail: check `NEXT_PUBLIC_API_URL` is set in Vercel env vars to your Render URL

### 2. Test supplier matching
Upload a CSV with known names (DHL, Tesco, Amazon). Process it. Check:
- Matched suppliers are correct (active entities, not dissolved)
- Companies House lookup on admin suppliers page returns sensible results
- Enrichment runs and generates findings

### 3. Test supplier enrichment
Pick a supplier, click "Rerun analysis". Check all 13 layers return data or graceful "no data". Check the Hemera Score and findings look right.

### 4. ICO registration
ico.org.uk/for-organisations/register. £40/year. 10 minutes. You get a registration number back — goes in the legal pages and footer.

### 5. Cookie consent banner
Not built yet. Legally needed before public launch. Ask Claude to build it — takes about an hour. Simple banner: Accept / Reject / Manage. Stores choice in a cookie.

### 6. Build robots.txt and sitemap
Ask Claude — 2 minutes. Tells Google what to crawl and what not to (block /dashboard, allow landing + legal pages).

### 7. Favicon and social sharing image
Need a favicon and an og:image (1200x630px) so links shared on LinkedIn/X show a proper preview. Do this during the brand session with Tom.

### 8. Enable MFA on everything
GitHub, Vercel, Render, Clerk dashboard, Cloudflare, email accounts. Takes 30 minutes. Required for Cyber Essentials.

### 9. Run dependency audits
```bash
cd /Users/nicohenry/Documents/Hemera && .venv/bin/pip audit
cd dashboard && npm audit
```
Fix anything flagged. Cyber Essentials requires patches within 14 days.

---

## Do this week

### 10. Logo and brand session with Tom
- Favicon (16x16, 32x32, 180x180)
- og:image for social sharing
- Logo variations (dark bg, light bg, icon-only, wordmark)
- Slide deck template for pitches
- Confirm the teal/slate/amber palette is final

### 11. Imperial Entrepreneurship Lab call
Ask about:
- Legal clinics for startups (free solicitor access?)
- IP protection for your methodology
- Upcoming demo days or investor intros
- Connection to Imperial sustainability research groups

Funding to ask about:
- Innovate UK Smart Grants (up to £500k)
- Innovate UK SBRI (government problem-solving contracts)
- Carbon Trust green innovation programmes
- EIC Accelerator (up to €2.5M, UK eligible via Horizon)
- Imperial's own grants/programmes

Legal questions for them:
- Anonymised supplier data retention (Recital 26) — is it truly anonymised?
- Controller vs processor classification
- DPA template needs
- AI disclosure requirements

### 12. Solicitor review
Send them: Privacy Policy, Terms & Conditions, Cookie Statement, the full legal research doc (`docs/research/2026-04-12-legal-statements.md`), Modern Slavery Statement.

Tell them: UK SaaS company, processes supplier/spend data for carbon reporting, uses AI (Anthropic Claude), stores data on US services (Render, Vercel), wants to publish within 2 weeks, also needs a DPA template for clients.

Key issues they must check: anonymised supplier retention clause, 12-month liability cap, PECR/DUAA cookie compliance, US data hosting adequacy.

£500-2,000. Ask Imperial if they have recommendations.

### 13. Nico — start GHG Protocol training
Free online course at ghgprotocol.org. Covers the Corporate Standard — the foundation of everything HemeraScope does. Do this before your first real client engagement.

---

## Do next week

### 14. Cyber Essentials
Book via CyberSmart (cybersmart.co.uk). ~£320+VAT. They guide you through the 80-question self-assessment. 2-6 weeks to certificate. Full prep checklist in `docs/research/2026-04-22-cyber-essentials-summary.md`.

### 15. UNGC Participant
unglobalcompact.org/participation/join. Tom signs the commitment letter. Free under $1M revenue. You get the "We Support the UN Global Compact" logo. Annual report required.

### 16. Living Wage accreditation
livingwage.org.uk/accredited-living-wage-employers. Free for small employers. Commit to the real Living Wage (£12/hr UK, £13.15/hr London — not the government minimum). Badge for your website. Directly relevant for an ESG company.

---

## Do in weeks 3-4

### 17. About Us section
Both founders on the landing page:
- Nico Henry — Co-founder & CTO
- Tom [surname] — Co-founder & COO
- Photo, 1-2 lines each, why you built Hemera

### 18. Video
Script is in `docs/research/2026-04-22-video-brief.md`. Both founders on camera, 2-3 minutes, iPhone is fine. Replaces the placeholder on the landing page.

### 19. Client list and strategy

**Target segments:**
1. UK Students' Unions (~130 affiliated with NUS, sustainability mandates, price-sensitive)
2. UK Universities (HEFE carbon reporting requirements, £5k-50k budgets)
3. UK Charities & CICs (increasing ESG scrutiny, £500-5k)
4. UK SMEs under supply chain pressure (Scope 3 requirements from large buyers, £2k-20k)
5. UK Local Councils (net zero commitments, Social Value Act, £10k-50k)

**How to build the list:**
- NUS directory for SU contacts
- LinkedIn Sales Navigator (Sustainability Officer, UK, education)
- Charity Commission search (charities >£1M income)
- Contracts Finder (sustainability/carbon tenders)
- B Corp directory (already ESG-minded companies)

### 20. Cost strategy
Stay on free tiers for now. When you get your first paying client:
- Render → $7/mo (avoids 30-second cold starts)
- At 5+ clients: Vercel Pro $20/mo + Clerk Pro $25/mo
- Total at 5 clients: ~$60/month

### 21. Launch marketing

**LinkedIn (main channel):**
- Both founders post from personal accounts (5-10x more reach than company pages)
- Nico: technical angle (confidence intervals, methodology)
- Tom: business angle (why supply chains need transparency)
- Join: UK Sustainability Professionals, ESG Network, Supply Chain groups

**Also:**
- Company LinkedIn page for product updates and case studies
- Instagram for visual brand building (infographics, behind-the-scenes)
- Newsletter (Substack or Buttondown) — monthly supply chain ESG insights
- PR: pitch to BusinessGreen, Edie, GreenBiz. Angle: "Imperial-backed startup brings academic rigour to carbon reporting"
- Webinar: "How to measure your carbon footprint with confidence intervals" — directly demos the product

---

## Do in month 2+

### 22. More accreditations

| What | Cost | Time | Why |
|------|------|------|-----|
| Cyber Essentials Plus | £1,500-2,500 | 2-4 weeks after CE | Technical audit, needed for some gov contracts |
| IEMA Corporate Member | £300-600/year | Immediate | Professional body for environmental management |
| Carbon Trust Standard | £2,000-5,000 | 3-6 months | Validates your carbon measurement approach |
| Planet Mark | £1,000-3,000/year | 2-3 months | Carbon reduction commitment certification |
| Disability Confident Employer | Free | 2-4 weeks | Government scheme, good optics |
| B Corp | Free to assess, £500-25k to certify | 12-18 months | Long game but very strong signal |
| CDP Accredited Solutions Provider | Application fee | 2-3 months | If helping clients with CDP disclosure |

### 23. Ongoing maintenance

| When | What |
|------|------|
| Every 2 weeks | Dependency security patches (`pip audit`, `npm audit`) |
| Monthly | Review sub-processor list, update if changed |
| Quarterly | Review legal pages, update dates |
| Annually | Renew ICO (£40), Cyber Essentials (£320), UNGC report |
| Every June | Update DEFRA conversion factors (new set published annually) |

---

## When Companies House number arrives

Give Claude these values and all 25 placeholders get filled in one commit:

```
Company number:        _______________
Registered address:    _______________
ICO registration:      _______________  (after ICO registration)
Privacy email:         _______________  (e.g. privacy@hemerascope.com)
Security email:        _______________
Accessibility email:   _______________
Whistleblowing email:  _______________
Founder name (Tom):    _______________
Effective date:        _______________  (set when solicitor approves)
Payment terms:         _______________  (e.g. "Net 30, GBP, VAT inclusive")
```
