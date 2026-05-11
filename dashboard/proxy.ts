import { NextRequest, NextResponse } from "next/server";

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

export function proxy(req: NextRequest) {
  const auth = req.headers.get("authorization") ?? "";
  const pwd = process.env.DASHBOARD_PASSWORD;
  if (!pwd) {
    return new NextResponse("DASHBOARD_PASSWORD not set", { status: 500 });
  }
  const expected = "Basic " + Buffer.from(`admin:${pwd}`).toString("base64");
  if (auth !== expected) {
    return new NextResponse("Auth required", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="dashboard"' },
    });
  }
  return NextResponse.next();
}
