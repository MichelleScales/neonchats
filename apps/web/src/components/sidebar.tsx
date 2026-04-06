"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Megaphone, FileText, CheckSquare,
  Mic2, BarChart2, Plug, Settings, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/content", label: "Content Factory", icon: FileText },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/voice", label: "Brand Voice", icon: Mic2 },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/admin", label: "Admin", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 flex-shrink-0 border-r border-border flex flex-col bg-card">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-border">
        <span className="font-semibold text-sm tracking-tight">EMP Platform</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-0.5 px-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-primary text-primary-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User stub */}
      <div className="px-4 py-3 border-t border-border text-xs text-muted-foreground">
        Marketing Lead
      </div>
    </aside>
  );
}
