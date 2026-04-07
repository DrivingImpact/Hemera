"use client";

import { PlotlyChart } from "@/components/charts/plotly-wrapper";

interface RadarProps {
  labels: string[];
  values: number[];
  title?: string;
  range?: [number, number];
}

export function EsgRadar({ labels, values, title, range = [0, 100] }: RadarProps) {
  // Close the polygon
  const closedLabels = [...labels, labels[0]];
  const closedValues = [...values, values[0]];

  return (
    <PlotlyChart
      data={[
        {
          type: "scatterpolar",
          fill: "toself",
          r: closedValues,
          theta: closedLabels,
          line: { color: "#0D9488", width: 2 },
          fillcolor: "#0D948833",
          hovertemplate: "<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>",
        },
      ]}
      layout={{
        polar: {
          radialaxis: {
            range,
            tickfont: { size: 10 },
          },
          angularaxis: {
            tickfont: { size: 11 },
          },
        },
        showlegend: false,
        margin: { l: 50, r: 50, t: title ? 40 : 20, b: 20 },
        title: title ? { text: title, font: { size: 13 } } : undefined,
        height: 300,
      }}
    />
  );
}
