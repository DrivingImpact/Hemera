export const metadata = {
  title: "Sub-processor List \u00b7 HemeraScope",
  description: "Third-party sub-processors used by Hemera Intelligence Ltd.",
};

export default function SubProcessorsPage() {
  return (
    <article className="prose-legal space-y-6 text-[14px] leading-relaxed text-slate">
      <header className="space-y-1 pb-4 border-b border-[#E5E5E0]">
        <h1 className="text-3xl font-bold text-slate">Sub-processor List</h1>
        <p className="text-muted text-sm">
          Hemera Intelligence Ltd &middot; Last updated: [pending &mdash; date] &middot; Version 1.0
        </p>
      </header>

      <Section title="Sub-processors">
        <p>
          The following third-party sub-processors are engaged by Hemera Intelligence Ltd in the
          provision of the HemeraScope service. Each sub-processor processes data only for the
          purposes described below.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px] border-collapse">
            <thead>
              <tr className="border-b border-[#E5E5E0] text-left">
                <th className="py-2 pr-3 font-semibold">Sub-processor</th>
                <th className="py-2 pr-3 font-semibold">Purpose</th>
                <th className="py-2 pr-3 font-semibold">Data processed</th>
                <th className="py-2 font-semibold">Location</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0F0EB]">
              <TR
                name="Clerk, Inc."
                purpose="Authentication & user management"
                data="User email, name, session data"
                location="US (SOC 2 Type II)"
              />
              <TR
                name="Vercel, Inc."
                purpose="Frontend hosting & CDN"
                data="Session cookies, page requests"
                location="Global (US-headquartered)"
              />
              <TR
                name="Render, Inc."
                purpose="Backend hosting & database"
                data="All application data"
                location="US (Oregon)"
              />
              <TR
                name="Anthropic, PBC"
                purpose="AI analysis (classification, risk)"
                data="Transaction descriptions, supplier names (no PII)"
                location="US"
              />
              <TR
                name="Companies House"
                purpose="Supplier registry lookup"
                data="Company names, numbers"
                location="UK (gov.uk)"
              />
              <TR
                name="Environment Agency"
                purpose="Environmental permit data"
                data="Company names"
                location="UK (gov.uk)"
              />
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Changes to this list">
        <p>
          This list was last updated <strong>[pending &mdash; date]</strong>. We will notify clients
          of changes to this list at least <strong>30 days</strong> before adding a new
          sub-processor, in line with our Data Processing Agreement.
        </p>
        <p>
          If you have questions about our sub-processors, please contact us at{" "}
          <strong>[pending &mdash; privacy email]</strong>.
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

function TR({
  name,
  purpose,
  data,
  location,
}: {
  name: string;
  purpose: string;
  data: string;
  location: string;
}) {
  return (
    <tr>
      <td className="py-2 pr-3 font-semibold align-top">{name}</td>
      <td className="py-2 pr-3 align-top">{purpose}</td>
      <td className="py-2 pr-3 align-top">{data}</td>
      <td className="py-2 align-top">{location}</td>
    </tr>
  );
}
