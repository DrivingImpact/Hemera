export const metadata = {
  title: "Accessibility Statement \u00b7 HemeraScope",
  description: "Hemera Intelligence Ltd\u2019s commitment to web accessibility.",
};

export default function AccessibilityPage() {
  return (
    <article className="prose-legal space-y-6 text-[14px] leading-relaxed text-slate">
      <header className="space-y-1 pb-4 border-b border-[#E5E5E0]">
        <h1 className="text-3xl font-bold text-slate">Accessibility Statement</h1>
        <p className="text-muted text-sm">
          Hemera Intelligence Ltd &middot; Last updated: [pending &mdash; effective date] &middot; Version 1.0
        </p>
      </header>

      <Section title="1. Our commitment">
        <p>
          Hemera Intelligence Ltd (&ldquo;Hemera&rdquo;) is committed to making{" "}
          <strong>HemeraScope</strong> accessible to the widest possible audience, including people
          with disabilities. We aim to conform to the{" "}
          <strong>Web Content Accessibility Guidelines (WCAG) 2.1 Level AA</strong> standard.
        </p>
      </Section>

      <Section title="2. Current status">
        <p>
          We are working towards full WCAG 2.1 AA compliance. HemeraScope is a new platform and we
          are actively improving accessibility across all areas of the product. We test new features
          against WCAG criteria during development and prioritise accessibility fixes alongside other
          work.
        </p>
      </Section>

      <Section title="3. Known issues">
        <p>
          As an early-stage product, some areas of HemeraScope may not yet meet every WCAG 2.1 AA
          success criterion. Known areas under active improvement include:
        </p>
        <ul>
          <li>Complex data tables and charts may not have full screen reader descriptions</li>
          <li>Some PDF report outputs may not be fully tagged for assistive technology</li>
          <li>Keyboard navigation in certain interactive components is being refined</li>
        </ul>
        <p>
          We are a new platform and are actively improving accessibility. We aim to resolve known
          issues as quickly as practicable.
        </p>
      </Section>

      <Section title="4. What we do">
        <ul>
          <li>Use semantic HTML and ARIA attributes throughout the application</li>
          <li>Ensure sufficient colour contrast ratios across our interface</li>
          <li>Support keyboard navigation for all core functionality</li>
          <li>Provide text alternatives for non-text content where possible</li>
          <li>Test with automated accessibility tools during development</li>
        </ul>
      </Section>

      <Section title="5. Reporting accessibility issues">
        <p>
          If you encounter an accessibility barrier on HemeraScope, please let us know. We take
          accessibility reports seriously and will do our best to address issues promptly.
        </p>
        <ul>
          <li>
            <strong>Email:</strong> [pending &mdash; accessibility contact email]
          </li>
        </ul>
        <p>
          When reporting an issue, please include the page URL, a description of the problem, and the
          assistive technology you were using (if applicable). We aim to respond within 5 working
          days.
        </p>
      </Section>

      <Section title="6. Enforcement">
        <p>
          Although Hemera is a private-sector organisation and is not subject to the Public Sector
          Bodies (Websites and Mobile Applications) (No. 2) Accessibility Regulations 2018, we
          voluntarily align with its guidance because many of our clients are public-sector bodies
          (universities, local authorities) who expect this standard.
        </p>
        <p>
          If you are not satisfied with our response to an accessibility concern, you can contact the{" "}
          <a
            href="https://www.equalityhumanrights.com/en/contact-us"
            className="text-teal hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Equality and Human Rights Commission (EHRC)
          </a>
          .
        </p>
      </Section>

      <Section title="7. Review">
        <p>
          This statement is reviewed annually and updated when significant changes are made to
          HemeraScope.
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
