import type { Metadata, Viewport } from "next";

import { ToastProvider } from "@/components/ui/toast";

import { APP_NAME, APP_TAGLINE } from "@aitzaz/shared";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: `${APP_NAME} — ${APP_TAGLINE}`,
    template: `%s · ${APP_NAME}`,
  },
  description:
    "Aitzaz AI — a personal AI agent with tools, memory, tasks, approvals and a full audit trail. Phase 1 foundation.",
};

export const viewport: Viewport = {
  themeColor: "#07090f",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script
          // Apply the saved theme before first paint to avoid flashing.
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var s=localStorage.getItem("aitzaz.theme");if(s==="light"){document.documentElement.classList.remove("dark");document.documentElement.classList.add("light");}}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
