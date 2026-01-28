import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login | FlowForge",
  description: "Sign in to FlowForge Dashboard",
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
