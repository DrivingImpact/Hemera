const STATUS_CONFIG: Record<string, { title: string; description: string; color: string }> = {
  uploaded: {
    title: "Your data has been uploaded",
    description: "Our team will review your submission and get back to you shortly.",
    color: "border-amber bg-amber-tint",
  },
  processing: {
    title: "Your data is being processed",
    description: "We're classifying transactions and calculating your carbon footprint. This may take a few minutes.",
    color: "border-teal bg-teal-tint",
  },
  delivered: {
    title: "Awaiting analyst approval",
    description: "Your carbon footprint has been calculated and is pending quality review by our team.",
    color: "border-teal bg-teal-tint",
  },
};

export function PendingBanner({ status }: { status: string }) {
  const config = STATUS_CONFIG[status];
  if (!config) return null;

  return (
    <div className={`rounded-lg border-l-4 p-4 mb-6 ${config.color}`}>
      <h3 className="text-sm font-semibold">{config.title}</h3>
      <p className="text-xs text-muted mt-1">{config.description}</p>
    </div>
  );
}
