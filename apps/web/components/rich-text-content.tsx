"use client";

import { useEffect, useState } from "react";

import { isEffectivelyEmptyRichText, richTextToPlainText, sanitizeRichText } from "@/lib/rich-text";

type Props = {
  value?: string | null;
  emptyText?: string;
  className?: string;
};

function joinClassNames(...classes: Array<string | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function RichTextContent({ value, emptyText = "No content available.", className }: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!value || isEffectivelyEmptyRichText(value)) {
    return <p className={className}>{emptyText}</p>;
  }

  if (!mounted) {
    return <p className={joinClassNames("whitespace-pre-wrap", className)}>{richTextToPlainText(value)}</p>;
  }

  return (
    <div
      className={joinClassNames("rich-content", className)}
      dangerouslySetInnerHTML={{ __html: sanitizeRichText(value) }}
    />
  );
}
