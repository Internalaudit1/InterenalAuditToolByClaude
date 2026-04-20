"use client";

import { useState } from "react";

type RevisionStatusSnapshot = Record<string, unknown>;

export type ActionPlanRevision = {
  id?: number;
  response_code?: string | null;
  revision_number?: number | null;
  management_implementation_remarks?: string | null;
  revised_date?: string | null;
  file_attachment_id?: number | null;
  updated_by_user_id?: number | null;
  status_snapshot?: RevisionStatusSnapshot | null;
  created_at?: string | null;
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
};

type RevisionHistoryPanelProps = {
  revisions?: ActionPlanRevision[] | null;
  message?: string;
};

const COMPACT_REVISION_COUNT = 3;

function getRevisionKey(revision: ActionPlanRevision) {
  if (revision.revision_number !== null && revision.revision_number !== undefined) {
    return `revision-${revision.revision_number}`;
  }
  if (revision.id !== null && revision.id !== undefined) {
    return `id-${revision.id}`;
  }
  if (revision.response_code) {
    return `response-${revision.response_code}`;
  }
  return `${revision.updated_at ?? revision.created_at ?? "unknown"}-${revision.management_implementation_remarks ?? ""}`;
}

function getRevisionTime(revision: ActionPlanRevision) {
  const rawDate = revision.updated_at ?? revision.created_at ?? revision.revised_date;
  const timestamp = rawDate ? Date.parse(rawDate) : 0;
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function normalizeRevisions(revisions?: ActionPlanRevision[] | null) {
  const revisionMap = new Map<string, ActionPlanRevision>();

  for (const revision of revisions ?? []) {
    const key = getRevisionKey(revision);
    const existing = revisionMap.get(key);

    if (!existing || getRevisionTime(revision) >= getRevisionTime(existing)) {
      revisionMap.set(key, revision);
    }
  }

  return Array.from(revisionMap.values()).sort((left, right) => {
    const revisionNumberDelta = Number(right.revision_number ?? 0) - Number(left.revision_number ?? 0);
    if (revisionNumberDelta !== 0) {
      return revisionNumberDelta;
    }
    return getRevisionTime(right) - getRevisionTime(left);
  });
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Not captured";
  }

  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return value;
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(timestamp));
}

function formatDate(value?: string | null) {
  if (!value) {
    return "Not set";
  }

  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return value;
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium"
  }).format(new Date(timestamp));
}

function toDisplayLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getUpdatedBy(revision: ActionPlanRevision) {
  return revision.updated_by || revision.created_by || (revision.updated_by_user_id ? `User #${revision.updated_by_user_id}` : "Not captured");
}

function getComment(revision: ActionPlanRevision) {
  return revision.management_implementation_remarks?.trim() || "No remarks captured for this revision.";
}

function getPreview(value: string) {
  return value.length > 130 ? `${value.slice(0, 130)}...` : value;
}

function RevisionTimelineItem({
  revision,
  expanded,
  onToggle,
  isLast
}: {
  revision: ActionPlanRevision;
  expanded: boolean;
  onToggle: () => void;
  isLast: boolean;
}) {
  const comment = getComment(revision);
  const statusEntries = Object.entries(revision.status_snapshot ?? {}).filter(([, value]) => value !== null && value !== undefined && value !== "");

  return (
    <div className="relative pl-7">
      <span className="absolute left-0 top-2 h-3 w-3 rounded-full bg-sage ring-4 ring-cream" />
      {!isLast ? <span className="absolute bottom-0 left-[5px] top-6 w-px bg-sand" /> : null}
      <article className="rounded-2xl border border-sand bg-cream p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-clay">Revision {revision.revision_number ?? "--"}</p>
            <h3 className="mt-1 text-sm font-semibold text-ink">{revision.response_code || "Response update"}</h3>
          </div>
          <div className="text-left text-xs text-slate sm:text-right">
            <p>Updated by {getUpdatedBy(revision)}</p>
            <p>{formatDateTime(revision.updated_at ?? revision.created_at)}</p>
          </div>
        </div>

        {statusEntries.length ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {statusEntries.map(([key, value]) => (
              <span key={key} className="rounded-full bg-sand px-3 py-1 text-xs font-semibold text-ink">
                {toDisplayLabel(key)}: {String(value)}
              </span>
            ))}
          </div>
        ) : null}

        <p className="mt-3 whitespace-pre-wrap text-sm text-slate">{expanded ? comment : getPreview(comment)}</p>

        {expanded ? (
          <dl className="mt-4 grid gap-3 rounded-2xl bg-white/60 p-3 text-xs text-slate sm:grid-cols-2">
            <div>
              <dt className="font-semibold text-ink">Revised Date</dt>
              <dd className="mt-1">{formatDate(revision.revised_date)}</dd>
            </div>
            <div>
              <dt className="font-semibold text-ink">Evidence Attachment</dt>
              <dd className="mt-1">{revision.file_attachment_id ? `Attachment #${revision.file_attachment_id}` : "No file linked"}</dd>
            </div>
          </dl>
        ) : null}

        <button type="button" className="mt-3 text-sm font-semibold text-clay underline-offset-4 hover:underline" onClick={onToggle}>
          {expanded ? "Hide details" : "View details"}
        </button>
      </article>
    </div>
  );
}

export function RevisionHistoryPanel({ revisions, message }: RevisionHistoryPanelProps) {
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [fullHistoryOpen, setFullHistoryOpen] = useState(false);
  const normalizedRevisions = normalizeRevisions(revisions);
  const compactRevisions = normalizedRevisions.slice(0, COMPACT_REVISION_COUNT);

  function toggleRevision(key: string) {
    setExpandedKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function renderTimeline(items: ActionPlanRevision[]) {
    if (!items.length) {
      return (
        <div className="rounded-2xl border border-dashed border-sand bg-cream p-4 text-sm text-slate">
          No revision history has been captured yet.
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {items.map((revision, index) => {
          const key = getRevisionKey(revision);
          return (
            <RevisionTimelineItem
              key={key}
              revision={revision}
              expanded={expandedKeys.has(key)}
              onToggle={() => toggleRevision(key)}
              isLast={index === items.length - 1}
            />
          );
        })}
      </div>
    );
  }

  return (
    <>
      <div className="panel p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-serif text-2xl">Revision History</h2>
            <p className="mt-2 text-sm text-slate">Latest response and review updates, shown newest first.</p>
          </div>
          {normalizedRevisions.length ? (
            <span className="chip">{normalizedRevisions.length} revision{normalizedRevisions.length === 1 ? "" : "s"}</span>
          ) : null}
        </div>

        <div className="mt-4 max-h-[360px] overflow-y-auto pr-2">
          {renderTimeline(compactRevisions)}
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {normalizedRevisions.length > COMPACT_REVISION_COUNT ? (
            <button type="button" className="button-secondary" onClick={() => setFullHistoryOpen(true)}>
              View Full History
            </button>
          ) : <span />}
          {message ? <p className="text-sm text-sage">{message}</p> : null}
        </div>
      </div>

      {fullHistoryOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6">
          <button
            type="button"
            className="absolute inset-0 bg-ink/50"
            aria-label="Close full revision history"
            onClick={() => setFullHistoryOpen(false)}
          />
          <section className="relative z-10 max-h-[88vh] w-full max-w-3xl overflow-hidden rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="chip">Audit Trail</p>
                <h2 className="mt-3 font-serif text-3xl">Full Revision History</h2>
                <p className="mt-2 text-sm text-slate">All captured revisions are deduplicated and sorted newest first.</p>
              </div>
              <button type="button" className="button-secondary" onClick={() => setFullHistoryOpen(false)}>
                Close
              </button>
            </div>
            <div className="mt-5 max-h-[68vh] overflow-y-auto pr-2">
              {renderTimeline(normalizedRevisions)}
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
