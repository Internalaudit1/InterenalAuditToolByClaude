"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { HclLogo } from "@/components/branding/hcl-logo";
import { type NavItem, visibleNavItems } from "@/lib/navigation";
import { cn } from "@/lib/utils";

export function Sidebar({ permissions }: { permissions: string[] }) {
  const pathname = usePathname();
  const items = useMemo(() => visibleNavItems(permissions), [permissions]);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});

  function visibleChildren(item: NavItem) {
    return item.children ?? [];
  }

  function isItemActive(item: NavItem) {
    return pathname === item.href || pathname.startsWith(`${item.href}/`);
  }

  function isChildActive(item: NavItem) {
    return visibleChildren(item).some((child) => pathname === child.href || pathname.startsWith(`${child.href}/`));
  }

  useEffect(() => {
    setOpenGroups((previous) => {
      const next = { ...previous };
      items.forEach((item) => {
        if (visibleChildren(item).length && isItemActive(item)) {
          next[item.href] = true;
        }
      });
      return next;
    });
  }, [items, pathname]);

  return (
    <aside className="panel flex h-full w-full max-w-xs flex-col gap-4 p-5">
      <div>
        <HclLogo subtitle="Internal Audit" labelClassName="font-semibold text-ink" />
        <h1 className="mt-3 font-serif text-2xl">Operational Command</h1>
        <p className="mt-2 text-sm text-slate">Planning, remediation, reporting, and control intelligence in one workspace.</p>
      </div>
      <nav className="space-y-2">
        {items.map((item) => {
          const children = visibleChildren(item);
          const hasChildren = children.length > 0;
          const isOpen = Boolean(openGroups[item.href]);
          const active = isItemActive(item);
          const activeChild = isChildActive(item);

          if (!hasChildren) {
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "block rounded-2xl px-4 py-3 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-ink/30",
                  active ? "bg-ink text-white" : "bg-white/70 text-ink hover:bg-sand"
                )}
              >
                {item.label}
              </Link>
            );
          }

          return (
            <div key={item.href} className="space-y-1">
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpenGroups((previous) => ({ ...previous, [item.href]: !previous[item.href] }))}
                className={cn(
                  "flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-ink/30",
                  active || activeChild ? "bg-ink text-white" : "bg-white/70 text-ink hover:bg-sand"
                )}
              >
                <span>{item.label}</span>
                <span className={cn("text-xs transition-transform duration-200", isOpen ? "rotate-90" : "rotate-0")}>{">"}</span>
              </button>
              <div
                className={cn(
                  "grid overflow-hidden transition-all duration-200 ease-out",
                  isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                )}
              >
                <div className="min-h-0 space-y-1">
                  {children.map((child) => (
                    <Link
                      key={child.href}
                      href={child.href}
                      className={cn(
                        "ml-3 block rounded-xl px-4 py-2 text-sm transition focus:outline-none focus:ring-2 focus:ring-ink/20",
                        pathname.startsWith(child.href) ? "bg-sand text-ink" : "text-slate hover:bg-white/60"
                      )}
                    >
                      {child.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
