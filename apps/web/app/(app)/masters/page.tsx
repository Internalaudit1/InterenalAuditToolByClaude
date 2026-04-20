"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function MastersIndexPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/masters/countries");
  }, [router]);
  return null;
}

