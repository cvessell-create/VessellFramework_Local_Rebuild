import type { Metadata } from "next";
import "./style.css";

export const metadata: Metadata = {
  title: "VessellFramework Control Panel",
  description: "Human evidence review and owner-controlled tasks for a callable specialist"
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
