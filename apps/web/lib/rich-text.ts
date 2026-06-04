const HTML_PATTERN = /<\/?[a-z][\s\S]*>/i;

const ALLOWED_TAGS = new Set([
  "a",
  "blockquote",
  "br",
  "div",
  "em",
  "h2",
  "h3",
  "h4",
  "hr",
  "li",
  "ol",
  "p",
  "strong",
  "table",
  "tbody",
  "td",
  "th",
  "thead",
  "tr",
  "u",
  "ul"
]);

function hasDomSupport() {
  return typeof window !== "undefined" && typeof DOMParser !== "undefined" && typeof document !== "undefined";
}

function decodeBasicEntities(value: string) {
  return value
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, "\"")
    .replace(/&#39;/gi, "'");
}

function normalizeTagName(tagName: string) {
  if (tagName === "b") return "strong";
  if (tagName === "i") return "em";
  return tagName;
}

function sanitizeUrl(value: string) {
  if (!value) return "";
  if (value.startsWith("#")) return value;

  try {
    const parsed = new URL(value, "https://placeholder.local");
    if (parsed.protocol === "http:" || parsed.protocol === "https:" || parsed.protocol === "mailto:") {
      return value;
    }
  } catch {
    return "";
  }

  return "";
}

function sanitizeNode(node: Node, targetDocument: Document): Node | null {
  if (node.nodeType === Node.TEXT_NODE) {
    return targetDocument.createTextNode(node.textContent ?? "");
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  const element = node as HTMLElement;
  const tagName = normalizeTagName(element.tagName.toLowerCase());

  if (!ALLOWED_TAGS.has(tagName)) {
    const fragment = targetDocument.createDocumentFragment();
    Array.from(element.childNodes).forEach((childNode) => {
      const sanitizedChild = sanitizeNode(childNode, targetDocument);
      if (sanitizedChild) {
        fragment.appendChild(sanitizedChild);
      }
    });
    return fragment;
  }

  const safeElement = targetDocument.createElement(tagName);

  if (tagName === "a") {
    const href = sanitizeUrl(element.getAttribute("href") ?? "");
    if (href) {
      safeElement.setAttribute("href", href);
      safeElement.setAttribute("target", "_blank");
      safeElement.setAttribute("rel", "noreferrer noopener");
    }
  }

  if (tagName === "td" || tagName === "th") {
    const colspan = Number(element.getAttribute("colspan"));
    if (Number.isFinite(colspan) && colspan > 1 && colspan <= 12) {
      safeElement.setAttribute("colspan", String(colspan));
    }

    const rowspan = Number(element.getAttribute("rowspan"));
    if (Number.isFinite(rowspan) && rowspan > 1 && rowspan <= 12) {
      safeElement.setAttribute("rowspan", String(rowspan));
    }
  }

  Array.from(element.childNodes).forEach((childNode) => {
    const sanitizedChild = sanitizeNode(childNode, targetDocument);
    if (sanitizedChild) {
      safeElement.appendChild(sanitizedChild);
    }
  });

  return safeElement;
}

export function looksLikeRichText(value: string | null | undefined) {
  return Boolean(value && HTML_PATTERN.test(value));
}

export function richTextToPlainText(value: string | null | undefined) {
  if (!value) return "";

  const withSpacing = value
    .replace(/<\s*br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|li|tr|h[1-6]|blockquote)>/gi, "\n")
    .replace(/<(td|th)[^>]*>/gi, " ")
    .replace(/<\/(td|th)>/gi, " ")
    .replace(/<[^>]+>/g, " ");

  return decodeBasicEntities(withSpacing)
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function isEffectivelyEmptyRichText(value: string | null | undefined) {
  return richTextToPlainText(value).replace(/\s+/g, "").length === 0;
}

export function sanitizeRichText(value: string | null | undefined) {
  if (!value) return "";
  if (!hasDomSupport()) return value;

  const parser = new DOMParser();
  const parsedDocument = parser.parseFromString(`<div>${value}</div>`, "text/html");
  const sourceRoot = parsedDocument.body.firstElementChild ?? parsedDocument.body;
  const targetDocument = document.implementation.createHTMLDocument("sanitized-rich-text");
  const container = targetDocument.createElement("div");

  Array.from(sourceRoot.childNodes).forEach((childNode) => {
    const sanitizedChild = sanitizeNode(childNode, targetDocument);
    if (sanitizedChild) {
      container.appendChild(sanitizedChild);
    }
  });

  return container.innerHTML.trim();
}
