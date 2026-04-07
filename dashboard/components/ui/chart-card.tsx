import Link from "next/link";

export function ChartCard({
  title,
  linkHref,
  linkText,
  className,
  children,
}: {
  title: string;
  linkHref?: string;
  linkText?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`bg-surface rounded-lg p-4 border border-[#E5E5E0] ${className || ""}`}>
      <h4 className="text-xs font-semibold mb-2">{title}</h4>
      {children}
      {linkHref && (
        <Link href={linkHref} className="text-[11px] text-teal font-semibold mt-2 block">
          {linkText || "View details →"}
        </Link>
      )}
    </div>
  );
}
