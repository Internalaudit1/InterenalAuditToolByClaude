"use client";

import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { getSessionUser } from "@/lib/auth";

export function AppShell({ children }: { children: React.ReactNode }) {
  const user = getSessionUser();

  return (
    <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 p-6">
      <Sidebar permissions={user?.permissions ?? []} />
      <main className="flex-1 space-y-6">
        <Header />
        {children}
      </main>
    </div>
  );
}
