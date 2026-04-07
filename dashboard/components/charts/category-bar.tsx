"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { SCOPE_COLORS } from "@/lib/plotly-theme";
import type { CategorySummary } from "@/lib/types";

interface CategoryBarProps {
  categories: CategorySummary[];
  topN?: number;
}

export function CategoryBar({ categories, topN = 10 }: CategoryBarProps) {
  const sorted = [...categories]
    .sort((a, b) => b.co2e_tonnes - a.co2e_tonnes)
    .slice(0, topN)
    .reverse(); // reversed so biggest is at top

  const names = sorted.map((c) => c.name);
  const values = sorted.map((c) => c.co2e_tonnes);
  const colors = sorted.map((c) => SCOPE_COLORS[c.scope] ?? "#64748B");

  return (
    <PlotlyChart
      data={[
        {
          type: "bar",
          orientation: "h",
          x: values,
          y: names,
          marker: { color: colors },
          hovertemplate: "%{y}<br>%{x:.1f} tCO₂e<extra></extra>",
        },
      ]}
      layout={{
        xaxis: { title: { text: "tCO₂e" }, tickfont: { size: 11 } },
        yaxis: { tickfont: { size: 11 }, automargin: true },
        margin: { l: 160, r: 20, t: 20, b: 40 },
        height: 360,
        showlegend: false,
      }}
    />
  );
}
