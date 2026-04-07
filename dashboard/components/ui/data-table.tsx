export interface Column<T> {
  key: string;
  label: string;
  align?: "left" | "right";
  render?: (row: T) => React.ReactNode;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
}: {
  columns: Column<T>[];
  rows: T[];
}) {
  return (
    <table className="w-full text-[13px] border-collapse">
      <thead>
        <tr>
          {columns.map((col) => (
            <th
              key={col.key}
              className={`text-left px-3 py-2.5 bg-paper text-[11px] font-semibold uppercase tracking-[0.5px] text-muted border-b-2 border-[#E5E5E0] ${
                col.align === "right" ? "text-right" : ""
              }`}
            >
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="hover:bg-[#FAFAF7]">
            {columns.map((col) => (
              <td
                key={col.key}
                className={`px-3 py-2.5 border-b border-[#F0F0EB] ${
                  col.align === "right" ? "text-right tabular-nums" : ""
                }`}
              >
                {col.render ? col.render(row) : String(row[col.key] ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
