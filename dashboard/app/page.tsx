import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate flex flex-col items-center justify-center px-6">
      <div className="max-w-xl w-full text-center space-y-8">
        <div>
          <div className="text-teal text-[13px] font-bold uppercase tracking-[4px] mb-4">
            Hemera
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white leading-tight">
            Supply Chain Carbon Intelligence
          </h1>
          <p className="mt-4 text-[#94A3B8] text-lg leading-relaxed">
            Understand, measure, and reduce your scope 3 emissions with
            AI-powered spend data analysis.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/dashboard"
            className="px-7 py-3.5 bg-teal text-white rounded-lg font-semibold text-sm hover:opacity-90 transition-opacity"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/sign-in"
            className="px-7 py-3.5 border border-white/20 text-white rounded-lg font-semibold text-sm hover:bg-white/5 transition-colors"
          >
            Sign In
          </Link>
        </div>

        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/10">
          {[
            { label: "Accuracy", value: "±15%", desc: "GHG uncertainty" },
            { label: "Coverage", value: "Scope 1–3", desc: "Full emissions" },
            { label: "Compliance", value: "GHG Protocol", desc: "Standard aligned" },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-teal text-xl font-bold">{stat.value}</div>
              <div className="text-white text-xs font-semibold mt-0.5">{stat.label}</div>
              <div className="text-[#94A3B8] text-[11px]">{stat.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
