import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "DKC 57 Video Clipper — AI-Powered Shorts Generator",
  description:
    "DKC 57 Video Clipper: local-first, AI-powered video clipping. Upload a long video, let AI find the best moments, and export 9:16 shorts with captions. Built on OpenClip (MIT) by AIONIX.",
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
            DKC 57 Video Clipper — AI-Powered Shorts Generator. Built on{" "}
            <a
              href="https://github.com/aionixOS/Openclip"
              target="_blank"
              rel="noreferrer"
              className="text-slate-500 underline decoration-white/10 hover:text-red-400"
            >
              OpenClip
            </a>{" "}
            (MIT) by AIONIX.
          </footer>
        </div>
      </body>
    </html>
  );
}
