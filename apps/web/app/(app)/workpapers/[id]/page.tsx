"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useState } from "react";

import { RichTextEditor } from "@/components/forms/rich-text-editor";
import { PageShell } from "@/components/layout/page-shell";
import { RichTextContent } from "@/components/rich-text-content";
import { apiDownload, apiFetch, apiOpenFile } from "@/lib/api";
import { hasPermission } from "@/lib/auth";

type WorkpaperVersion = {
  id: number;
  version_no: number;
  document_id: number;
  change_summary?: string | null;
  uploaded_by_name?: string | null;
  uploaded_at: string;
  hash_checksum: string;
};

type WorkpaperReview = {
  id: number;
  reviewer_user_id?: number | null;
  reviewer_name?: string | null;
  review_status: string;
  review_comment?: string | null;
  reviewed_at: string;
};

type WorkpaperDetail = {
  id: number;
  workpaper_code: string;
  audit_id: number;
  activity_id?: number | null;
  observation_id?: number | null;
  test_procedure_id?: number | null;
  title: string;
  folder_path?: string | null;
  status: string;
  current_version_no: number;
  owner_user_id?: number | null;
  owner_name?: string | null;
  reviewer_user_id?: number | null;
  reviewer_name?: string | null;
  signoff_at?: string | null;
  versions: WorkpaperVersion[];
  reviews: WorkpaperReview[];
  linked_evidence_ids: number[];
};

type EvidenceItem = { id: number; evidence_code: string; source_name: string; confidentiality_level: string };

export default function WorkpaperDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [tab, setTab] = useState<"overview" | "versions" | "review" | "evidence">("overview");
  const [workpaper, setWorkpaper] = useState<WorkpaperDetail | null>(null);
  const [availableEvidence, setAvailableEvidence] = useState<EvidenceItem[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [changeSummary, setChangeSummary] = useState("");
  const [reviewComment, setReviewComment] = useState("");
  const [submitComment, setSubmitComment] = useState("");
  const [linkEvidenceId, setLinkEvidenceId] = useState("");
  const canManage = hasPermission("workpapers:manage");
  const canReview = hasPermission("workpapers:review");
  const canManageEvidence = hasPermission("evidence:manage");

  const nextReviewAction = useMemo(() => {
    if (!workpaper) return null;
    if (workpaper.status === "Submitted for Review") return { label: "Mark Reviewed", value: "Reviewed" };
    if (workpaper.status === "Reviewed") return { label: "Approve", value: "Approved" };
    if (workpaper.status === "Approved") return { label: "Lock", value: "Locked" };
    return null;
  }, [workpaper]);

  async function load() {
    const detail = await apiFetch<WorkpaperDetail>(`/workpapers/${id}`);
    setWorkpaper(detail);
    const evidenceData = await apiFetch<{ items: EvidenceItem[] }>(`/evidence?page_size=100&audit_id=${detail.audit_id}`);
    setAvailableEvidence(evidenceData.items);
  }

  useEffect(() => {
    load().catch((err) => setError((err as Error).message));
  }, [id]);

  if (!workpaper) return null;

  return (
    <PageShell
      title={workpaper.title}
      eyebrow={workpaper.workpaper_code}
      description="Control version history, reviewer sign-off, and evidence linkage for this workpaper."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href={`/audits/${workpaper.audit_id}`} className="button-secondary px-4 py-2">
            Open Audit
          </Link>
          <Link href={`/evidence?audit_id=${workpaper.audit_id}`} className="button-secondary px-4 py-2">
            Evidence Register
          </Link>
        </div>
      }
    >
      {message ? <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-sm text-emerald-800">{message}</div> : null}
      {error ? <div className="rounded-2xl bg-ember/10 px-4 py-3 text-sm text-ember">{error}</div> : null}

      <div className="flex flex-wrap gap-2">
        {[
          ["overview", "Overview"],
          ["versions", "Versions"],
          ["review", "Review / Sign-off"],
          ["evidence", "Evidence"],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={tab === value ? "button-primary" : "button-secondary"}
            onClick={() => setTab(value as typeof tab)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <section className="panel p-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div><span className="chip">Status</span><p className="mt-3 text-lg font-semibold">{workpaper.status}</p></div>
            <div><span className="chip">Version</span><p className="mt-3 text-lg font-semibold">v{workpaper.current_version_no}</p></div>
            <div><span className="chip">Owner</span><p className="mt-3 text-lg font-semibold">{workpaper.owner_name ?? (workpaper.owner_user_id ? `User #${workpaper.owner_user_id}` : "--")}</p></div>
            <div><span className="chip">Reviewer</span><p className="mt-3 text-lg font-semibold">{workpaper.reviewer_name ?? (workpaper.reviewer_user_id ? `User #${workpaper.reviewer_user_id}` : "--")}</p></div>
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <label className="space-y-2 text-sm font-semibold">
              <span>Title</span>
              <input
                className="field"
                disabled={!canManage || workpaper.status === "Locked"}
                value={workpaper.title}
                onChange={(event) => setWorkpaper((prev) => (prev ? { ...prev, title: event.target.value } : prev))}
              />
            </label>
            <label className="space-y-2 text-sm font-semibold">
              <span>Folder Path</span>
              <input
                className="field"
                disabled={!canManage || workpaper.status === "Locked"}
                value={workpaper.folder_path ?? ""}
                onChange={(event) => setWorkpaper((prev) => (prev ? { ...prev, folder_path: event.target.value } : prev))}
              />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            {canManage && workpaper.status !== "Locked" ? (
              <button
                className="button-primary"
                onClick={async () => {
                  try {
                    await apiFetch(`/workpapers/${id}`, {
                      method: "PATCH",
                      body: JSON.stringify({
                        title: workpaper.title,
                        folder_path: workpaper.folder_path || null,
                      }),
                    });
                    setMessage("Workpaper updated.");
                    setError("");
                    await load();
                  } catch (err) {
                    setMessage("");
                    setError((err as Error).message);
                  }
                }}
              >
                Save Changes
              </button>
            ) : null}
            {workpaper.signoff_at ? <p className="text-sm text-slate">Signed off at {new Date(workpaper.signoff_at).toLocaleString()}</p> : null}
          </div>
        </section>
      ) : null}

      {tab === "versions" ? (
        <section className="panel p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-serif text-2xl">Version History</h2>
            <p className="text-sm text-slate">Immutable history is preserved; new uploads create a new numbered version and reset review status if needed.</p>
          </div>
          {canManage && workpaper.status !== "Locked" ? (
            <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_220px_auto]">
              <input type="file" className="field" onChange={(event) => setVersionFile(event.target.files?.[0] ?? null)} />
              <input className="field" placeholder="Change summary" value={changeSummary} onChange={(event) => setChangeSummary(event.target.value)} />
              <button
                className="button-primary"
                onClick={async () => {
                  if (!versionFile) return;
                  try {
                    const formData = new FormData();
                    formData.append("change_summary", changeSummary);
                    formData.append("file", versionFile);
                    await apiFetch(`/workpapers/${id}/versions`, { method: "POST", body: formData });
                    setVersionFile(null);
                    setChangeSummary("");
                    setMessage("New workpaper version uploaded.");
                    setError("");
                    await load();
                  } catch (err) {
                    setMessage("");
                    setError((err as Error).message);
                  }
                }}
              >
                Upload Version
              </button>
            </div>
          ) : null}
          <div className="mt-4 space-y-3">
            {[...workpaper.versions].sort((a, b) => b.version_no - a.version_no).map((version) => (
              <div key={version.id} className="rounded-2xl border border-sand bg-cream p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <p className="font-semibold">Version {version.version_no}</p>
                    <p className="text-sm text-slate">{new Date(version.uploaded_at).toLocaleString()}</p>
                    {version.uploaded_by_name ? <p className="text-sm text-slate">Uploaded by {version.uploaded_by_name}</p> : null}
                    <RichTextContent value={version.change_summary} emptyText="No summary added." className="text-sm text-slate" />
                    <p className="text-xs text-slate">Checksum: {version.hash_checksum}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button className="button-secondary px-4 py-2" onClick={() => apiOpenFile(`/workpapers/versions/${version.id}/view`)}>
                      View File
                    </button>
                    <button className="button-secondary px-4 py-2" onClick={() => apiDownload(`/workpapers/versions/${version.id}/download`, `${workpaper.workpaper_code}-v${version.version_no}`)}>
                      Download
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {!workpaper.versions.length ? <p className="text-sm text-slate">No versions uploaded yet.</p> : null}
          </div>
        </section>
      ) : null}

      {tab === "review" ? (
        <section className="panel p-6">
          <h2 className="font-serif text-2xl">Review / Sign-off</h2>
          <div className="mt-4 grid gap-6 xl:grid-cols-[360px_1fr]">
            <div className="space-y-3 rounded-2xl border border-sand bg-cream p-4">
              <p className="text-sm text-slate">Current status: <span className="font-semibold text-ink">{workpaper.status}</span></p>
              {canManage && workpaper.status === "Draft" ? (
                <>
                  <RichTextEditor value={submitComment} onChange={setSubmitComment} placeholder="Submission note" minHeightClass="min-h-24" />
                  <button
                    className="button-primary"
                    onClick={async () => {
                      try {
                        await apiFetch(`/workpapers/${id}/submit-review`, {
                          method: "POST",
                          body: JSON.stringify({ comment: submitComment || null }),
                        });
                        setSubmitComment("");
                        setMessage("Workpaper submitted for review.");
                        setError("");
                        await load();
                      } catch (err) {
                        setMessage("");
                        setError((err as Error).message);
                      }
                    }}
                  >
                    Submit For Review
                  </button>
                </>
              ) : null}
              {canReview && nextReviewAction ? (
                <>
                  <RichTextEditor value={reviewComment} onChange={setReviewComment} placeholder="Reviewer comment" minHeightClass="min-h-24" />
                  <button
                    className="button-primary"
                    onClick={async () => {
                      try {
                        await apiFetch(`/workpapers/${id}/review`, {
                          method: "POST",
                          body: JSON.stringify({
                            review_status: nextReviewAction.value,
                            review_comment: reviewComment || null,
                          }),
                        });
                        setReviewComment("");
                        setMessage(`Workpaper moved to ${nextReviewAction.value}.`);
                        setError("");
                        await load();
                      } catch (err) {
                        setMessage("");
                        setError((err as Error).message);
                      }
                    }}
                  >
                    {nextReviewAction.label}
                  </button>
                </>
              ) : null}
            </div>
            <div className="space-y-3">
              {[...workpaper.reviews].sort((a, b) => +new Date(b.reviewed_at) - +new Date(a.reviewed_at)).map((review) => (
                <div key={review.id} className="rounded-2xl border border-sand bg-cream p-4">
                  <p className="font-semibold">{review.review_status}</p>
                  <p className="text-sm text-slate">{new Date(review.reviewed_at).toLocaleString()}</p>
                  {review.reviewer_name ? <p className="text-sm text-slate">Reviewed by {review.reviewer_name}</p> : null}
                  <RichTextContent value={review.review_comment} emptyText="No comment added." className="mt-2 text-sm text-slate" />
                </div>
              ))}
              {!workpaper.reviews.length ? <p className="text-sm text-slate">No review entries yet.</p> : null}
            </div>
          </div>
        </section>
      ) : null}

      {tab === "evidence" ? (
        <section className="panel p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-serif text-2xl">Linked Evidence</h2>
            <Link href={`/evidence?audit_id=${workpaper.audit_id}`} className="button-secondary px-4 py-2">
              Open Evidence Register
            </Link>
          </div>
          {canManageEvidence ? (
            <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
              <select className="field" value={linkEvidenceId} onChange={(event) => setLinkEvidenceId(event.target.value)}>
                <option value="">Select evidence to link</option>
                {availableEvidence.map((evidence) => (
                  <option key={evidence.id} value={evidence.id}>
                    {evidence.evidence_code} - {evidence.source_name} ({evidence.confidentiality_level})
                  </option>
                ))}
              </select>
              <button
                className="button-primary"
                onClick={async () => {
                  if (!linkEvidenceId) return;
                  try {
                    await apiFetch(`/evidence/${linkEvidenceId}/link`, {
                      method: "POST",
                      body: JSON.stringify({ linked_module: "workpaper", linked_record_id: workpaper.id }),
                    });
                    setLinkEvidenceId("");
                    setMessage("Evidence linked to workpaper.");
                    setError("");
                    await load();
                  } catch (err) {
                    setMessage("");
                    setError((err as Error).message);
                  }
                }}
              >
                Link Evidence
              </button>
            </div>
          ) : null}
          <div className="mt-4 space-y-3">
            {workpaper.linked_evidence_ids.map((evidenceId) => {
              const evidence = availableEvidence.find((entry) => entry.id === evidenceId);
              return (
                <div key={evidenceId} className="rounded-2xl border border-sand bg-cream p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold">{evidence?.evidence_code ?? `Evidence #${evidenceId}`}</p>
                      <p className="text-sm text-slate">{evidence?.source_name ?? "Linked evidence record"}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/evidence/${evidenceId}`} className="button-secondary px-4 py-2">
                        Open
                      </Link>
                      <button className="button-secondary px-4 py-2" onClick={() => apiOpenFile(`/evidence/${evidenceId}/view`)}>
                        View File
                      </button>
                      <button className="button-secondary px-4 py-2" onClick={() => apiDownload(`/evidence/${evidenceId}/download`, `evidence-${evidenceId}`)}>
                        Download
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
            {!workpaper.linked_evidence_ids.length ? <p className="text-sm text-slate">No evidence linked to this workpaper yet.</p> : null}
          </div>
        </section>
      ) : null}
    </PageShell>
  );
}
