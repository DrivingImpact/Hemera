export const metadata = {
  title: "Privacy Policy · HemeraScope",
  description: "How Hemera Intelligence Ltd handles personal data.",
};

export default function PrivacyPolicyPage() {
  return (
    <article className="prose-legal space-y-6 text-[14px] leading-relaxed text-slate">
      <header className="space-y-1 pb-4 border-b border-[#E5E5E0]">
        <h1 className="text-3xl font-bold text-slate">Privacy Policy</h1>
        <p className="text-muted text-sm">
          Hemera Intelligence Ltd · Last updated: [DATE] · Version 1.0
        </p>
      </header>

      <Section title="1. Who we are and our role under UK data protection law">
        <p>
          Hemera Intelligence Ltd (&ldquo;Hemera&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;,
          &ldquo;our&rdquo;) is a company registered in England and Wales, company number [########],
          with its registered office at [address]. We trade under the product name{" "}
          <strong>HemeraScope</strong>.
        </p>
        <p>We operate in two distinct roles under the UK GDPR:</p>
        <ul>
          <li>
            <strong>Data controller.</strong> For personal data we collect directly — website
            visitors, marketing contacts, job applicants, and the user accounts our clients set up
            to access HemeraScope. This Privacy Policy explains how we handle that data.
          </li>
          <li>
            <strong>Data processor.</strong> For supplier and spend data our clients upload into
            HemeraScope. Our processing of that data is governed by the Data Processing Agreement
            in place with the client, not by this Privacy Policy.
          </li>
        </ul>
        <p>
          We are registered with the Information Commissioner&apos;s Office (ICO) under registration
          number <strong>[########]</strong>.
        </p>
      </Section>

      <Section title="2. What personal data we collect and why">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px] border-collapse">
            <thead>
              <tr className="border-b border-[#E5E5E0] text-left">
                <th className="py-2 pr-3 font-semibold">Category</th>
                <th className="py-2 pr-3 font-semibold">Examples</th>
                <th className="py-2 pr-3 font-semibold">Purpose</th>
                <th className="py-2 font-semibold">Lawful basis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0F0EB]">
              <TR c="Website visitor data" e="IP address, browser, pages viewed, session timestamps" p="Operating and securing the site, measuring traffic, debugging" b="Legitimate interests" />
              <TR c="Account data" e="Name, work email, employer, role, password hash (via Clerk)" p="Creating and securing HemeraScope accounts" b="Contract" />
              <TR c="Client contact data" e="Name, work email, phone, company, role" p="Responding to enquiries, delivering the service, billing" b="Contract + legitimate interests" />
              <TR c="Marketing data" e="Email address, preferences" p="Sending the HemeraScope newsletter" b="Consent / legitimate interests (B2B)" />
              <TR c="Support correspondence" e="Message content, attachments, call notes" p="Answering support requests and keeping a record" b="Legitimate interests" />
              <TR c="Billing data" e="Name, billing address, company, payment references" p="Taking payment and meeting tax obligations" b="Contract; legal obligation" />
            </tbody>
          </table>
        </div>
        <p>
          We do <strong>not</strong> knowingly process special category data (health, ethnicity,
          political opinion etc.) in the ordinary course of running HemeraScope. If a client uploads
          documents that contain such data, we process it strictly as their processor.
        </p>
      </Section>

      <Section title="3. Where we get personal data from">
        <p>
          Most of the personal data we hold comes directly from you — when you fill in a form on
          our website, sign up for an account, email us, or engage us as a client.
        </p>
        <p>We also collect:</p>
        <ul>
          <li>
            <strong>Cookies and similar technologies</strong> when you visit our website (see our{" "}
            <a href="/legal/cookies" className="text-teal hover:underline">
              Cookie Statement
            </a>
            ).
          </li>
          <li>
            <strong>Public company registries</strong> — Companies House, HSE, SBTi, CDP, and
            similar public sources. We use these to build supplier intelligence data in
            HemeraScope. This data is about <strong>organisations</strong>, not individuals.
          </li>
        </ul>
      </Section>

      <Section title="4. Who we share personal data with">
        <p>We share personal data only with:</p>
        <ul>
          <li>
            <strong>Our sub-processors and service providers</strong> — the current list is
            available on our Trust page at [URL]. As of the last update these include Clerk, Inc.
            (US-based authentication), our hosting provider, our database host, our email provider
            and any analytics or error-monitoring tools.
          </li>
          <li>
            <strong>Professional advisers</strong> — lawyers, accountants, auditors, insurers —
            under duties of confidentiality.
          </li>
          <li>
            <strong>Authorities</strong> where we are legally required to.
          </li>
          <li>
            <strong>Successors</strong> in the event of a merger, acquisition or sale of our
            business.
          </li>
        </ul>
        <p>
          We do <strong>not</strong> sell personal data. We do not use client data to train
          general-purpose AI models.
        </p>
      </Section>

      <Section title="5. International transfers">
        <p>
          Some of our sub-processors — notably <strong>Clerk, Inc.</strong> — are based in the
          United States. When personal data is transferred out of the UK we use a valid UK GDPR
          Article 46 transfer mechanism: the UK Extension to the EU–US Data Privacy Framework, the
          UK International Data Transfer Agreement, or the UK Addendum to the EU SCCs, together
          with supplementary technical and organisational measures.
        </p>
      </Section>

      <Section title="6. How long we keep data">
        <table className="w-full text-[12px] border-collapse">
          <thead>
            <tr className="border-b border-[#E5E5E0] text-left">
              <th className="py-2 pr-3 font-semibold">Data</th>
              <th className="py-2 font-semibold">Retention</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F0F0EB]">
            <TR2 l="Active account data" r="Duration of the contract + 12 months" />
            <TR2 l="Billing and tax records" r="6 years from the end of the accounting period (HMRC)" />
            <TR2 l="Support correspondence" r="3 years from last contact" />
            <TR2 l="Marketing contacts" r="Until you unsubscribe; a minimal suppression record is kept indefinitely" />
            <TR2 l="Website analytics" r="Up to 26 months" />
            <TR2 l="Security logs" r="12 months" />
          </tbody>
        </table>
      </Section>

      <Section title="7. Your rights under UK GDPR">
        <p>You have the right to:</p>
        <ul>
          <li>access the personal data we hold about you;</li>
          <li>rectify inaccurate data;</li>
          <li>erase data in certain circumstances;</li>
          <li>restrict processing in certain circumstances;</li>
          <li>data portability;</li>
          <li>object to processing based on legitimate interests, including direct marketing;</li>
          <li>withdraw consent at any time where we rely on consent;</li>
          <li>
            not be subject to solely automated decisions with legal or similarly significant
            effects — we do not make such decisions about individuals.
          </li>
        </ul>
        <p>
          To exercise any of these rights, email <strong>[privacy@hemera.xxx]</strong>. We&apos;ll
          respond within one month. You can also complain to the ICO at{" "}
          <a href="https://ico.org.uk/make-a-complaint/" className="text-teal hover:underline">
            ico.org.uk/make-a-complaint
          </a>
          .
        </p>
      </Section>

      <Section title="11. Anonymised and aggregated data after termination">
        <p>
          When a client stops using HemeraScope, we delete or return the personal and
          client-identifiable data we hold as their processor, in line with our contractual
          commitments.
        </p>
        <p>
          Separately, and <strong>only after the data has been irreversibly anonymised and
          aggregated</strong> so that it cannot be linked back to the client, any individual
          supplier, or any natural person, Hemera retains statistical information derived from the
          work. Examples of the kind of retained information:
        </p>
        <ul>
          <li>
            &ldquo;UK universities in our benchmark have on average 12 transport-sector
            suppliers.&rdquo;
          </li>
          <li>
            &ldquo;Across professional-services clients, average modern-slavery risk score in the
            construction category is 2.3 out of 5.&rdquo;
          </li>
          <li>
            &ldquo;Reported scope 3 emissions intensity for higher-education clients: x tCO₂e / £m
            spend.&rdquo;
          </li>
        </ul>
        <p>This retained information does not include:</p>
        <ul>
          <li>the identity of any client (even indirectly — we apply a minimum cohort size);</li>
          <li>supplier names, company numbers, contact details, or any other direct or indirect identifier of a supplier;</li>
          <li>any personal data of any natural person.</li>
        </ul>
        <p>
          We rely on UK GDPR <strong>Recital 26</strong>, which provides that the principles of
          data protection do not apply to truly anonymous information. Because this retained
          information is not personal data, it is not subject to UK GDPR access, rectification,
          erasure or portability rights. Clients acknowledge and agree to this retention in the{" "}
          <a href="/legal/terms" className="text-teal hover:underline">
            Terms and Conditions
          </a>{" "}
          (Section 6) and the DPA.
        </p>
      </Section>

      <Section title="13. Contact us">
        <ul>
          <li>
            <strong>Email:</strong> [privacy@hemera.xxx]
          </li>
          <li>
            <strong>Post:</strong> Hemera Intelligence Ltd, [address]
          </li>
        </ul>
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

function TR({ c, e, p, b }: { c: string; e: string; p: string; b: string }) {
  return (
    <tr>
      <td className="py-2 pr-3 font-semibold align-top">{c}</td>
      <td className="py-2 pr-3 align-top">{e}</td>
      <td className="py-2 pr-3 align-top">{p}</td>
      <td className="py-2 align-top">{b}</td>
    </tr>
  );
}

function TR2({ l, r }: { l: string; r: string }) {
  return (
    <tr>
      <td className="py-2 pr-3 font-semibold align-top">{l}</td>
      <td className="py-2 align-top">{r}</td>
    </tr>
  );
}
