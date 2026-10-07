import type { Metadata } from "next";
import "./style.css";

export const metadata: Metadata = {
  title: "Vessell Ambient Review",
  description: "Local analysis-only event review and durable approval history"
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
