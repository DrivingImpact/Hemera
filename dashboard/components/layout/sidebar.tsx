"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  name: string;
  href: string;
  icon: string;
  absolute?: boolean;
}

const CLIENT_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: "Analysis",
    items: [
      { name: "Overview", href: "", icon: "◉" },
      { name: "Carbon", href: "/carbon", icon: "◯" },
      { name: "Suppliers", href: "/suppliers", icon: "◯" },
      { name: "Data Quality", href: "/quality", icon: "◯" },
    ],
  },
  {
    label: "Actions",
    items: [
      { name: "Reduction", href: "/reduction", icon: "◯" },
      { name: "HemeraScope", href: "/hemerascope/report", icon: "◯" },
      { name: "Upload", href: "/upload", icon: "◯", absolute: true },
    ],
  },
];

const ADMIN_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: "Admin",
    items: [
      { name: "Clients", href: "/clients", icon: "◉", absolute: true },
      { name: "Upload", href: "/upload", icon: "◯", absolute: true },
    ],
  },
  {
    label: "Tools",
    items: [
      { name: "HemeraScope", href: "/hemerascope", icon: "◯" },
    ],
  },
];

export function Sidebar({
  engagementId,
  orgName,
  role,
}: {
  engagementId?: number;
  orgName: string;
  role: string;
}) {
  const pathname = usePathname();
  const basePath = engagementId ? `/dashboard/${engagementId}` : "/dashboard";
  const isAdmin = role === "admin";
  const sections = isAdmin ? ADMIN_SECTIONS : CLIENT_SECTIONS;

  return (
    <aside className="w-[220px] bg-slate flex flex-col flex-shrink-0 min-h-screen">
      <div className="px-5 pt-5 pb-4 border-b border-white/10">
        <div className="text-teal text-[11px] font-bold uppercase tracking-[2px]">Hemera</div>
        <div className="text-[#94A3B8] text-xs mt-1">{orgName}</div>
        {isAdmin && (
          <div className="mt-1.5">
            <span className="text-[9px] font-bold uppercase tracking-[1px] px-1.5 py-0.5 rounded bg-teal/15 text-teal">
              Admin
            </span>
          </div>
        )}
      </div>
      <nav className="mt-3 flex-1">
        {sections.map((section) => (
          <div key={section.label}>
            <div className="px-5 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-[1px] text-[#475569]">
              {section.label}
            </div>
            {section.items.map((item) => {
              const href = item.absolute ? `/dashboard${item.href}` : `${basePath}${item.href}`;
              const isActive = item.href === ""
                ? pathname === basePath
                : pathname.startsWith(href);

              return (
                <Link
                  key={item.name}
                  href={href}
                  className={`flex items-center gap-2.5 px-5 py-2 text-[13px] transition-colors ${
                    isActive
                      ? "text-white bg-teal/12 border-r-2 border-teal"
                      : "text-[#94A3B8] hover:text-white"
                  }`}
                >
                  <span className="w-4 text-center text-xs">{isActive ? "●" : item.icon}</span>
                  {item.name}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
