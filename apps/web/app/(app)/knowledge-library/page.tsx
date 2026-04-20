"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function KnowledgeLibraryIndexPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/knowledge-library/process-universe");
  }, [router]);
  return null;
}

