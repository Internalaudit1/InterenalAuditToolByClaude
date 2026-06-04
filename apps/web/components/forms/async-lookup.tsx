"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";
import { normalizeItems } from "@/lib/meta";

export type LookupOption = {
  value: number | string;
  label: string;
  description?: string | null;
};

type Props = {
  value: number | string | null | undefined;
  selectedLabel?: string | null;
  onSelect: (option: LookupOption | null) => void;
  endpoint: string;
  queryParam?: string;
  placeholder?: string;
  minChars?: number;
  disabled?: boolean;
  staticParams?: Record<string, string | number | boolean | null | undefined>;
  mapOption: (row: Record<string, unknown>) => LookupOption | null;
};

function buildLookupUrl(
  endpoint: string,
  queryParam: string,
  query: string,
  staticParams?: Record<string, string | number | boolean | null | undefined>
) {
  const joiner = endpoint.includes("?") ? "&" : "?";
  const params = new URLSearchParams();
  params.set(queryParam, query);
  params.set("page_size", "20");
  Object.entries(staticParams ?? {}).forEach(([key, rawValue]) => {
    if (rawValue === null || rawValue === undefined || rawValue === "") return;
    params.set(key, String(rawValue));
  });
  return `${endpoint}${joiner}${params.toString()}`;
}

export function AsyncLookupField({
  value,
  selectedLabel,
  onSelect,
  endpoint,
  queryParam = "q",
  placeholder,
  minChars = 3,
  disabled = false,
  staticParams,
  mapOption
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapOptionRef = useRef(mapOption);
  const suppressSyncRef = useRef(false);
  const [query, setQuery] = useState(selectedLabel ?? "");
  const [results, setResults] = useState<LookupOption[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const effectivePlaceholder = placeholder ?? `Type at least ${minChars} characters`;
  const paramsSignature = JSON.stringify(staticParams ?? {});

  useEffect(() => {
    mapOptionRef.current = mapOption;
  }, [mapOption]);

  useEffect(() => {
    if (suppressSyncRef.current) {
      suppressSyncRef.current = false;
      return;
    }
    setQuery(selectedLabel ?? "");
  }, [selectedLabel, value]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (disabled) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    const trimmed = query.trim();
    if (trimmed.length < minChars) {
      setResults([]);
      return;
    }
    let active = true;
    setLoading(true);
    apiFetch<unknown>(buildLookupUrl(endpoint, queryParam, trimmed, staticParams))
      .then((payload) => {
        if (!active) return;
        const options = normalizeItems(payload)
          .map((row) => mapOptionRef.current(row))
          .filter((option): option is LookupOption => Boolean(option));
        setResults(options);
        setIsOpen(true);
      })
      .catch(() => {
        if (!active) return;
        setResults([]);
        setIsOpen(false);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [disabled, endpoint, minChars, paramsSignature, query, queryParam]);

  const helperText = useMemo(() => {
    if (disabled) return "";
    if (query.trim().length === 0) return `Type ${minChars}+ letters to search`;
    if (query.trim().length < minChars) return `Keep typing to reach ${minChars} characters`;
    if (loading) return "Searching...";
    if (!results.length) return "No matches found";
    return `${results.length} suggestion${results.length === 1 ? "" : "s"} found`;
  }, [disabled, loading, minChars, query, results.length]);

  return (
    <div className="relative" ref={containerRef}>
      <input
        className="field"
        value={query}
        disabled={disabled}
        placeholder={effectivePlaceholder}
        onFocus={() => {
          if (results.length) setIsOpen(true);
        }}
        onChange={(event) => {
          const nextQuery = event.target.value;
          setQuery(nextQuery);
          if (value !== null && value !== undefined && nextQuery !== selectedLabel) {
            suppressSyncRef.current = true;
            onSelect(null);
          }
        }}
      />
      <p className="mt-1 text-xs text-slate">{helperText}</p>
      {isOpen && results.length ? (
        <div className="absolute z-20 mt-2 max-h-64 w-full overflow-y-auto rounded-2xl border border-sand bg-white shadow-soft">
          {results.map((option) => (
            <button
              key={String(option.value)}
              type="button"
              className="flex w-full flex-col gap-1 border-b border-sand/50 px-4 py-3 text-left last:border-b-0 hover:bg-cream"
              onClick={() => {
                onSelect(option);
                setQuery(option.label);
                setResults([]);
                setIsOpen(false);
              }}
            >
              <span className="text-sm font-semibold text-ink">{option.label}</span>
              {option.description ? <span className="text-xs text-slate">{option.description}</span> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
