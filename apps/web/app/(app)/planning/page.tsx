"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getPrimaryRole } from "@/lib/auth";

export default function PlanningIndexPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getPrimaryRole() === "auditee" ? "/planning/audit-plans" : "/planning/process-risk-mappings");
  }, [router]);

  return null;
}

