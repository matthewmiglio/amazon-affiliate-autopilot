import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background:
            "linear-gradient(135deg, #f7f1ea 0%, #e9c9a9 100%)",
          color: "#3a302c",
          fontFamily: "serif",
          fontSize: 110,
          fontWeight: 500,
          letterSpacing: "-0.04em",
        }}
      >
        S
      </div>
    ),
    size,
  );
}
