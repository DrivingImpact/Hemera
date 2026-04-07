"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { SCOPE_COLORS, SCOPE_LABELS } from "@/lib/plotly-theme";

interface ScopeDonutProps {
  scope1: number;
  scope2: number;
  scope3: number;
}

export function ScopeDonut({ scope1, scope2, scope3 }: ScopeDonutProps) {
  const labels = [SCOPE_LABELS[1], SCOPE_LABELS[2], SCOPE_LABELS[3]];
  const values = [scope1, scope2, scope3];
  const colors = [SCOPE_COLORS[1], SCOPE_COLORS[2], SCOPE_COLORS[3]];

  return (
    <PlotlyChart
      data={[
        {
          type: "pie",
          hole: 0.55,
          labels,
          values,
          marker: { colors },
          textinfo: "percent",
          hovertemplate: "%{label}<br>%{value:.1f} tCO₂e<br>%{percent}<extra></extra>",
        },
      ]}
      layout={{
        showlegend: true,
        legend: { orientation: "h", y: -0.1 },
        margin: { l: 10, r: 10, t: 10, b: 30 },
        height: 320,
      }}
    />
  );
}
