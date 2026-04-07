"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { SCOPE_COLORS, SCOPE_LABELS } from "@/lib/plotly-theme";
import type { CategorySummary } from "@/lib/types";

interface ScatterBubbleProps {
  categories: CategorySummary[];
}

export function ScatterBubble({ categories }: ScatterBubbleProps) {
  // Sort by co2e to find top 5 for labelling
  const top5Names = new Set(
    [...categories]
      .sort((a, b) => b.co2e_tonnes - a.co2e_tonnes)
      .slice(0, 5)
      .map((c) => c.name)
  );

  // Group by scope for separate traces
  const byScope: Record<number, CategorySummary[]> = {};
  for (const cat of categories) {
    if (!byScope[cat.scope]) byScope[cat.scope] = [];
    byScope[cat.scope].push(cat);
  }

  const traces = Object.entries(byScope).map(([scopeStr, cats]) => {
    const scope = Number(scopeStr);
    return {
      type: "scatter" as const,
      mode: "markers+text" as const,
      name: SCOPE_LABELS[scope] ?? `Scope ${scope}`,
      x: cats.map((c) => c.spend_gbp),
      y: cats.map((c) => c.co2e_tonnes),
      text: cats.map((c) => (top5Names.has(c.name) ? c.name : "")),
      textposition: "top center" as const,
      textfont: { size: 10 },
      marker: {
        color: SCOPE_COLORS[scope] ?? "#64748B",
        size: cats.map((c) => Math.max(8, Math.min(40, Math.sqrt(c.gsd) * 6))),
        opacity: 0.8,
        line: { width: 1, color: "white" },
      },
      hovertemplate:
        "<b>%{text}</b><br>Spend: £%{x:,.0f}<br>Emissions: %{y:.1f} tCO₂e<extra></extra>",
      customdata: cats.map((c) => c.name),
    };
  });

  return (
    <PlotlyChart
      data={traces}
      layout={{
        xaxis: { title: { text: "Spend (£)" }, tickformat: ",.0f", tickprefix: "£" },
        yaxis: { title: { text: "tCO₂e" } },
        margin: { l: 60, r: 20, t: 20, b: 50 },
        height: 360,
        showlegend: true,
        legend: { orientation: "h", y: -0.2 },
      }}
    />
  );
}
