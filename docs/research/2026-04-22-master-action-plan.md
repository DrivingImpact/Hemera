# HemeraScope — Master Action Plan

**Last updated:** 2026-04-22
**Founders:** Nico (CTO), Tom (COO)

---

## What is robots.txt?

A `robots.txt` file sits at the root of your website (hemerascope.com/robots.txt) and tells search engines what they can and can't crawl. Without it, Google and others may or may not index your pages — you have no control. With it, you can:

- Allow all public pages to be indexed (landing, legal pages)
- Block private pages (dashboard, admin, API endpoints)
- Point to your sitemap so Google finds all your pages

**I'll build this for you — takes 2 minutes.**

A `sitemap.xml` lists every public URL on your site with priority and update frequency. Google reads it to know what to crawl. Next.js can auto-generate it.

---

## Action Plan — Prioritised

### THIS WEEK (Before Launch)

#### 1. Companies House Registration — Today/Tomorrow
- Register Hemera Intelligence Ltd at **gov.uk/set-up-limited-company**
- Cost: £12 (online) or £30 (paper)
- You'll get a company number immediately on online registration
- **Give Nico the company number + registered address → Claude fills all 25 placeholders in one commit**

#### 2. Check Everything on the Webpage Works
What to check (hemerascope.com):

**Landing page:**
- [ ] All sections load (hero, stats, how it works, glass box, standards, CTA, footer)
- [ ] Footer links to /legal/* pages work
- [ ] Sign in / sign up buttons work (Clerk auth on the new domain)
- [ ] Mobile layout (test at 375px width)
- [ ] Video placeholder — decide: keep or remove

**Dashboard (after sign in):**
- [ ] Client queue loads, shows engagements
- [ ] Delete button + confirmation works
- [ ] Info dropdown shows uploader details
- [ ] Admin suppliers page loads, search works
- [ ] Companies House lookup works
- [ ] Supplier detail page loads, enrichment layers expand
- [ ] AI Intelligence buttons work (Max copies prompt, API calls Claude)
- [ ] Admin bin page works (restore + permanent delete)
- [ ] Excel export downloads a valid .xlsx
- [ ] Emission factor verify modal opens with DEFRA table
- [ ] QC card flow works (swipe pass/fail)
- [ ] Upload flow works (both spend and activity data types)

**If anything fails, it's likely:**
- CORS (backend not allowing hemerascope.com) — already fixed
- Clerk domain (need to add hemerascope.com in Clerk dashboard → Domains)
- `NEXT_PUBLIC_API_URL` not set in Vercel env vars → needs Render backend URL

#### 3. Fuzzy Name / AI Name Check
The supplier matcher uses fuzzy matching (SequenceMatcher, 0.85 threshold) with status-based ranking (active > dissolved). The DHL bug was fixed in the April 12 batch.

**To verify it's working well:**
- [ ] Upload a test CSV with known supplier names (DHL, Tesco, Amazon, local suppliers)
- [ ] Check the client queue → process → verify matched suppliers are correct
- [ ] In admin suppliers page, search for a company → verify results are sensible
- [ ] Try Companies House lookup for edge cases (common names, abbreviations)

**If matching is poor, improvements could include:**
- Normalisation (strip Ltd, Limited, PLC, Inc before matching)
- Multiple candidate matching (currently picks best above threshold)
- AI classification fallback for ambiguous names (add as an option, not automatic)

#### 4. Recheck Supplier Method
The 13-layer enrichment protocol. Verify by enriching a known supplier and checking:
- [ ] Layer 1 (Corporate Identity) returns Companies House data
- [ ] Layer 2 (Ownership & Sanctions) checks PSCs and OpenSanctions
- [ ] Layer 3 (Financial Health) pulls charges, gender pay gap
- [ ] Layer 4 (Carbon & Environmental) checks Environment Agency
- [ ] Layer 5 (Labour & Ethics) checks modern slavery registry
- [ ] Remaining layers return data or graceful "no data found"
- [ ] Hemera Score calculates correctly
- [ ] Findings are generated for each data point

#### 5. ICO Registration
- **Go to:** ico.org.uk/for-organisations/register
- **Cost:** £40/year (Tier 1)
- **Time:** 10 minutes, number within days
- **Blocker:** Number needed for legal pages and landing footer

#### 6. Cookie Consent Banner
- **Status:** Not built yet
- **Recommendation:** Build a simple one (Nico, ~1 hour with Claude)
- Only essential cookie is Clerk session (doesn't need consent)
- Banner is for future-proofing and showing compliance
- Store preference in `hemera_consent` cookie

#### 7. Imperial Entrepreneurship Lab Call
**Topics to cover:**

*Legal advice:*
- Review your Privacy Policy's anonymised supplier retention clause (Recital 26 — this is the legally novel bit)
- Controller vs processor classification for HemeraScope
- DPA template for client contracts
- Whether the 12-month liability cap in T&Cs is enforceable for your specific services
- DUAA 2025 impact on your cookie approach

*AI and innovation funds:*
- Innovate UK Smart Grants (up to £500k for disruptive R&D)
- Innovate UK SBRI (Small Business Research Initiative) — government problem-solving contracts
- UKRI Future Leaders Fellowships (if either founder is doing research)
- EIC Accelerator (EU, up to €2.5M equity + grant — UK eligible post-Brexit via Horizon association)
- Creative Destruction Lab (CDL) — structured mentorship programme
- Carbon Trust programmes — they fund green innovation specifically
- Imperial Enterprise Lab's own grants/investment programmes
- Nesta challenges (if any ESG/sustainability challenges are running)

*Questions to ask Imperial:*
- Do they have legal clinics for startups? (Many university enterprise labs do)
- Can they connect you with IP lawyers? (Your methodology may be protectable)
- Any upcoming demo days or investor introductions?
- Access to Imperial's sustainability research groups for academic validation?

#### 8. Solicitor Review — What They Need

Send them a package:

**Documents to review (priority order):**
1. **Privacy Policy** — `dashboard/app/legal/privacy/page.tsx` (or export as PDF). Key issue: anonymised supplier retention clause under Recital 26. Ask: is this truly anonymised or merely pseudonymised?
2. **Terms & Conditions** — `dashboard/app/legal/terms/page.tsx`. Key issue: 12-month liability cap, IP ownership of anonymised insights, termination provisions.
3. **Cookie Statement** — `dashboard/app/legal/cookies/page.tsx`. Key issue: PECR compliance, DUAA 2025 impact.
4. **Full legal research doc** — `docs/research/2026-04-12-legal-statements.md` (613 lines, all the legal reasoning and flagged issues).
5. **Modern Slavery Statement** — voluntary, but review for accuracy.

**Tell the solicitor:**
- You're a UK SaaS company processing client spend/supplier data for carbon reporting
- You use AI (Anthropic Claude) for classification and analysis — they should check the AI disclosure
- You store data on US-hosted services (Render, Vercel, Anthropic) — they should check adequacy decisions
- You want to publish these on hemerascope.com within 2 weeks
- You also need a standalone DPA template for client contracts

**Expected cost:** £500-2,000 for the full review.
**Look for:** A solicitor who specialises in tech/SaaS data protection law, ideally familiar with ESG or sustainability sector. Imperial's enterprise lab may have recommendations.

---

### NEXT WEEK

#### 9. Logo & Brand Guidelines (with Tom)
- Review `docs/brand-guidelines.md` — existing guidelines are documented
- Design deliverables needed:
  - **Favicon** (16x16, 32x32, 180x180 Apple touch icon)
  - **og:image** (1200x630px for social sharing)
  - **Logo variations** (dark bg, light bg, icon-only, wordmark)
  - **Slide deck template** (for pitches, client presentations)
  - **Report cover page** (for PDF reports delivered to clients)
- Decide: is the current teal/slate/amber palette final?
- Decide: HemeraScope wordmark typography — Plus Jakarta Sans bold, or custom?

#### 10. Cyber Essentials
- **Prep this week** (enable MFA, run audits, document services)
- **Book assessment next week** via CyberSmart (cybersmart.co.uk) — they guide you through it
- **~£320+VAT, 2-6 weeks**

#### 11. UNGC Participant
- **Go to:** unglobalcompact.org/participation/join
- **CEO (Tom) signs** the commitment letter
- **Free** for companies under $1M revenue
- **Yields:** "We Support the UN Global Compact" logo
- **Requirement:** Annual Communication on Progress report

#### 12. Living Wage Accreditation
- **Go to:** livingwage.org.uk/accredited-living-wage-employers
- **Commit to paying** the real Living Wage (currently £12.00/hr UK, £13.15/hr London)
- **Cost:** Free for small employers (under 10 staff, turnover under £1M)
- **Yields:** Living Wage Employer badge/logo
- **Why it matters:** Directly relevant for an ESG consultancy — demonstrates you practice what you preach on labour standards. Buyers in procurement/sustainability notice this.
- **Note:** This is about the *real* Living Wage (set by Living Wage Foundation), not the government minimum. They're different.

---

### WEEKS 3-4

#### 13. Client Potential List & Strategy

**Target segments (priority order):**

1. **UK Students' Unions** (current pilots)
   - There are ~130 SUs in the UK affiliated with NUS
   - Many have sustainability officers and carbon reporting mandates
   - Price-sensitive but reputation-conscious
   - Referral potential: one good report → other SUs hear about it

2. **UK Universities** (natural step up from SUs)
   - HEFE (Higher Education Funding England) requires carbon reporting
   - Procurement teams deal with hundreds of suppliers
   - Budgets: £5k-50k for sustainability consulting

3. **UK Charities & CICs**
   - Charity Commission regulated, increasing ESG scrutiny
   - Often have grant-funded sustainability projects
   - Price range: £500-5,000

4. **UK SMEs with supply chain pressure**
   - Companies supplying to large corporates who require Scope 3 data from suppliers
   - Construction, food & drink, manufacturing sub-contractors
   - Price range: £2,000-20,000

5. **UK Local Councils**
   - Net zero commitments, public procurement obligations
   - Must comply with Social Value Act 2012
   - Price range: £10,000-50,000 (via frameworks or direct procurement)

**Strategy for list building:**
- NUS directory for SU contacts
- LinkedIn Sales Navigator (filter: Sustainability Officer/Manager, UK, education sector)
- Charity Commission search for charities with >£1M income
- GOV.UK Contracts Finder for upcoming sustainability/carbon tenders
- B Corp directory for companies already ESG-minded (they value supply chain intelligence)

#### 14. About Us
**For the landing page:**
- Nico Henry — Co-founder & CTO. [Add: background, what he brings, why ESG]
- Tom [surname] — Co-founder & COO. [Add: background, what he brings, why ESG]
- Photo of both founders (professional but approachable)
- 2-3 sentences on why Hemera exists, what drove you to build it

#### 15. Video
See `docs/research/2026-04-22-video-brief.md` — full script and production notes.
Both founders on camera. 2-3 minutes. iPhone is fine.

#### 16. Nico — Carbon Audit Training
Options:
- **GHG Protocol Corporate Standard course** — ghgprotocol.org (free online modules)
- **IEMA Carbon Management** — iema.net (£300-600, accredited)
- **Carbon Trust training** — carbontrust.com (various courses)
- **CDP Accredited Provider training** — if you want to help clients with CDP disclosure
- **Recommended first:** GHG Protocol free online course (establishes the foundation), then IEMA for formal accreditation

---

### MONTH 2+

#### 17. Cost Strategy & Paid Tiers

**Current infrastructure costs:**
| Service | Free Tier | First Paid Tier | When You Need Paid |
|---------|-----------|-----------------|-------------------|
| **Vercel** | Hobby (free) | Pro ($20/mo) | When you need custom domains with SSL, team access, analytics |
| **Render** | Free (spins down after inactivity) | Starter ($7/mo) | When you need always-on (no cold starts), more RAM, custom domains |
| **Clerk** | Free (10,000 MAUs) | Pro ($25/mo) | When you need custom branding, remove Clerk branding, SSO |
| **PostgreSQL** | Render free (256MB) | Starter ($7/mo) | When you hit 256MB or need backups |
| **Anthropic API** | Pay per use | Pay per use | Already paying — ~$0.003 per classification, ~$0.05 per risk analysis |
| **Domain** | N/A | ~$10/year | Already registered |

**Recommendation:**
- **Now:** Stay on free tiers. Vercel Hobby + Render free is fine for early clients.
- **First paying client:** Upgrade Render to Starter ($7/mo) to avoid cold starts (free tier spins down after 15 min inactivity — first request takes 30-60 seconds to wake).
- **5+ clients:** Upgrade Vercel to Pro ($20/mo) for team access and analytics. Upgrade Clerk to Pro ($25/mo) for custom branding.
- **Total at 5 clients:** ~$60/month infrastructure. Negligible vs your pricing.

#### 18. Launch Strategy

**LinkedIn (primary channel):**
- Both founders post about the launch — personal accounts get 5-10x more reach than company pages
- Nico: technical angle — "We built a carbon footprint tool that shows you the confidence interval, not just a number"
- Tom: business angle — "Why we started HemeraScope and what we found in UK supply chains"
- Company page: product updates, case studies (anonymised), methodology insights
- Join and post in: UK Sustainability Professionals, ESG Network, Supply Chain Sustainability groups
- Target connections: Sustainability Officers, Procurement Managers, CFOs at universities and charities

**Instagram:**
- Secondary channel — less B2B but good for brand building
- Visual: infographics from reports (anonymised), behind-the-scenes, team shots
- Stories: quick tips on carbon reporting, sustainability news
- Less frequent than LinkedIn — 2-3 posts/week vs daily LinkedIn

**Other channels:**
- **X/Twitter** — sustainability community is active. Share methodology insights.
- **Newsletter** — set up a Substack or Buttondown. Monthly "State of Supply Chain ESG" with insights from your data (anonymised). Builds authority.
- **PR** — reach out to: BusinessGreen, Edie, The Sustainability Report, GreenBiz. Angle: "Imperial-backed startup brings academic rigour to carbon reporting"
- **Events** — Sustainability Live (NEC Birmingham), ESG Investor Conference, university sustainability officer networks
- **Webinars** — host a free "How to measure your carbon footprint with confidence intervals" session. Directly demonstrates the product.

#### 19. Other Accreditations to Consider

| Accreditation | Relevance | Cost | Timeline |
|---------------|-----------|------|----------|
| **Living Wage Employer** | High — ESG credibility | Free (small employer) | 2-4 weeks |
| **Carbon Trust Standard** | Very high — validates your carbon measurement approach | £2,000-5,000 | 3-6 months |
| **IEMA Corporate Member** | High — professional body for environmental management | £300-600/year | Immediate |
| **GHG Protocol Scope 3 Evaluator** | Niche — demonstrates deep methodology knowledge | Training cost only | 1-2 months |
| **Disability Confident Employer** | Good — government scheme, free | Free | 2-4 weeks |
| **Investors in People** | Good — demonstrates people management quality | £2,000-5,000 | 3-6 months |
| **Planet Mark** | High — certification for carbon reduction commitment | £1,000-3,000/year | 2-3 months |
| **CDP Accredited Solutions Provider** | Very high if you help clients with CDP | Application fee | 2-3 months |

**Recommended priority:** Living Wage (free, immediate) → IEMA membership (professional credibility) → Carbon Trust or Planet Mark (validates your core offering)

---

## Quick Reference — What to Do Tomorrow

1. Companies House registration (if not already done)
2. Fill the placeholder values form (Part 5 of launch-readiness.md)
3. Enable MFA on all accounts (GitHub, Vercel, Render, Clerk, Cloudflare, email)
4. Test hemerascope.com in a browser — run through the checklist in section 2
5. Logo/brand session with Tom
6. ICO registration (ico.org.uk)
