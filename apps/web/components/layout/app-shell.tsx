"use client";

import { startTransition, useEffect, useState } from "react";

import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { getSessionUser, type SessionUser } from "@/lib/auth";
import { refreshSessionSilently } from "@/lib/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    let active = true;

    async function syncSession() {
      startTransition(() => {
        setUser(getSessionUser());
      });
      const refreshedUser = await refreshSessionSilently();
      if (!active) return;
      startTransition(() => {
        setUser(refreshedUser ?? getSessionUser());
      });
    }

    void syncSession();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="mx-auto grid min-h-screen w-full max-w-[1500px] grid-cols-1 gap-3 p-2.5 sm:p-4 lg:grid-cols-[13.5rem_minmax(0,1fr)] xl:grid-cols-[14.5rem_minmax(0,1fr)] 2xl:max-w-[1680px] 2xl:grid-cols-[16rem_minmax(0,1fr)] 2xl:gap-5 2xl:p-6">
      <Sidebar permissions={user?.permissions ?? []} />
      <main className="min-w-0 space-y-4 lg:space-y-5">
        <Header user={user} />
        {children}
      </main>
    </div>
  );
}
