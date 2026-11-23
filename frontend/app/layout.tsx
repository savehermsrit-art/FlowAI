import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = {
  title: "FormFlow AI | A little guidance. A clearer next step.",
  description:
    "Private, local and evidence-aware welfare discovery for senior citizens. Karnataka. English and Kannada.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
