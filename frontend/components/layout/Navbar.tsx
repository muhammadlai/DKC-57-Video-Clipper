"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { DkcLogo } from "./DkcLogo";

export function Navbar() {
  const pathname = usePathname();

  const nav = [
    { href: "/", label: "Command Center" },
    { href: "/library", label: "Clip Library" },
    { href: "/admin", label: "Admin" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-black/80 px-6 py-4 backdrop-blur-xl lg:px-14">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl">
            <DkcLogo size={40} />
          </div>
          <span className="flex flex-col leading-none">
            <span className="text-xl font-black tracking-tight text-white">
              AITZAZ <span className="text-primary">AI</span>
            </span>
            <span className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
              Live Content Command Center
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-5">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`text-sm font-semibold transition-colors ${pathname === item.href ? "text-white" : "text-slate-400 hover:text-white"}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
