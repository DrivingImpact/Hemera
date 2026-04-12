export const metadata = {
  title: "Cookie Statement · HemeraScope",
  description: "How HemeraScope uses cookies.",
};

export default function CookiesPage() {
  return (
    <article className="space-y-6 text-[14px] leading-relaxed text-slate">
      <header className="space-y-1 pb-4 border-b border-[#E5E5E0]">
        <h1 className="text-3xl font-bold text-slate">Cookie Statement</h1>
        <p className="text-muted text-sm">Last updated: [DATE] · Version 1.0</p>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-bold text-slate">What are cookies?</h2>
        <p>
          Cookies are small text files a website places on your device. They let the site remember
          things like whether you&apos;re signed in, what preferences you&apos;ve chosen, and how
          you reached the page. Some cookies are essential for the site to work; others are
          optional.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold text-slate">How we use cookies</h2>
        <p>
          HemeraScope uses cookies in three narrow, essential ways: to keep you signed in, to
          remember a small number of UI preferences, and to protect the site against common web
          attacks. We do not currently run advertising or cross-site tracking cookies.
        </p>
        <p>
          Under the Privacy and Electronic Communications Regulations 2003 (PECR), as updated by
          the Data (Use and Access) Act 2025 which came into force on 5 February 2026, we must ask
          for your consent before setting any cookie that is not strictly necessary. For strictly
          necessary cookies we can rely on the &ldquo;strictly necessary&rdquo; exemption and do
          not need consent; we list them transparently below so you can see what they do.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold text-slate">Cookies we set</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px] border-collapse">
            <thead>
              <tr className="border-b border-[#E5E5E0] text-left">
                <th className="py-2 pr-3 font-semibold">Name</th>
                <th className="py-2 pr-3 font-semibold">Set by</th>
                <th className="py-2 pr-3 font-semibold">Purpose</th>
                <th className="py-2 pr-3 font-semibold">Duration</th>
                <th className="py-2 font-semibold">Category</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0F0EB]">
              <Row
                name="__session"
                setBy="Clerk"
                purpose="Keeps you signed in to HemeraScope."
                duration="Session / rotating"
                category="Strictly necessary"
              />
              <Row
                name="__client_uat"
                setBy="Clerk"
                purpose="Tracks the latest authentication timestamp to detect concurrent sessions."
                duration="Session"
                category="Strictly necessary"
              />
              <Row
                name="__clerk_db_jwt"
                setBy="Clerk"
                purpose="Stores the signed session token."
                duration="Session / rotating"
                category="Strictly necessary"
              />
              <Row
                name="csrf_token"
                setBy="HemeraScope"
                purpose="Protects against cross-site request forgery on form submissions."
                duration="Session"
                category="Strictly necessary"
              />
              <Row
                name="hemera_consent"
                setBy="HemeraScope"
                purpose="Remembers your cookie preferences so we don't ask again on every visit."
                duration="12 months"
                category="Strictly necessary (consent record)"
              />
            </tbody>
          </table>
        </div>
        <p className="text-[12px] text-muted italic">
          If we add any analytics, product-intelligence, or marketing cookies in future, they will
          appear in this table and will require your opt-in consent before being set.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold text-slate">Managing your preferences</h2>
        <p>
          You can change or withdraw your consent at any time via the &ldquo;Cookie settings&rdquo;
          link in the footer. You can also control cookies through your browser settings — every
          major browser lets you block or delete cookies on a site-by-site basis.
        </p>
        <p>
          Blocking the cookies listed as &ldquo;strictly necessary&rdquo; will prevent HemeraScope
          from working — you won&apos;t be able to stay signed in or submit forms.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold text-slate">More information</h2>
        <p>
          For more on how we handle personal data generally, see our{" "}
          <a href="/legal/privacy" className="text-teal hover:underline">
            Privacy Policy
          </a>
          . For information about cookies in general, the ICO&apos;s{" "}
          <a
            href="https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/"
            className="text-teal hover:underline"
          >
            cookies guidance
          </a>{" "}
          is a good starting point.
        </p>
      </section>
    </article>
  );
}

function Row({
  name,
  setBy,
  purpose,
  duration,
  category,
}: {
  name: string;
  setBy: string;
  purpose: string;
  duration: string;
  category: string;
}) {
  return (
    <tr>
      <td className="py-2 pr-3 font-mono text-[11px] align-top">{name}</td>
      <td className="py-2 pr-3 align-top">{setBy}</td>
      <td className="py-2 pr-3 align-top">{purpose}</td>
      <td className="py-2 pr-3 align-top">{duration}</td>
      <td className="py-2 align-top">{category}</td>
    </tr>
  );
}
