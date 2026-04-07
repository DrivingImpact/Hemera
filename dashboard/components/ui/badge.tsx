const VARIANTS = {
  teal: "bg-teal-tint text-[#0F766E]",
  amber: "bg-amber-tint text-[#92400E]",
  red: "bg-red-tint text-[#991B1B]",
  green: "bg-[#D1FAE5] text-[#065F46]",
  slate: "bg-slate-tint text-[#475569]",
};

export function Badge({
  children,
  variant = "slate",
}: {
  children: React.ReactNode;
  variant?: keyof typeof VARIANTS;
}) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${VARIANTS[variant]}`}>
      {children}
    </span>
  );
}
