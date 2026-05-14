import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
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
          fontSize: 22,
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
