import { getSupplier } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { ChartCard } from "@/components/ui/chart-card";
import { DataTable } from "@/components/ui/data-table";
import { EsgRadar } from "@/components/charts/radar";

export default async function SupplierDetailPage({
  params,
}: {
  params: Promise<{ id: string; supplierId: string }>;
}) {
  const { id, supplierId } = await params;
  const supplier = await getSupplier(Number(supplierId));

  const latestScore = supplier.score_history?.[supplier.score_history.length - 1];
  const radarLabels = latestScore ? Object.keys(latestScore.domains) : [];
  const radarValues = latestScore ? Object.values(latestScore.domains) : [];

  type SourceRow = (typeof supplier.sources)[number] & Record<string, unknown>;
  const sourceRows: SourceRow[] = (supplier.sources ?? []).map((s) => ({
    ...s,
  }));

  const sourceColumns = [
    { key: "source_name", label: "Source" },
    {
      key: "layer",
      label: "Layer",
      align: "right" as const,
      render: (row: SourceRow) => `L${row.layer}`,
    },
    {
      key: "tier",
      label: "Tier",
      align: "right" as const,
      render: (row: SourceRow) => String(row.tier),
    },
    { key: "summary", label: "Summary" },
    {
      key: "is_verified",
      label: "Verified",
      render: (row: SourceRow) =>
        row.is_verified ? (
          <Badge variant="green">Yes</Badge>
        ) : (
          <Badge variant="slate">No</Badge>
        ),
    },
    {
      key: "fetched_at",
      label: "Fetched",
      render: (row: SourceRow) =>
        new Date(row.fetched_at as string).toLocaleDateString("en-GB"),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Supplier header */}
      <div className="bg-surface rounded-lg border border-[#E5E5E0] p-5">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{supplier.name}</h1>
            {supplier.legal_name && supplier.legal_name !== supplier.name && (
              <p className="text-muted text-sm mt-0.5">{supplier.legal_name}</p>
            )}
            <div className="flex gap-2 mt-2 flex-wrap">
              {supplier.sector && <Badge variant="teal">{supplier.sector}</Badge>}
              {supplier.entity_type && <Badge variant="slate">{supplier.entity_type}</Badge>}
              {supplier.critical_flag && <Badge variant="red">Critical</Badge>}
            </div>
          </div>
          <div className="text-right">
            {latestScore && (
              <div>
                <div className="text-[10px] uppercase tracking-[1px] text-muted">Hemera Score</div>
                <div className="text-3xl font-extrabold text-teal">
                  {latestScore.hemera_score.toFixed(0)}
                </div>
                <Badge
                  variant={
                    latestScore.confidence === "high"
                      ? "green"
                      : latestScore.confidence === "medium"
                      ? "amber"
                      : "slate"
                  }
                >
                  {latestScore.confidence} confidence
                </Badge>
              </div>
            )}
          </div>
        </div>
        {supplier.registered_address && (
          <p className="text-sm text-muted mt-3">{supplier.registered_address}</p>
        )}
        {supplier.ch_number && (
          <p className="text-xs text-muted mt-1">Companies House: {supplier.ch_number}</p>
        )}
      </div>

      {/* Hemera Score Radar */}
      {radarLabels.length > 0 && (
        <ChartCard title="Hemera Domain Scores">
          <EsgRadar labels={radarLabels} values={radarValues} range={[0, 100]} />
        </ChartCard>
      )}

      {/* Source evidence */}
      {sourceRows.length > 0 && (
        <div className="bg-surface rounded-lg border border-[#E5E5E0] overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E5E5E0]">
            <h4 className="text-xs font-semibold">Source Evidence</h4>
          </div>
          <DataTable<SourceRow> columns={sourceColumns} rows={sourceRows} />
        </div>
      )}

      <div className="pt-2">
        <a
          href={`/dashboard/${id}/suppliers`}
          className="text-[12px] text-teal font-semibold hover:underline"
        >
          ← Back to suppliers
        </a>
      </div>
    </div>
  );
}
