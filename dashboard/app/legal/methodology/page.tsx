export const metadata = {
  title: "AI & Methodology Disclosure \u00b7 HemeraScope",
  description: "How HemeraScope calculates carbon footprints and assesses supplier risk.",
};

export default function MethodologyPage() {
  return (
    <article className="prose-legal space-y-6 text-[14px] leading-relaxed text-slate">
      <header className="space-y-1 pb-4 border-b border-[#E5E5E0]">
        <h1 className="text-3xl font-bold text-slate">AI &amp; Methodology Disclosure</h1>
        <p className="text-muted text-sm">
          Hemera Intelligence Ltd &middot; Last updated: [pending &mdash; effective date] &middot; Version 1.0
        </p>
      </header>

      <Section title="1. Carbon methodology">
        <p>
          HemeraScope calculates carbon footprints using <strong>DEFRA GHG Conversion Factors</strong>{" "}
          (published annually by the UK Department for Environment, Food &amp; Rural Affairs). We
          apply a cascading precision model:
        </p>
        <ul>
          <li>
            <strong>Level 1 &mdash; Supplier-specific:</strong> Where a supplier provides verified
            emissions data (e.g. via CDP, SBTi, or direct disclosure), we use their reported figures.
            This is the highest-fidelity tier.
          </li>
          <li>
            <strong>Level 2 &mdash; Activity-based:</strong> Where specific activity data is
            available (e.g. kWh of electricity, litres of fuel, tonnes of waste), we apply the
            corresponding DEFRA conversion factor.
          </li>
          <li>
            <strong>Level 4 &mdash; EEIO spend-based:</strong> Where only spend data is available, we
            apply environmentally extended input&ndash;output (EEIO) emission factors by sector and
            spend amount. This is the lowest-fidelity tier and is clearly flagged in reports.
          </li>
        </ul>
        <p>
          Every carbon figure in HemeraScope includes an <strong>uncertainty range</strong> expressed
          as a geometric standard deviation (GSD) with a 95% confidence interval. Data quality is
          scored using a <strong>Pedigree Matrix</strong> aligned with ISO 14044 requirements,
          assessing reliability, completeness, temporal correlation, geographical correlation, and
          technological correlation.
        </p>
      </Section>

      <Section title="2. Supplier intelligence">
        <p>
          HemeraScope builds supplier risk profiles using a <strong>13-layer enrichment
          protocol</strong> that draws on publicly available registries and datasets, including:
        </p>
        <ul>
          <li>Companies House (company status, filing history, directors, SIC codes)</li>
          <li>Environment Agency (environmental permits, pollution incidents, enforcement actions)</li>
          <li>Health and Safety Executive (HSE notices, prosecutions)</li>
          <li>ICO Register of Data Controllers</li>
          <li>Modern Slavery Statement Registry</li>
          <li>Contracts Finder (public procurement history)</li>
          <li>Science Based Targets initiative (SBTi) commitments</li>
          <li>CDP disclosure status</li>
        </ul>
        <p>
          Findings from public registries are <strong>deterministic</strong> &mdash; they are direct
          lookups against authoritative sources and are presented as factual records with source
          attribution. AI-assisted risk analysis is applied on top of these deterministic findings and
          is always clearly distinguished in reports.
        </p>
      </Section>

      <Section title="3. AI usage">
        <p>
          HemeraScope uses <strong>Claude</strong> (developed by Anthropic, PBC) for the following
          purposes:
        </p>
        <ul>
          <li>
            <strong>Transaction classification:</strong> Categorising spend line items into emissions
            categories for carbon calculation
          </li>
          <li>
            <strong>Supplier risk analysis:</strong> Synthesising findings from multiple public
            registries into coherent risk narratives
          </li>
          <li>
            <strong>Report generation:</strong> Producing client-language summaries and explanatory
            text for deliverables
          </li>
        </ul>
        <p>
          <strong>Important safeguards:</strong>
        </p>
        <ul>
          <li>
            AI outputs are always reviewed by a human analyst before delivery to the client. We do not
            send AI-generated content directly to clients without review.
          </li>
          <li>
            We do not fine-tune AI models on client data. Transaction descriptions and supplier names
            (with no personal identifiable information) are sent to the Anthropic API for processing;
            this data is not used by Anthropic to train their models, per our data processing
            agreement with Anthropic.
          </li>
          <li>
            AI-generated analysis is clearly labelled in reports so clients can distinguish between
            deterministic findings and AI-assisted interpretation.
          </li>
        </ul>
      </Section>

      <Section title="4. Quality control">
        <p>
          Our quality assurance process is inspired by <strong>ISO 19011</strong> audit sampling
          principles:
        </p>
        <ul>
          <li>
            <strong>Stratified sampling:</strong> A representative sample of transactions and supplier
            records is manually reviewed for every engagement, with sampling rates weighted by risk
            and value
          </li>
          <li>
            <strong>Hard gate threshold:</strong> If the error rate in any sample exceeds 5%, the
            entire batch is returned for reclassification before proceeding
          </li>
          <li>
            <strong>Source traceability:</strong> Every finding in a HemeraScope report is traceable
            to its source &mdash; whether a public registry record, a DEFRA conversion factor, a
            client-provided data point, or an AI-generated analysis
          </li>
        </ul>
      </Section>

      <Section title="5. Standards alignment">
        <p>HemeraScope is aligned with the following standards and frameworks:</p>
        <ul>
          <li>
            <strong>GHG Protocol Corporate Standard</strong> &mdash; for scope 1, 2, and 3 emissions
            categorisation and reporting
          </li>
          <li>
            <strong>ISO 14064-1</strong> &mdash; for greenhouse gas quantification and reporting at
            the organisation level
          </li>
          <li>
            <strong>TCFD recommendations</strong> &mdash; for climate-related financial disclosure
            alignment
          </li>
        </ul>
        <p>
          <strong>Note:</strong> We are aligned with these standards but not independently certified
          against them. HemeraScope outputs are estimates prepared using recognised methodologies and
          are not a substitute for independent verification or third-party assurance where required by
          a specific regulatory regime.
        </p>
      </Section>

      <Section title="6. Changes to this disclosure">
        <p>
          We update this page when our methodology, AI usage, or quality control processes change
          materially. The &ldquo;Last updated&rdquo; date at the top reflects the most recent
          revision.
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
