"use client";

import { Bell, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { HclLogo } from "@/components/branding/hcl-logo";
import { clearSession, type SessionUser } from "@/lib/auth";

export function Header({ user }: { user: SessionUser | null }) {
  const router = useRouter();

  return (
    <header className="panel flex min-w-0 flex-col gap-3 p-4 xl:flex-row xl:items-center xl:justify-between">
      <div className="min-w-0">
        <HclLogo subtitle="Internal Audit Workspace" />
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-2 xl:justify-end">
        <button className="button-secondary gap-2 px-4">
          <Bell className="h-4 w-4" />
          Notifications
        </button>
        <div className="min-w-0 rounded-2xl border border-sand bg-cream px-4 py-2.5 text-left xl:text-right">
          <div className="max-w-52 truncate text-sm font-semibold">{user?.full_name ?? "User"}</div>
          <div className="text-xs uppercase tracking-[0.16em] text-slate">{user?.roles?.[0] ?? "guest"}</div>
        </div>
        <button
          className="button-primary gap-2 px-4"
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
