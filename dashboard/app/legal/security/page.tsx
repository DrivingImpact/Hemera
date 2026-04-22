export const metadata = {
  title: "Security & Trust \u00b7 HemeraScope",
  description: "How Hemera Intelligence Ltd protects your data.",
};

export default function SecurityPage() {
  return (
    <article className="prose-legal space-y-6 text-[14px] leading-relaxed text-slate">
      <header className="space-y-1 pb-4 border-b border-[#E5E5E0]">
        <h1 className="text-3xl font-bold text-slate">Security &amp; Trust</h1>
        <p className="text-muted text-sm">
          Hemera Intelligence Ltd &middot; Last updated: [pending &mdash; effective date] &middot; Version 1.0
        </p>
      </header>

      <Section title="1. Data hosting">
        <p>
          HemeraScope application data is stored in a managed <strong>PostgreSQL</strong> database
          hosted by <strong>Render, Inc.</strong> in their Oregon (US) data centre. We acknowledge
          that US hosting introduces international transfer considerations under UK GDPR; appropriate
          safeguards are detailed in our{" "}
          <a href="/legal/privacy" className="text-teal hover:underline">
            Privacy Policy
          </a>{" "}
          (Section 5 &mdash; International transfers).
        </p>
        <p>
          Our frontend is hosted on <strong>Vercel, Inc.</strong>, which operates a global CDN with
          EU data residency options available. Static assets and page requests are served from edge
          locations closest to the user.
        </p>
      </Section>

      <Section title="2. Encryption">
        <ul>
          <li>
            <strong>In transit:</strong> All connections to HemeraScope are encrypted using TLS 1.2 or
            higher. We enforce HTTPS across all endpoints.
          </li>
          <li>
            <strong>At rest:</strong> Database storage is encrypted using AES-256, which is the
            standard for managed PostgreSQL providers. Backups are also encrypted at rest.
          </li>
        </ul>
      </Section>

      <Section title="3. Authentication">
        <p>
          User authentication is managed by <strong>Clerk, Inc.</strong> (SOC 2 Type II certified).
          Clerk provides:
        </p>
        <ul>
          <li>Multi-factor authentication (MFA) support</li>
          <li>Secure session token management</li>
          <li>Brute-force and credential-stuffing protections</li>
          <li>Role-based access control (RBAC) integration</li>
        </ul>
      </Section>

      <Section title="4. Access control">
        <p>
          HemeraScope enforces <strong>role-based access control</strong> with the following
          principles:
        </p>
        <ul>
          <li>
            <strong>Roles:</strong> Admin and Client, with permissions scoped to the minimum required
            for each role
          </li>
          <li>
            <strong>Principle of least privilege:</strong> Team members and systems are granted only
            the access necessary for their function
          </li>
          <li>
            <strong>Client data isolation:</strong> Each client&apos;s data is logically separated;
            clients cannot access another organisation&apos;s data
          </li>
        </ul>
      </Section>

      <Section title="5. Data retention">
        <ul>
          <li>
            <strong>Client data:</strong> Retained for the duration of the engagement plus 12 months,
            after which it is deleted or returned in accordance with our contractual commitments
          </li>
          <li>
            <strong>Anonymised supplier data:</strong> Irreversibly anonymised and aggregated
            statistical data is retained indefinitely for benchmarking and methodology improvement, as
            described in our{" "}
            <a href="/legal/privacy" className="text-teal hover:underline">
              Privacy Policy
            </a>{" "}
            (Section 11)
          </li>
          <li>
            <strong>Security logs:</strong> Retained for 12 months
          </li>
        </ul>
      </Section>

      <Section title="6. Incident response">
        <p>
          In the event of a personal data breach, we will notify affected clients within{" "}
          <strong>72 hours</strong> of confirming the breach, in line with UK GDPR Article 33. Our
          incident response process includes:
        </p>
        <ul>
          <li>Immediate containment and assessment of the breach</li>
          <li>Notification to the ICO where required (within 72 hours)</li>
          <li>Notification to affected clients with details of the breach, its likely impact, and remediation steps</li>
          <li>Post-incident review and implementation of preventive measures</li>
        </ul>
      </Section>

      <Section title="7. Certifications and registrations">
        <ul>
          <li>
            <strong>Cyber Essentials:</strong> We are pursuing Cyber Essentials certification
            (expected [pending &mdash; date])
          </li>
          <li>
            <strong>ICO registration:</strong> Hemera Intelligence Ltd is registered with the
            Information Commissioner&apos;s Office. Registration number:{" "}
            <strong>[pending &mdash; ICO number]</strong>
          </li>
        </ul>
      </Section>

      <Section title="8. Sub-processors">
        <p>
          A full list of our sub-processors, including the data they process and their hosting
          locations, is available on our{" "}
          <a href="/legal/sub-processors" className="text-teal hover:underline">
            Sub-processor List
          </a>
          . We notify clients of changes to this list at least 30 days in advance.
        </p>
      </Section>

      <Section title="9. Responsible disclosure">
        <p>
          If you discover a security vulnerability in HemeraScope, please report it responsibly to{" "}
          <strong>security@[pending &mdash; domain]</strong>. We ask that you:
        </p>
        <ul>
          <li>Do not access or modify other users&apos; data</li>
          <li>Do not publicly disclose the vulnerability before we have addressed it</li>
          <li>Provide sufficient detail for us to reproduce and fix the issue</li>
        </ul>
        <p>
          We will acknowledge your report within 3 working days and aim to resolve confirmed
          vulnerabilities promptly.
        </p>
      </Section>

      <Section title="10. Contact">
        <p>
          For security-related enquiries, contact us at{" "}
          <strong>security@[pending &mdash; domain]</strong>.
        </p>
      </Section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-bold text-slate">{title}</h2>
      <div className="space-y-3 [&>p]:leading-relaxed [&>ul]:pl-5 [&>ul]:list-disc [&>ul>li]:mb-1">
        {children}
      </div>
    </section>
  );
}
