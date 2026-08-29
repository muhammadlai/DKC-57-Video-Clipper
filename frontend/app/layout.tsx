import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "AITZAZ AI — Live Content Command Center",
  description:
    "AITZAZ AI combines YouTube Live, STUMPS cricket context, backend AI, FFmpeg clip processing, and a publishing queue for short-form sports content.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body>
        <div className="relative flex min-h-screen flex-col bg-black">
          <Suspense>
            <Navbar />
          </Suspense>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-white/5 py-5 text-center text-[11px] text-slate-600">
            AITZAZ AI — Live Content Command Center. Real backend diagnostics only.
          </footer>
        </div>
      </body>
    </html>
  );
}
