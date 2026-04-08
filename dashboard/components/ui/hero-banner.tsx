import type { Engagement } from "@/lib/types";
import { fmtNumber } from "@/lib/format";

export function HeroBanner({ engagement, pending }: { engagement: Engagement; pending?: boolean }) {
  const total = engagement.total_co2e || 0;
  const ciLower = engagement.ci_lower || 0;
  const ciUpper = engagement.ci_upper || 0;

  return (
    <div className="bg-slate rounded-xl px-7 py-6 flex items-center gap-6 mb-5">
      <div>
        <div className="text-[10px] uppercase tracking-[1px] text-[#94A3B8]">
          Total Carbon Footprint
        </div>
        <div className="text-4xl font-extrabold text-teal mt-0.5">
          {pending ? "—" : fmtNumber(total)}
        </div>
        <div className="text-xs text-[#94A3B8] mt-0.5">
          {pending ? "tCO₂e · 95% CI: Pending" : `tCO₂e · 95% CI: ${fmtNumber(ciLower)} – ${fmtNumber(ciUpper)}`}
        </div>
      </div>
      <div className="ml-auto flex gap-5">
        <div className="text-center">
          <div className="text-[9px] text-[#94A3B8] uppercase tracking-[0.5px]">Suppliers</div>
          <div className="text-xl font-bold text-amber mt-0.5">
            {pending ? "—" : (engagement.supplier_count || 0)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[9px] text-[#94A3B8] uppercase tracking-[0.5px]">Transactions</div>
          <div className="text-xl font-bold text-white mt-0.5">
            {pending ? "—" : fmtNumber(engagement.transaction_count || 0)}
          </div>
        </div>
      </div>
    </div>
  );
}
