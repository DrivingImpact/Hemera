const STATUS_CONFIG: Record<string, { title: string; description: string; color: string }> = {
  uploaded: {
    title: "Your data has been uploaded",
    description: "Our team will review your submission and be in touch if we have any questions. Your analyst will begin work shortly.",
    color: "border-amber bg-amber-tint",
  },
  processing: {
    title: "Your data is being analysed",
    description: "Our analysts are classifying your transactions and calculating your carbon footprint.",
    color: "border-teal bg-teal-tint",
  },
  delivered: {
    title: "Your data is under review",
    description: "Our analysts are reviewing your carbon footprint for quality assurance. We'll notify you when it's ready.",
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
