import { cookies } from "next/headers";
import { NextResponse } from "next/server";

function isSameOrigin(req: Request): boolean {
  const origin = req.headers.get("origin");
  const requestOrigin = new URL(req.url).origin;
  if (origin) return origin === requestOrigin;
  const referer = req.headers.get("referer");
  if (referer) return new URL(referer).origin === requestOrigin;
  // No Origin or Referer — same-origin requests may omit both
  return true;
}

export async function POST(req: Request) {
  if (!isSameOrigin(req)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }
  const { token, expiresIn } = await req.json();
  const cookieStore = await cookies();
  cookieStore.set("flowforge-auth-token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: expiresIn,
  });
  return NextResponse.json({ ok: true });
}

export async function DELETE(req: Request) {
  if (!isSameOrigin(req)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }
  const cookieStore = await cookies();
  cookieStore.delete({ name: "flowforge-auth-token", path: "/" });
  return NextResponse.json({ ok: true });
}
