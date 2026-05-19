import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeonGrad — AI Job Hunting OS",
  description:
    "NeonGrad finds the right jobs for you, ranks them by AI-assessed fit, and tailors your application in 60 seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
