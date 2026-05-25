"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/dashboard",    label: "Dashboard"    },
  { href: "/applications", label: "Applications" },
  { href: "/profile",      label: "Profile"      },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center justify-between px-8 py-4 border-b border-slate-800 sticky top-0 z-10 bg-slate-950/80 backdrop-blur-sm">
      <Link href="/dashboard" className="text-xl font-bold text-brand-500 hover:text-brand-400 transition-colors">
        NeonGrad
      </Link>
      <div className="flex gap-6 text-sm text-slate-400">
        {NAV_LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`transition-colors hover:text-slate-100 ${
              pathname === href ? "text-slate-100 font-medium" : ""
            }`}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
