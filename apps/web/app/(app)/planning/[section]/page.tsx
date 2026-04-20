import { notFound } from "next/navigation";

import { ResourcePage } from "@/components/resource-page";
import { planningPageConfig } from "@/lib/page-config";

export default async function PlanningSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const config = planningPageConfig[section];
  if (!config) notFound();
  return <ResourcePage {...config} />;
}
