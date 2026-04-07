"use client";

import dynamic from "next/dynamic";
import type * as Plotly from "plotly.js";
import { HEMERA_THEME } from "@/lib/plotly-theme";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export function PlotlyChart({
  data,
  layout,
  config,
  className,
  style,
}: {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  config?: Partial<Plotly.Config>;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <Plot
      data={data}
      layout={{
        ...HEMERA_THEME,
        autosize: true,
        ...layout,
      }}
      config={{
        displayModeBar: false,
        responsive: true,
        ...config,
      }}
      className={className}
      style={{ width: "100%", ...style }}
      useResizeHandler
    />
  );
}
