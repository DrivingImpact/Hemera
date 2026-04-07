import { getEngagement, getCategories, getMonthly } from "@/lib/api";
import { ChartCard } from "@/components/ui/chart-card";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { PendingBanner } from "@/components/ui/pending-banner";
import { CategoryBar } from "@/components/charts/category-bar";
import { ScatterBubble } from "@/components/charts/scatter-bubble";
import { MonthlyArea } from "@/components/charts/monthly-area";
import { fmtTonnes, fmtGBP, fmtPct } from "@/lib/format";
import { SCOPE_LABELS } from "@/lib/plotly-theme";
import type { CategorySummary } from "@/lib/types";

export default async function CarbonPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const engagementId = Number(id);

  let engagement;
  try {
    engagement = await getEngagement(engagementId);
  } catch {
    return (
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-bold">Carbon Footprint</h1>
        </div>
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <p className="text-muted text-sm">No data yet.</p>
        </div>
      </div>
    );
  }

  if (engagement.status !== "qc_passed") {
    return (
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-bold">Carbon Footprint</h1>
          <p className="text-muted text-sm mt-0.5">{engagement.org_name}</p>
        </div>
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-2 gap-4">
          <ChartCard title="Top 10 Categories by Emissions">
            <div className="space-y-2 mt-2 px-2">
              {[90, 75, 65, 55, 45, 38, 30, 24, 18, 12].map((w, i) => (
                <div key={i} className="h-4 rounded bg-[#E5E5E0] opacity-40" style={{ width: `${w}%` }} />
              ))}
            </div>
          </ChartCard>
          <ChartCard title="Spend vs Emissions">
            <div className="flex items-end justify-around h-40 px-4 pb-2">
              {[40, 60, 30, 75, 50, 85, 45].map((h, i) => (
                <div key={i} className="w-6 rounded-t bg-[#E5E5E0] opacity-40" style={{ height: `${h}%` }} />
              ))}
            </div>
          </ChartCard>
        </div>
        <ChartCard title="Monthly Emissions by Scope">
          <div className="flex items-end justify-around h-40 px-4 pb-2">
            {[30, 45, 40, 55, 50, 65, 60, 70, 55, 45, 50, 40].map((h, i) => (
              <div key={i} className="w-5 rounded-t bg-[#E5E5E0] opacity-40" style={{ height: `${h}%` }} />
            ))}
          </div>
        </ChartCard>
        <div className="bg-surface rounded-lg border border-[#E5E5E0] overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E5E5E0]">
            <h4 className="text-xs font-semibold">All Categories</h4>
          </div>
          <div className="p-4 space-y-2">
            {[85, 70, 60, 50, 40].map((w, i) => (
              <div key={i} className="h-3 rounded bg-[#E5E5E0] opacity-30" style={{ width: `${w}%` }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const [categories, monthly] = await Promise.all([
    getCategories(engagementId),
    getMonthly(engagementId),
  ]);

  const totalCo2e = categories.reduce((s, c) => s + c.co2e_tonnes, 0) || 1;

  const tableRows = [...categories]
    .sort((a, b) => b.co2e_tonnes - a.co2e_tonnes)
    .map((cat) => ({
      ...cat,
      pct: (cat.co2e_tonnes / totalCo2e) * 100,
    }));

  type TableRow = CategorySummary & { pct: number } & Record<string, unknown>;

  const columns = [
    { key: "name", label: "Category" },
    {
      key: "scope",
      label: "Scope",
      render: (row: TableRow) => (
        <Badge variant={row.scope === 1 ? "slate" : row.scope === 2 ? "teal" : "amber"}>
          {SCOPE_LABELS[row.scope] ?? `Scope ${row.scope}`}
        </Badge>
      ),
    },
    {
      key: "spend_gbp",
      label: "Spend",
      align: "right" as const,
      render: (row: TableRow) => fmtGBP(row.spend_gbp),
    },
    {
      key: "co2e_tonnes",
      label: "tCO₂e",
      align: "right" as const,
      render: (row: TableRow) => fmtTonnes(row.co2e_tonnes),
    },
    {
      key: "pct",
      label: "% of Total",
      align: "right" as const,
      render: (row: TableRow) => fmtPct(row.pct),
    },
    {
      key: "gsd",
      label: "GSD",
      align: "right" as const,
      render: (row: TableRow) => row.gsd.toFixed(2),
    },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Carbon Footprint</h1>
        <p className="text-muted text-sm mt-0.5">{engagement.org_name}</p>
      </div>

      {/* 2-col grid: category bar + scatter */}
      <div className="grid grid-cols-2 gap-4">
        <ChartCard title="Top 10 Categories by Emissions">
          <CategoryBar categories={categories} topN={10} />
        </ChartCard>
        <ChartCard title="Spend vs Emissions">
          <ScatterBubble categories={categories} />
        </ChartCard>
      </div>

      {/* Full-width monthly area */}
      <ChartCard title="Monthly Emissions by Scope">
        <MonthlyArea data={monthly} />
      </ChartCard>

      {/* Full-width data table */}
      <div className="bg-surface rounded-lg border border-[#E5E5E0] overflow-hidden">
        <div className="px-4 py-3 border-b border-[#E5E5E0]">
          <h4 className="text-xs font-semibold">All Categories</h4>
        </div>
        <DataTable<TableRow> columns={columns} rows={tableRows} />
      </div>
    </div>
  );
}
