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
  const [openGroup, setOpenGroup] = useState<string | null>(null);

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
    const activeGroup = items.find((item) => visibleChildren(item).length && isItemActive(item));
    setOpenGroup(activeGroup?.href ?? null);
  }, [items, pathname]);

  return (
    <aside className="panel flex h-fit min-w-0 flex-col gap-3 overflow-hidden p-3 transition-[height] duration-200 lg:sticky lg:top-4 xl:p-4 2xl:top-6">
      <div className="shrink-0">
        <HclLogo subtitle="Internal Audit" labelClassName="font-semibold text-ink" />
        <h1 className="mt-3 font-serif text-lg leading-tight xl:text-xl 2xl:text-2xl">Operational Command</h1>
        <p className="mt-2 text-xs leading-5 text-slate 2xl:text-sm">Planning, remediation, reporting, and control intelligence in one workspace.</p>
      </div>
      <nav className="min-h-0 space-y-2 pr-1">
        {items.map((item) => {
          const children = visibleChildren(item);
          const hasChildren = children.length > 0;
          const isOpen = openGroup === item.href;
          const active = isItemActive(item);
          const activeChild = isChildActive(item);

          if (!hasChildren) {
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpenGroup(null)}
                className={cn(
                  "block rounded-2xl px-3 py-2 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-ink/30 xl:text-sm",
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
                onClick={() => setOpenGroup((previous) => (previous === item.href ? null : item.href))}
                className={cn(
                  "flex w-full items-center justify-between rounded-2xl px-3 py-2 text-left text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-ink/30 xl:text-sm",
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
                      onClick={() => setOpenGroup(item.href)}
                      className={cn(
                        "ml-2 block rounded-xl px-3 py-1.5 text-xs leading-5 transition focus:outline-none focus:ring-2 focus:ring-ink/20 xl:ml-3 xl:text-sm",
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
