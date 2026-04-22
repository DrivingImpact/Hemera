# Cyber Essentials Certification — Summary & Requirements

**Last updated:** 2026-04-22

## What it is

Cyber Essentials is a UK government-backed cybersecurity certification scheme run by IASME (on behalf of the National Cyber Security Centre). It proves you have basic cybersecurity controls in place. Two levels:

1. **Cyber Essentials** — self-assessment questionnaire, verified by a certification body. ~£320+VAT. 2-6 weeks.
2. **Cyber Essentials Plus** — everything above + an independent technical audit (vulnerability scan, config check). ~£1,500-2,500. Additional 2-4 weeks after CE.

## Why Hemera needs it

- **Trust signal:** The #1 cybersecurity credential UK enterprise buyers recognise. Many RFPs require it.
- **Government contracts:** Mandatory for any UK government contract involving personal data or ICT.
- **Insurance:** Some cyber insurance providers offer discounts for CE-certified organisations.
- **Cost-effective:** Highest trust-per-pound of any certification Hemera can get right now.

## The 5 Technical Controls (v3.3, effective 27 April 2026)

### 1. Firewalls
- **Requirement:** All devices accessing the internet must be protected by a correctly configured firewall or equivalent boundary device.
- **Hemera's position:** Render and Vercel handle network-level firewalls. Local dev machines need OS firewalls enabled (macOS firewall on by default). No on-premises servers.
- **Action needed:** Verify macOS firewall is enabled on all founder machines. Document Render/Vercel network controls.

### 2. Secure Configuration
- **Requirement:** Computers and network devices are configured to reduce vulnerabilities. Remove unnecessary software, change default passwords, disable auto-run.
- **New in v3.3:** All admin accounts must use separate credentials from day-to-day accounts.
- **Hemera's position:** Cloud-hosted, no servers to configure. Clerk handles auth with secure defaults.
- **Action needed:** Ensure no default passwords anywhere (database, admin panels). Document all services and their default config state.

### 3. User Access Control
- **Requirement:** User accounts are managed and only provide the minimum access necessary. Admin accounts used only when needed. Remove/disable accounts when no longer required.
- **Hemera's position:** Clerk RBAC with admin/client roles. Principle of least privilege already in place.
- **Action needed:** Document the role matrix (who can access what). Ensure no shared accounts.

### 4. Malware Protection
- **Requirement:** Anti-malware software is installed and kept up to date, OR application allow-listing is in place.
- **New in v3.3:** All devices must have malware protection — macOS included (no longer exempt).
- **Hemera's position:** macOS has built-in XProtect + Gatekeeper. Consider adding a third-party solution (e.g., Malwarebytes, CrowdStrike Falcon Go) for stronger compliance posture.
- **Action needed:** Verify XProtect is enabled and up to date on all machines. Consider whether third-party AV is needed for the assessment.

### 5. Security Update Management (Patching)
- **Requirement:** Software is kept up to date. Security patches applied within 14 days of release (tightened from previous versions).
- **New in v3.3:** 14-day patching window is now a hard requirement (was "reasonable timeframe" before).
- **Hemera's position:** Vercel and Render auto-update infrastructure. Python/Node dependencies need manual updates.
- **Action needed:** Enable automatic OS updates. Set a fortnightly reminder to check dependency updates (`pip audit`, `npm audit`). Document the patching process.

## Additional v3.3 Requirements

- **MFA on all admin accounts:** Cloud services (GitHub, Vercel, Render, Clerk dashboard, Cloudflare, database admin) must all have MFA enabled.
- **MFA on all email accounts:** Gmail/Outlook accounts used for business must have MFA.
- **Password policy:** Minimum 8 characters for user accounts, 12 characters for admin accounts. No complexity rules required but must use a blocklist of common passwords (Clerk handles this).
- **BYOD policy:** If founders use personal devices, those devices are in scope for the assessment.

## The Assessment Process

1. **Choose a certification body:** IASME-accredited. Examples: IASME itself, IT Governance, Amshire Cyber, CyberSmart.
2. **Complete the self-assessment questionnaire:** ~80 questions about your 5 controls. Takes 2-4 hours if you've prepared.
3. **Submit + pay:** ~£320+VAT for Cyber Essentials.
4. **Review period:** The certification body reviews your answers. May ask clarifying questions. 5-10 business days.
5. **Certificate issued:** Valid for 12 months. You get a badge/logo to display.

## Preparation Checklist for Hemera

- [ ] Enable macOS firewall on all founder machines (`System Settings > Network > Firewall`)
- [ ] Enable MFA on: GitHub, Vercel, Render, Clerk dashboard, Cloudflare (when domain registered), email accounts, database admin (if applicable)
- [ ] Verify no default or shared passwords anywhere
- [ ] Enable automatic OS updates on all machines
- [ ] Run `pip audit` and `npm audit` — fix any known vulnerabilities
- [ ] Document: which services you use, who has admin access, what devices are in scope
- [ ] Verify anti-malware is active (macOS: `System Settings > Privacy & Security > Advanced > XProtect`)
- [ ] Create a simple incident response plan (who to contact, what to do if breached)
- [ ] Choose a certification body and book the assessment

## Cost & Timeline

| Item | Cost | Timeline |
|------|------|----------|
| Cyber Essentials (self-assessment) | ~£320+VAT | 2-6 weeks |
| Cyber Essentials Plus (technical audit) | ~£1,500-2,500 | Additional 2-4 weeks |
| Third-party antivirus (if needed) | £30-50/device/year | Immediate |

## Recommended Certification Bodies

1. **IASME** (iasme.co.uk) — they run the scheme, so direct access
2. **CyberSmart** (cybersmart.co.uk) — app-based, guides you through the process, popular with startups
3. **IT Governance** (itgovernance.co.uk) — well-known, also does ISO 27001
