import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DevPilot — Autonomous Software Engineering Workspace",
  description: "Controlled multi-agent software engineering platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-gray-100 antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}

