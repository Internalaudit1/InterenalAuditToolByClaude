"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { PageShell } from "@/components/layout/page-shell";
import { RichTextContent } from "@/components/rich-text-content";
import { apiDownload, apiFetch, apiOpenFile } from "@/lib/api";
import { hasPermission } from "@/lib/auth";

type LinkItem = { id: number; linked_module: string; linked_record_id: number };
type WorkpaperOption = { id: number; workpaper_code: string; title: string };
type ObservationOption = { id: number; observation_number: string; heading: string };
type EvidenceDetail = {
  id: number;
  evidence_code: string;
  audit_id: number;
  source_type: string;
  source_name: string;
  evidence_description?: string | null;
  confidentiality_level: string;
  collected_at: string;
  document_id: number;
  links: LinkItem[];
};

export default function EvidenceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [evidence, setEvidence] = useState<EvidenceDetail | null>(null);
  const [workpapers, setWorkpapers] = useState<WorkpaperOption[]>([]);
  const [observations, setObservations] = useState<ObservationOption[]>([]);
  const [linkedModule, setLinkedModule] = useState("workpaper");
  const [linkedRecordId, setLinkedRecordId] = useState("");
  const [testProcedureId, setTestProcedureId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const canManage = hasPermission("evidence:manage");

  async function load() {
    const detail = await apiFetch<EvidenceDetail>(`/evidence/${id}`);
    const [workpaperData, observationData] = await Promise.all([
      apiFetch<{ items: WorkpaperOption[] }>(`/workpapers?page_size=100&audit_id=${detail.audit_id}`),
      apiFetch<{ items: ObservationOption[] }>(`/audits/${detail.audit_id}/observations?page_size=100`),
    ]);
    setEvidence(detail);
    setWorkpapers(workpaperData.items);
    setObservations(observationData.items);
  }

  useEffect(() => {
    load().catch((err) => setError((err as Error).message));
  }, [id]);

  if (!evidence) return null;

  const currentOptions =
    linkedModule === "workpaper"
      ? workpapers.map((workpaper) => ({ id: workpaper.id, label: `${workpaper.workpaper_code} - ${workpaper.title}` }))
      : observations.map((observation) => ({ id: observation.id, label: `${observation.observation_number} - ${observation.heading}` }));

  return (
    <PageShell
      title={evidence.source_name}
      eyebrow={evidence.evidence_code}
      description="Review evidence metadata, download the registered support, and link it to workpapers or findings."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href={`/audits/${evidence.audit_id}`} className="button-secondary px-4 py-2">
            Open Audit
          </Link>
          <button className="button-secondary px-4 py-2" onClick={() => apiOpenFile(`/evidence/${evidence.id}/view`)}>
            View File
          </button>
          <button className="button-secondary px-4 py-2" onClick={() => apiDownload(`/evidence/${evidence.id}/download`, `${evidence.evidence_code}.bin`)}>
            Download
          </button>
        </div>
      }
    >
      {message ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{message}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}

      <section className="panel p-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div><span className="chip">Source Type</span><p className="mt-3 text-lg font-semibold">{evidence.source_type}</p></div>
          <div><span className="chip">Confidentiality</span><p className="mt-3 text-lg font-semibold">{evidence.confidentiality_level}</p></div>
          <div><span className="chip">Collected At</span><p className="mt-3 text-lg font-semibold">{new Date(evidence.collected_at).toLocaleString()}</p></div>
          <div><span className="chip">Document</span><p className="mt-3 text-lg font-semibold">Attachment #{evidence.document_id}</p></div>
        </div>
        <div className="mt-6 rounded-2xl border border-sand bg-cream p-4">
          <p className="font-semibold">Description</p>
          <RichTextContent value={evidence.evidence_description} emptyText="No description captured." className="mt-2 text-sm text-slate" />
        </div>
      </section>

      <section className="panel p-6">
        <h2 className="font-serif text-2xl">Links</h2>
        {canManage ? (
          <div className="mt-4 grid gap-3 md:grid-cols-[220px_1fr_auto]">
            <select
              className="field"
              value={linkedModule}
              onChange={(event) => {
                setLinkedModule(event.target.value);
                setLinkedRecordId("");
                setTestProcedureId("");
              }}
            >
              <option value="workpaper">Workpaper</option>
              <option value="observation">Observation</option>
              <option value="test_procedure">Test Procedure</option>
            </select>
            {linkedModule === "test_procedure" ? (
              <input className="field" type="number" min="1" placeholder="Future test procedure reference" value={testProcedureId} onChange={(event) => setTestProcedureId(event.target.value)} />
            ) : (
              <select className="field" value={linkedRecordId} onChange={(event) => setLinkedRecordId(event.target.value)}>
                <option value="">Select {linkedModule === "workpaper" ? "Workpaper" : "Observation"}</option>
                {currentOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            )}
            <button
              className="button-primary"
              onClick={async () => {
                const recordId = linkedModule === "test_procedure" ? testProcedureId : linkedRecordId;
                if (!recordId) return;
                try {
                  await apiFetch(`/evidence/${id}/link`, {
                    method: "POST",
                    body: JSON.stringify({
                      linked_module: linkedModule,
                      linked_record_id: Number(recordId),
                    }),
                  });
                  setLinkedRecordId("");
                  setTestProcedureId("");
                  setMessage("Evidence link saved.");
                  setError("");
                  await load();
                } catch (err) {
                  setMessage("");
                  setError((err as Error).message);
                }
              }}
            >
              Link
            </button>
          </div>
        ) : null}
        <div className="mt-4 space-y-3">
          {evidence.links.map((link) => (
            <div key={link.id} className="rounded-2xl border border-sand bg-cream p-4">
              <p className="font-semibold">{link.linked_module.replaceAll("_", " ")}</p>
              <p className="mt-2 text-sm text-slate">Record ID: {link.linked_record_id}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {link.linked_module === "workpaper" ? (
                  <Link href={`/workpapers/${link.linked_record_id}`} className="button-secondary px-4 py-2">
                    Open Workpaper
                  </Link>
                ) : null}
                {link.linked_module === "observation" ? (
                  <Link href={`/audits/${evidence.audit_id}`} className="button-secondary px-4 py-2">
                    Open Audit Observations
                  </Link>
                ) : null}
              </div>
            </div>
          ))}
          {!evidence.links.length ? <p className="text-sm text-slate">No links created yet.</p> : null}
        </div>
      </section>
    </PageShell>
  );
}
