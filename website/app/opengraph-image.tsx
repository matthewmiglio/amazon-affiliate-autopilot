import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "The Luxe Drawer — Daily Amazon luxury finds for women";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          background:
            "linear-gradient(135deg, #f7f1ea 0%, #f3e3d3 55%, #e9c9a9 100%)",
          color: "#3a302c",
          fontFamily: "serif",
          padding: "80px",
        }}
      >
        <div
          style={{
            fontSize: 28,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            color: "#a87a3d",
            marginBottom: 32,
          }}
        >
          Curated Daily · Amazon Associate
        </div>
        <div
          style={{
            fontSize: 132,
            lineHeight: 1,
            textAlign: "center",
            fontWeight: 500,
          }}
        >
          The Luxe Drawer
        </div>
        <div
          style={{
            marginTop: 40,
            fontSize: 38,
            color: "#6b5f58",
            textAlign: "center",
            maxWidth: 900,
            fontFamily: "sans-serif",
          }}
        >
          Daily Amazon luxury finds for women — the look without the markup.
        </div>
      </div>
    ),
    size,
  );
}
