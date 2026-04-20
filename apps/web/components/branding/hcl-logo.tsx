"use client";

import { cn } from "@/lib/utils";

type HclLogoProps = {
  className?: string;
  labelClassName?: string;
  subtitle?: string;
};

export function HclLogo({ className, labelClassName, subtitle }: HclLogoProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <svg
        viewBox="0 0 360 96"
        role="img"
        aria-label="HCL"
        className="h-auto w-full max-w-[240px]"
      >
        <g transform="translate(8 10) skewX(-16)">
          <text
            x="0"
            y="58"
            fill="#0b6fbc"
            fontFamily="Arial Black, Arial, Helvetica, sans-serif"
            fontSize="72"
            fontWeight="900"
            letterSpacing="2"
          >
            HCL
          </text>
        </g>
      </svg>
      {subtitle ? (
        <p className={cn("text-xs uppercase tracking-[0.22em] text-slate", labelClassName)}>
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}
