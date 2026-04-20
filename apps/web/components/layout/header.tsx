"use client";

import { Bell, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { HclLogo } from "@/components/branding/hcl-logo";
import { clearSession, getSessionUser } from "@/lib/auth";

export function Header() {
  const router = useRouter();
  const user = getSessionUser();

  return (
    <header className="panel flex items-center justify-between gap-4 p-5">
      <div>
        <HclLogo subtitle="Internal Audit Workspace" />
      </div>
      <div className="flex items-center gap-3">
        <button className="button-secondary gap-2">
          <Bell className="h-4 w-4" />
          Notifications
        </button>
        <div className="rounded-2xl border border-sand bg-cream px-4 py-3 text-right">
          <div className="text-sm font-semibold">{user?.full_name ?? "User"}</div>
          <div className="text-xs uppercase tracking-[0.16em] text-slate">{user?.roles?.[0] ?? "guest"}</div>
        </div>
        <button
          className="button-primary gap-2"
          onClick={() => {
            clearSession();
            router.push("/login");
          }}
        >
          <LogOut className="h-4 w-4" />
          Log out
        </button>
      </div>
    </header>
  );
}
