import Link from "next/link";
import { getEngagement, getEngagementSuppliers } from "@/lib/api";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { PendingBanner } from "@/components/ui/pending-banner";
import { fmtTonnes, fmtGBP, fmtNumber } from "@/lib/format";
import type { EngagementSupplier } from "@/lib/types";

const SUPPLIER_PLACEHOLDER_COLUMNS = [
  { key: "name", label: "Supplier" },
  { key: "spend_gbp", label: "Spend", align: "right" as const },
  { key: "co2e_tonnes", label: "tCO₂e", align: "right" as const },
  { key: "intensity_kg_per_gbp", label: "Intensity (kg/£)", align: "right" as const },
  { key: "transaction_count", label: "Transactions", align: "right" as const },
  { key: "risk", label: "Risk" },
];

function getRiskVariant(intensity: number): { variant: "red" | "amber" | "green"; label: string } {
  if (intensity > 2) return { variant: "red", label: "High" };
  if (intensity > 0.5) return { variant: "amber", label: "Medium" };
  return { variant: "green", label: "Low" };
}

export default async function SuppliersPage({
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
          <h1 className="text-2xl font-bold">Suppliers</h1>
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
          <h1 className="text-2xl font-bold">Suppliers</h1>
          <p className="text-muted text-sm mt-0.5">{engagement.org_name}</p>
        </div>
        <PendingBanner status={engagement.status} />
        <div className="bg-surface rounded-lg border border-[#E5E5E0] overflow-hidden">
          <DataTable columns={SUPPLIER_PLACEHOLDER_COLUMNS} rows={[]} />
        </div>
      </div>
    );
  }

  const suppliers = await getEngagementSuppliers(engagementId);

  const sorted = [...suppliers].sort((a, b) => b.co2e_tonnes - a.co2e_tonnes);

  type SupplierRow = EngagementSupplier & { _id: string } & Record<string, unknown>;
  const rows: SupplierRow[] = sorted.map((s) => ({ ...s, _id: id }));

  const columns = [
    {
      key: "name",
      label: "Supplier",
      render: (row: SupplierRow) =>
        row.supplier_id ? (
          <Link
            href={`/dashboard/${id}/suppliers/${row.supplier_id}`}
            className="text-teal font-medium hover:underline"
          >
            {row.name}
          </Link>
        ) : (
          <span>{row.name}</span>
        ),
    },
    {
      key: "spend_gbp",
      label: "Spend",
      align: "right" as const,
      render: (row: SupplierRow) => fmtGBP(row.spend_gbp),
    },
    {
      key: "co2e_tonnes",
      label: "tCO₂e",
      align: "right" as const,
      render: (row: SupplierRow) => fmtTonnes(row.co2e_tonnes),
    },
    {
      key: "intensity_kg_per_gbp",
      label: "Intensity (kg/£)",
      align: "right" as const,
      render: (row: SupplierRow) => row.intensity_kg_per_gbp.toFixed(3),
    },
    {
      key: "transaction_count",
      label: "Transactions",
      align: "right" as const,
      render: (row: SupplierRow) => fmtNumber(row.transaction_count),
    },
    {
      key: "risk",
      label: "Risk",
      render: (row: SupplierRow) => {
        const { variant, label } = getRiskVariant(row.intensity_kg_per_gbp);
        return <Badge variant={variant}>{label}</Badge>;
      },
    },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Suppliers</h1>
        <p className="text-muted text-sm mt-0.5">
          {suppliers.length} supplier{suppliers.length !== 1 ? "s" : ""} in this engagement
        </p>
      </div>

      <div className="bg-surface rounded-lg border border-[#E5E5E0] overflow-hidden">
        <DataTable<SupplierRow> columns={columns} rows={rows} />
      </div>
    </div>
  );
}
