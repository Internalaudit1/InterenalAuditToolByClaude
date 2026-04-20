"use client";

import { use, useEffect, useState } from "react";

import { RevisionHistoryPanel } from "@/components/action-plan-revision-history";
import { PageShell } from "@/components/layout/page-shell";
import { apiFetch } from "@/lib/api";
import { getPrimaryRole, hasPermission } from "@/lib/auth";

type ManagementReview = {
  id: number;
  review_note: string;
  review_decision: string;
  created_by_user_name?: string | null;
  created_at: string;
};

export default function ActionPlanDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [actionPlan, setActionPlan] = useState<any>(null);
  const [managementReviews, setManagementReviews] = useState<ManagementReview[]>([]);
  const [managementReviewForm, setManagementReviewForm] = useState({ review_note: "", review_decision: "Noted" });
  const [message, setMessage] = useState("");
  const role = getPrimaryRole();
  const canViewManagementReviews = hasPermission("management_reviews:view");
  const canCreateManagementReviews = role === "management" && hasPermission("management_reviews:create");

  async function load() {
    const [data, reviewData] = await Promise.all([
      apiFetch<any>(`/action-plans/${id}`),
      canViewManagementReviews ? apiFetch<ManagementReview[]>(`/action-plans/${id}/management-reviews`) : Promise.resolve([])
    ]);
    setActionPlan(data);
    setManagementReviews(reviewData);
  }

  useEffect(() => {
    load().catch(console.error);
  }, [id]);

  if (!actionPlan) return null;

  return (
    <PageShell title={actionPlan.observation_heading} eyebrow={actionPlan.action_plan_id} description="Status transitions are backend controlled. The UI only exposes actions allowed for the current role.">
      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="panel space-y-4 p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div><span className="chip">Audit</span><p className="mt-3 text-lg font-semibold">{actionPlan.audit_number}</p></div>
            <div><span className="chip">Target Date</span><p className="mt-3 text-lg font-semibold">{actionPlan.agreed_timeline}</p></div>
            <div><span className="chip">Auditor Status</span><p className="mt-3 text-lg font-semibold">{actionPlan.auditor_status}</p></div>
            <div><span className="chip">Auditee Status</span><p className="mt-3 text-lg font-semibold">{actionPlan.auditee_status}</p></div>
          </div>
          <div>
            <h2 className="font-serif text-2xl">Detailed Observation</h2>
            <p className="mt-3 text-sm text-slate">{actionPlan.detailed_observation}</p>
          </div>
          <div>
            <h2 className="font-serif text-2xl">Management Response</h2>
            <p className="mt-3 text-sm text-slate">{actionPlan.management_response || "No response yet."}</p>
          </div>
          <div>
            <h2 className="font-serif text-2xl">Agreed Action Plan</h2>
            <p className="mt-3 text-sm text-slate">{actionPlan.agreed_action_plan || "No agreed action plan yet."}</p>
          </div>
          <div className="rounded-2xl bg-sand/50 p-4">
            <h2 className="font-serif text-2xl">Auditee Implementation Remarks</h2>
            <p className="mt-3 whitespace-pre-wrap text-sm text-slate">{actionPlan.management_implementation_remarks || "No implementation remarks submitted yet."}</p>
          </div>
        </section>
        <section className="space-y-6">
          {canViewManagementReviews ? (
            <div className="panel space-y-4 p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-serif text-2xl">Management Reviews</h2>
                  <p className="mt-2 text-sm text-slate">Independent management notes and escalation comments. These do not change auditor or auditee status.</p>
                </div>
                <span className="chip">{managementReviews.length} note{managementReviews.length === 1 ? "" : "s"}</span>
              </div>
              {canCreateManagementReviews ? (
                <form
                  className="rounded-2xl border border-sand bg-cream p-4"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    await apiFetch(`/action-plans/${id}/management-reviews`, {
                      method: "POST",
                      body: JSON.stringify(managementReviewForm)
                    });
                    setManagementReviewForm({ review_note: "", review_decision: "Noted" });
                    setMessage("Management review note added.");
                    await load();
                  }}
                >
                  <label className="space-y-2 text-sm font-semibold">
                    <span>Review Decision</span>
                    <select
                      className="field"
                      value={managementReviewForm.review_decision}
                      onChange={(event) => setManagementReviewForm((prev) => ({ ...prev, review_decision: event.target.value }))}
                    >
                      <option value="Noted">Noted</option>
                      <option value="Needs Attention">Needs Attention</option>
                      <option value="Escalated">Escalated</option>
                    </select>
                  </label>
                  <label className="mt-3 block space-y-2 text-sm font-semibold">
                    <span>Review Note</span>
                    <textarea
                      className="field min-h-24"
                      value={managementReviewForm.review_note}
                      onChange={(event) => setManagementReviewForm((prev) => ({ ...prev, review_note: event.target.value }))}
                      placeholder="Add management review note"
                    />
                  </label>
                  <button className="button-primary mt-3">Add Review Note</button>
                </form>
              ) : null}
              <div className="max-h-72 space-y-3 overflow-y-auto pr-2">
                {managementReviews.map((review) => (
                  <article key={review.id} className="rounded-2xl border border-sand bg-cream p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold">{review.review_decision}</p>
                        <p className="mt-1 text-xs text-slate">By {review.created_by_user_name || "Management"}</p>
                      </div>
                      <p className="text-xs text-slate">{new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(review.created_at))}</p>
                    </div>
                    <p className="mt-3 whitespace-pre-wrap text-sm text-slate">{review.review_note}</p>
                  </article>
                ))}
                {!managementReviews.length ? (
                  <div className="rounded-2xl border border-dashed border-sand bg-cream p-4 text-sm text-slate">
                    No management review notes have been captured yet.
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}
          {role === "auditee" ? (
            <form
              className="panel space-y-4 p-6"
              onSubmit={async (event) => {
                event.preventDefault();
                const formData = new FormData(event.currentTarget);
                await apiFetch(`/action-plans/${id}/remarks`, {
                  method: "POST",
                  body: JSON.stringify({
                    management_implementation_remarks: formData.get("remarks")
                  })
                });
                setMessage("Implementation remarks updated.");
                await load();
              }}
            >
              <h2 className="font-serif text-2xl">Implementation Remarks</h2>
              <p className="text-sm text-slate">Auditee access is limited to updating implementation remarks. Status and auditor-side review fields are controlled separately.</p>
              <textarea name="remarks" className="field min-h-32" placeholder="Implementation remarks" defaultValue={actionPlan.management_implementation_remarks ?? ""} />
              <button className="button-primary">Save Remarks</button>
            </form>
          ) : null}
          {role !== "auditee" ? (
            <form
              className="panel space-y-4 p-6"
              onSubmit={async (event) => {
                event.preventDefault();
                const formData = new FormData(event.currentTarget);
                await apiFetch(`/action-plans/${id}/review`, {
                  method: "POST",
                  body: JSON.stringify({
                    auditor_status: formData.get("auditor_status"),
                    auditor_implementation_remarks: formData.get("remarks")
                  })
                });
                setMessage("Review submitted.");
                await load();
              }}
            >
              <h2 className="font-serif text-2xl">Auditor Review</h2>
              <div className="rounded-2xl border border-sand bg-cream p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-clay">Latest Auditee Remarks</p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate">{actionPlan.management_implementation_remarks || "No implementation remarks submitted yet."}</p>
              </div>
              <textarea name="remarks" className="field min-h-24" placeholder="Auditor remarks" />
              <select name="auditor_status" className="field">
                <option value="Under Review">Under Review</option>
                <option value="Completed">Completed</option>
                <option value="Reopened">Reopened</option>
              </select>
              <button className="button-primary">Submit Review</button>
            </form>
          ) : null}
          <RevisionHistoryPanel revisions={actionPlan.revisions} message={message} />
        </section>
      </div>
    </PageShell>
  );
}
