export async function setAuthCookie(token: string, expiresIn: number): Promise<void> {
  await fetch("/api/auth/set-cookie", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, expiresIn }),
  });
}

export async function clearAuthCookie(): Promise<void> {
  await fetch("/api/auth/set-cookie", { method: "DELETE" });
}
