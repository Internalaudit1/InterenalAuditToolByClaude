"use client";

import type { ClipboardEvent } from "react";
import { useEffect, useRef, useState } from "react";

import { isEffectivelyEmptyRichText, richTextToPlainText, sanitizeRichText } from "@/lib/rich-text";

type Props = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  name?: string;
  minHeightClass?: string;
  className?: string;
};

type ToolbarButton = {
  label: string;
  title: string;
  onClick: () => void;
};

function joinClassNames(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function buildTableHtml(rows: number, columns: number) {
  const safeRows = Math.max(1, Math.min(rows, 6));
  const safeColumns = Math.max(1, Math.min(columns, 6));
  const header = `<tr>${Array.from({ length: safeColumns }, (_, index) => `<th>Header ${index + 1}</th>`).join("")}</tr>`;
  const body = Array.from({ length: safeRows }, () => `<tr>${Array.from({ length: safeColumns }, () => "<td>Cell</td>").join("")}</tr>`).join("");
  return `<table><thead>${header}</thead><tbody>${body}</tbody></table><p><br></p>`;
}

export function RichTextEditor({
  value,
  onChange,
  placeholder = "Write here",
  disabled = false,
  name,
  minHeightClass = "min-h-28",
  className
}: Props) {
  const editorRef = useRef<HTMLDivElement | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || isFocused || !editorRef.current) return;
    const safeValue = sanitizeRichText(value);
    editorRef.current.innerHTML = isEffectivelyEmptyRichText(safeValue) ? "" : safeValue;
  }, [isFocused, mounted, value]);

  function focusEditor() {
    if (disabled) return;
    editorRef.current?.focus();
  }

  function emitCurrentValue() {
    if (!editorRef.current) return;
    const safeValue = sanitizeRichText(editorRef.current.innerHTML);
    onChange(isEffectivelyEmptyRichText(safeValue) ? "" : safeValue);
  }

  function runCommand(command: string, commandValue?: string) {
    if (disabled) return;
    focusEditor();
    document.execCommand(command, false, commandValue);
    emitCurrentValue();
  }

  function insertHtml(html: string) {
    if (disabled) return;
    focusEditor();
    document.execCommand("insertHTML", false, html);
    emitCurrentValue();
  }

  function handlePaste(event: ClipboardEvent<HTMLDivElement>) {
    event.preventDefault();
    if (disabled) return;

    const html = event.clipboardData.getData("text/html");
    const text = event.clipboardData.getData("text/plain");

    if (html) {
      insertHtml(sanitizeRichText(html));
      return;
    }

    const safeText = text
      .split(/\r?\n/)
      .map((line) => line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"))
      .join("<br>");
    insertHtml(safeText);
  }

  if (!mounted) {
    return (
      <>
        {name ? <input type="hidden" name={name} value={value} /> : null}
        <textarea
          className={joinClassNames("field", minHeightClass, className)}
          value={richTextToPlainText(value)}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          disabled={disabled}
        />
      </>
    );
  }

  const toolbarButtons: ToolbarButton[] = [
    { label: "B", title: "Bold", onClick: () => runCommand("bold") },
    { label: "I", title: "Italic", onClick: () => runCommand("italic") },
    { label: "U", title: "Underline", onClick: () => runCommand("underline") },
    { label: "H2", title: "Heading", onClick: () => runCommand("formatBlock", "<h2>") },
    { label: "H3", title: "Subheading", onClick: () => runCommand("formatBlock", "<h3>") },
    { label: "Bullet List", title: "Bulleted list", onClick: () => runCommand("insertUnorderedList") },
    { label: "1. List", title: "Numbered list", onClick: () => runCommand("insertOrderedList") },
    { label: "Quote", title: "Blockquote", onClick: () => runCommand("formatBlock", "<blockquote>") },
    {
      label: "Link",
      title: "Insert link",
      onClick: () => {
        const url = window.prompt("Enter link URL");
        if (url) {
          runCommand("createLink", url);
        }
      }
    },
    {
      label: "Table",
      title: "Insert table",
      onClick: () => {
        const rows = Number(window.prompt("Number of rows", "2") ?? "2");
        const columns = Number(window.prompt("Number of columns", "2") ?? "2");
        insertHtml(buildTableHtml(rows, columns));
      }
    },
    { label: "Rule", title: "Insert divider", onClick: () => runCommand("insertHorizontalRule") },
    {
      label: "Clear",
      title: "Clear formatting",
      onClick: () => {
        runCommand("removeFormat");
        runCommand("formatBlock", "<p>");
      }
    }
  ];

  return (
    <div className="rich-editor">
      {name ? <input type="hidden" name={name} value={value} /> : null}
      {!disabled ? (
        <div className="rich-editor__toolbar" role="toolbar" aria-label="Rich text formatting toolbar">
          {toolbarButtons.map((button) => (
            <button
              key={button.title}
              type="button"
              className="rich-editor__toolbar-button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={button.onClick}
              title={button.title}
            >
              {button.label}
            </button>
          ))}
        </div>
      ) : null}
      <div
        ref={editorRef}
        className={joinClassNames(
          "rich-editor__surface",
          "field",
          minHeightClass,
          disabled && "rich-editor__surface--disabled",
          className
        )}
        contentEditable={!disabled}
        suppressContentEditableWarning
        data-placeholder={placeholder}
        onFocus={() => setIsFocused(true)}
        onBlur={() => {
          setIsFocused(false);
          if (!editorRef.current) return;
          const safeValue = sanitizeRichText(editorRef.current.innerHTML);
          editorRef.current.innerHTML = isEffectivelyEmptyRichText(safeValue) ? "" : safeValue;
          onChange(isEffectivelyEmptyRichText(safeValue) ? "" : safeValue);
        }}
        onInput={() => emitCurrentValue()}
        onPaste={handlePaste}
      />
    </div>
  );
}
