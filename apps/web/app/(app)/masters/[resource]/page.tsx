import { notFound } from "next/navigation";

import { ResourcePage } from "@/components/resource-page";
import { masterPageConfig } from "@/lib/page-config";

export default async function MasterResourcePage({ params }: { params: Promise<{ resource: string }> }) {
  const { resource } = await params;
  const config = masterPageConfig[resource];
  if (!config) notFound();
  return <ResourcePage {...config} />;
}
