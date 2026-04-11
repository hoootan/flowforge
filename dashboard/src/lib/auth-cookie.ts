export async function setAuthCookie(token: string, expiresIn: number): Promise<void> {
  const response = await fetch("/api/auth/set-cookie", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, expiresIn }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set auth cookie: ${response.status}`);
  }
}

export async function clearAuthCookie(): Promise<void> {
  const response = await fetch("/api/auth/set-cookie", {
    method: "DELETE",
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(`Failed to clear auth cookie: ${response.status}`);
  }
}
