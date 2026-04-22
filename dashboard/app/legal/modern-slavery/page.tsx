export const metadata = {
  title: "Modern Slavery Statement \u00b7 HemeraScope",
  description: "Hemera Intelligence Ltd\u2019s commitment to preventing modern slavery.",
};

export default function ModernSlaveryPage() {
  return (
    <article className="prose-legal space-y-6 text-[14px] leading-relaxed text-slate">
      <header className="space-y-1 pb-4 border-b border-[#E5E5E0]">
        <h1 className="text-3xl font-bold text-slate">Modern Slavery Statement</h1>
        <p className="text-muted text-sm">
          Hemera Intelligence Ltd &middot; Last updated: [pending &mdash; effective date] &middot; Version 1.0
        </p>
      </header>

      <Section title="1. Our commitment">
        <p>
          Hemera Intelligence Ltd (&ldquo;Hemera&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;,
          &ldquo;our&rdquo;) is committed to preventing modern slavery and human trafficking in all
          of its operations and supply chains. We expect the same commitment from our suppliers,
          contractors, and business partners.
        </p>
      </Section>

      <Section title="2. About Hemera">
        <p>
          Hemera is a UK-registered ESG and carbon intelligence consultancy trading under the product
          name <strong>HemeraScope</strong>. We help organisations understand the carbon footprint of
          their supply chain spend, assess supplier ESG risk, and meet environmental reporting
          obligations. Our clients include UK higher education institutions and public sector bodies.
        </p>
      </Section>

      <Section title="3. Voluntary disclosure">
        <p>
          We are not required to publish this statement under the Modern Slavery Act 2015 as our
          turnover is below the &pound;36 million threshold, but we publish it voluntarily as part of
          our commitment to transparency and because we believe organisations working in supply chain
          assurance should lead by example.
        </p>
      </Section>

      <Section title="4. Steps we take">
        <ul>
          <li>
            <strong>Supplier due diligence.</strong> Modern slavery risk assessment is embedded in our
            core product. As part of our 8-layer supplier enrichment methodology, we check the UK
            Modern Slavery Statement Registry and other public enforcement databases for every
            supplier we analyse. We apply the same rigour to our own supply chain.
          </li>
          <li>
            <strong>Sub-processor review.</strong> We review the modern slavery and labour practices
            of our key technology sub-processors (see our{" "}
            <a href="/legal/sub-processors" className="text-teal hover:underline">
              sub-processor list
            </a>
            ) before onboarding them, and periodically thereafter.
          </li>
          <li>
            <strong>Employee awareness.</strong> All team members are made aware of the indicators of
            modern slavery and our expectations regarding ethical conduct. As we grow, we will
            introduce formal training.
          </li>
          <li>
            <strong>Whistleblowing.</strong> We encourage anyone &mdash; employees, contractors,
            suppliers, or members of the public &mdash; to report concerns about modern slavery or
            human trafficking. Reports can be made to{" "}
            <strong>[pending &mdash; whistleblowing contact email]</strong> and will be investigated
            confidentially.
          </li>
          <li>
            <strong>Recruitment.</strong> We verify the right to work of every employee and
            contractor. We do not use recruitment agencies that cannot demonstrate their own
            anti-slavery due diligence.
          </li>
        </ul>
      </Section>

      <Section title="5. Our supply chain">
        <p>
          As an early-stage technology consultancy, our supply chain is limited and predominantly
          comprises cloud infrastructure providers, software-as-a-service tools, and professional
          services firms. We consider the risk of modern slavery in our immediate supply chain to be
          low, but we remain vigilant and will expand our due diligence as the business grows.
        </p>
      </Section>

      <Section title="6. Governance and review">
        <p>
          This statement is reviewed annually by the directors of Hemera Intelligence Ltd. It will be
          updated to reflect changes in our operations, supply chain, and risk assessment.
        </p>
      </Section>

      <Section title="7. Approval">
        <p>
          This statement was approved by the board of directors of Hemera Intelligence Ltd and is
          signed on their behalf by:
        </p>
        <p className="mt-4">
          <strong>[pending &mdash; founder name]</strong>
          <br />
          Director, Hemera Intelligence Ltd
          <br />
          Date: [pending &mdash; effective date]
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
