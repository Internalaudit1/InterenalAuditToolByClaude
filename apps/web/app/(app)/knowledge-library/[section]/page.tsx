import { notFound } from "next/navigation";

import { ResourcePage } from "@/components/resource-page";
import { knowledgePageConfig } from "@/lib/page-config";

export default async function KnowledgeSectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const config = knowledgePageConfig[section];
  if (!config) notFound();
  return <ResourcePage {...config} />;
}
