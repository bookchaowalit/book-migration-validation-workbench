import type { Metadata } from "next";
import "../styles.css";

export const metadata: Metadata = {
  title: "Migration Validation Workbench",
  description: "ตรวจข้อมูลหลัง migration ให้เห็นหลักฐานทุกแถว",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="th">
      <body>{children}</body>
    </html>
  );
}
