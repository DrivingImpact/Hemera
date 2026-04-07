export function KpiCard({
  label,
  value,
  unit,
  color = "teal",
}: {
  label: string;
  value: string;
  unit?: string;
  color?: "teal" | "slate" | "amber" | "success" | "error";
}) {
  const colorMap = {
    teal: "text-teal",
    slate: "text-slate",
    amber: "text-amber",
    success: "text-success",
    error: "text-error",
  };

  return (
    <div className="bg-paper rounded-lg p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
        {label}
      </div>
      <div className={`text-[32px] font-bold mt-1 tabular-nums ${colorMap[color]}`}>
        {value}
        {unit && <span className="text-sm font-normal text-[#94A3B8] ml-1">{unit}</span>}
      </div>
    </div>
  );
}
