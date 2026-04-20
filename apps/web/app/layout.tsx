import type { Metadata } from "next";
import { IBM_Plex_Serif, Manrope } from "next/font/google";

import { APP_NAME } from "@/lib/config";
import "./globals.css";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });
const plexSerif = IBM_Plex_Serif({ subsets: ["latin"], variable: "--font-plex-serif", weight: ["400", "500", "600", "700"] });

export const metadata: Metadata = {
  title: APP_NAME,
  description: "HCL internal audit workspace"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${plexSerif.variable}`}>{children}</body>
    </html>
  );
}
