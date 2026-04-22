# Domain registration options for hemerascope.com

Researched 2026-04-12 for Hemera (UK-based ESG consultancy).
Goal: register the domain cheaply, no email/hosting needed.

## Availability of hemerascope.com

**Not definitively confirmed.** This research environment denied direct WHOIS and registrar website fetches, so I could not run a live WHOIS query. What I can say:

- Google indexes no pages at `hemerascope.com`. A search for `"hemerascope.com"` returns zero matches for that exact host; the closest indexed site is the unrelated Spanish training centre `hemeroscopea.com`.
- The literal word "hemerascope" only appears in a 1899 French advert for an antique photographic device — no current commercial usage.
- This is a strong but not conclusive signal that the domain is unregistered or parked. **Verify manually** at one of:
  - <https://www.whois.com/whois/hemerascope.com>
  - <https://lookup.icann.org/>
  - <https://domains.cloudflare.com/> (will show availability + at-cost price)

Assuming it is available, the comparison below applies.

## Summary table (.com, USD, 2026 prices)

| Registrar | Year 1 | Renewal | WHOIS privacy | Notes |
|---|---|---|---|---|
| **Cloudflare Registrar** | ~$10.44 | ~$10.44 | Free | At-cost, no markup. Requires using Cloudflare nameservers. New registrations now supported (historically transfer-only). |
| **Porkbun** | ~$11.06 | ~$11.06 | Free | Flat pricing, no renewal hike. Free SSL, email forwarding, WHOIS privacy. |
| **Namecheap** | ~$6.79–9.58 (promo) | ~$13.98–18.48 | Free for life | Biggest year-1/renewal gap of the "good" registrars. Reliable otherwise. |
| **Name.com** | ~$8.99 (promo) | ~$13.98+ | Bundled in "Advanced Security" add-on | Privacy bundling makes effective price higher than headline. |
| **IONOS** | £1 / ~$1 (promo) | ~$20 | Free (varies) | Very cheap year 1, steep renewal. 2026 price adjustment in effect. UK entity, GBP billing available. |
| **GoDaddy** | $0.01–4.99 (promo, often 2-yr lock-in) | ~$18.99–24.99 | Free | Aggressive upsells at checkout (SSL, email, "protection plans"). Highest renewal of the mainstream options. |
| **Squarespace Domains** | ~$20 | ~$20 (same) | Free | Transparent flat pricing. Inherited Google Domains users. Higher floor than Porkbun/Cloudflare. |
| **Gandi** | ~$15.50 | ~$24.50–38.38 | Free | Privacy-friendly EU registrar but .com renewal is notably high post-2023 pricing changes. |

Prices from vendor pages, TLD-List, domaindetails.com, and vendor comparison aggregators as of April 2026. Exchange rates apply for UK billing. All figures exclude the $0.18–0.20 ICANN fee.

## Recommended shortlist

1. **Cloudflare Registrar** — cheapest at-cost, no markup, no renewal surprise. The main caveat: you have to use Cloudflare's nameservers. For a consultancy domain with no email/hosting, that's fine.
2. **Porkbun** — a close second; more flexible (bring your own DNS), free WHOIS privacy, free SSL, email forwarding, flat renewal. Excellent UX and support reputation.
3. **Namecheap** — fine if you already have an account, but the renewal jump means Porkbun beats it over any multi-year horizon.

Avoid: GoDaddy (renewal + upsells), Gandi (renewal price), IONOS (renewal jump), Squarespace (floor price).

## Details by registrar

### Cloudflare Registrar
- Year 1: ~$10.44 (at-cost, passed through from Verisign)
- Renewal: ~$10.44 (same — no markup, ever)
- WHOIS privacy: free, on by default
- DNS: requires Cloudflare DNS; this is free and actually very good (fast anycast, unlimited records, DNSSEC)
- Caveats: must use Cloudflare nameservers; cannot use another DNS provider while registered here. Free Cloudflare account required.
- **Cloudflare .com pricing not fully price-confirmed in this session** — verify at <https://domains.cloudflare.com/> before buying. The $10.44 figure is from third-party trackers (tldprice.org, tldspy.com) and Cloudflare's own "low-cost domain" page.

### Porkbun
- Year 1: ~$11.06 (no promo needed; sometimes $9.xx promo)
- Renewal: ~$11.06 (flat; Porkbun explicitly markets "no renewal hikes")
- WHOIS privacy: free ("Private By Design", on by default)
- DNS: free, full-featured. You can also use external DNS.
- Extras included free: SSL certificate, URL forwarding, email forwarding, WHOIS privacy
- Caveats: none of note. Independent US company, good reputation in developer/indie community.

### Namecheap
- Year 1: ~$6.79 (promo) to $9.58 (standard first year)
- Renewal: ~$13.98 (with recent reports up to $18.48)
- WHOIS privacy: free for life (rebranded "Domain Privacy")
- DNS: free basic DNS, FreeDNS option, can use external DNS
- Caveats: largest year-1/renewal gap among the "reputable" options. Fine if you're happy to migrate later.

### Squarespace Domains (ex-Google Domains)
- Year 1: ~$20 (no intro promo on .com)
- Renewal: ~$20 (flat, same price)
- WHOIS privacy: free, automatic
- DNS: full DNS control, SSL included, 100 email forwards included
- Caveats: highest floor among flat-priced registrars. Clean UI, solid reliability — but you pay for it.

### GoDaddy
- Year 1: $0.01–$4.99 (promo, usually bundled into a 2-year deal where year 2 is ~$18.99)
- Renewal: ~$18.99–$24.99
- WHOIS privacy: free (since 2022)
- DNS: free basic DNS
- Caveats: aggressive checkout upsells (SSL, "Full Domain Protection", Microsoft 365). Highest renewal of the mainstream options. Also owns Route 53's competition for enterprise — not relevant here. Generally not recommended for a no-frills single domain.

### IONOS
- Year 1: £1 / ~$1 (heavy promo, UK entity)
- Renewal: ~£15–£16 / ~$20
- WHOIS privacy: free on most TLDs
- DNS: free basic DNS
- Caveats: large year-1/renewal gap. IONOS ran a 2026 price adjustment (notified by email). UK billing available in GBP, which is convenient for a UK consultancy filing expenses in sterling.

### Gandi
- Year 1: ~$15.50
- Renewal: ~$24.50–$38.38 (sources vary; notably higher since their 2023 pricing overhaul)
- WHOIS privacy: free, default
- DNS: free, good tooling
- Caveats: historically the privacy-friendly EU-focused choice, but .com renewals became uncompetitive post-2023. Worth it if you specifically want EU jurisdiction; otherwise overpriced.

### Name.com
- Year 1: ~$8.99 (promo)
- Renewal: ~$13.98+
- WHOIS privacy: **not free standalone** — bundled into the "Advanced Security" product, adding cost
- DNS: free basic DNS
- Caveats: hidden-ish privacy cost pushes the effective price above Porkbun. Owned by Donuts/Identity Digital.

## Alternative TLDs

For a UK-based ESG consultancy, the "scope" in the brand is a strong pointer toward `.com` or `.earth`/`.eco` for sustainability signalling. Prices below are rough — verify at the registrar before buying.

| TLD | Cheapest registrar | Year 1 | Renewal | Notes |
|---|---|---|---|---|
| `.com` | Cloudflare | ~$10.44 | ~$10.44 | Baseline; universally recognised. |
| `.co` | Porkbun | ~$8.58 (promo) | ~$25.97 | Renewal ~2.5x. .co is a Colombian ccTLD widely used as "company". |
| `.io` | Cloudflare / Porkbun | ~$45–50 | ~$45–50 | Tech-startup connotation; expensive. Cloudflare at-cost is typically best. |
| `.earth` | varies, roughly $35–50 | ~$35–50 | ~$35–50 | Sustainability-relevant. Uncommon; small registries. Check TLD-List for current cheapest. **Not confirmed in this research.** |
| `.eco` | varies, roughly $45–75 | ~$60–70 | ~$60–70 | Requires a short "Eco Profile" pledge (go.eco). Strong ESG signal, but renewals are high. |
| `.ai` | Cloudflare (~$70/yr over 2 yrs) or Epik ($74.95 flat) | ~$50–80 | ~$70–80 | Anguilla ccTLD, minimum 2-year registration at most registrars. Overkill for ESG positioning. |

**Recommendation on TLD:** Stick with `.com`. It's the cheapest, the most recognised, and it avoids the semantic drift of `.ai` (AI company?) or `.io` (tech startup?). `.earth` or `.eco` have ESG flavour but both cost 3–6x more per year and carry less recognition than `.com`. If you want a sustainability TLD later, buy it *in addition* to `.com` — but lock in `.com` first.

## One-line recommendation

**Register `hemerascope.com` at Cloudflare Registrar (~$10/yr at-cost flat) if you're happy using Cloudflare DNS; otherwise Porkbun (~$11/yr flat, free privacy + SSL). Skip GoDaddy, Gandi, and anything with a renewal cliff.**

## Sources

- Porkbun: <https://porkbun.com/products/domains>, <https://kb.porkbun.com/article/97-how-to-configure-whois-privacy-service-porkbun>
- Cloudflare Registrar: <https://www.cloudflare.com/products/registrar/>, <https://domains.cloudflare.com/>, <https://tldprice.org/registrar/cloudflare>
- Namecheap: <https://www.namecheap.com/domains/>, <https://allaboutcookies.org/namecheap-pricing-guide>
- GoDaddy: <https://hostingrevelations.com/godaddy-renewal-price-list/>, <https://nameexperts.com/blog/godaddy-domain-name-cost/>
- IONOS: <https://www.ionos.com/domains/domain-name-prices>, <https://www.ionos.co.uk/help/2026/information-on-the-2026-ionos-price-adjustment/>
- Gandi: <https://tldes.com/registrars/gandi>, <https://domcomp.com/registrars/gandi-net>
- Name.com: <https://www.name.com/support/articles/205934677-adding-whois-privacy>, <https://nameexperts.com/blog/how-much-to-buy-a-domain-name/>
- Squarespace Domains: <https://support.squarespace.com/hc/en-us/articles/205812438-Whois-privacy>, <https://domains.squarespace.com/>
- TLD comparison aggregators: <https://tld-list.com/>, <https://domaindetails.com/registrars/cheapest>, <https://domcomp.com/>
- .ai pricing: <https://domainoffer.net/tld/ai>, <https://tld-list.com/tld/ai>
- .co pricing: <https://domainoffer.net/tld/co/porkbun>
- .eco pricing: <https://tld-list.com/tld/eco>, <https://support.go.eco/en/articles/1721350-how-much-does-eco-cost>
- .earth pricing: <https://tld-list.com/tld/earth>
- .io pricing: <https://domainoffer.net/tld/io>, <https://tldspy.com/tld/io>
