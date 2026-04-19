import { ImageResponse } from "next/og";

export const alt = "FlowForge Dashboard — monitor and manage your AI workflows";
export const size = { width: 2400, height: 1260 };
export const contentType = "image/png";

async function loadGoogleFont(family: string, weight: number, style: "normal" | "italic" = "normal") {
  const familyParam = family.replace(/ /g, "+");
  const css = await fetch(
    `https://fonts.googleapis.com/css2?family=${familyParam}:ital,wght@${style === "italic" ? 1 : 0},${weight}&display=swap`,
    { headers: { "User-Agent": "Mozilla/5.0" } }
  ).then((r) => r.text());
  const url = css.match(/src: url\((https:[^)]+)\) format/)?.[1];
  if (!url) throw new Error(`font not found: ${family} ${weight} ${style}`);
  return fetch(url).then((r) => r.arrayBuffer());
}

export default async function OpengraphImage() {
  const [interTight, instrumentSerif, jetbrainsMono] = await Promise.all([
    loadGoogleFont("Inter Tight", 800),
    loadGoogleFont("Instrument Serif", 400, "italic"),
    loadGoogleFont("JetBrains Mono", 500),
  ]);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "112px 144px",
          background: "#F2EEE5",
          color: "#0B0C0F",
          fontFamily: "Inter Tight",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "linear-gradient(to right, rgba(11,12,15,0.1) 2px, transparent 2px), linear-gradient(to bottom, rgba(11,12,15,0.1) 2px, transparent 2px)",
            backgroundSize: "176px 176px",
            opacity: 0.8,
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 24, zIndex: 1 }}>
          <svg width="68" height="68" viewBox="0 0 24 24">
            <path
              d="M 3 3 L 21 3 L 21 7 L 13 7 L 13 11 L 19 11 L 19 15 L 13 15 L 13 21 L 9 21 L 9 7 L 3 7 Z"
              fill="#0B0C0F"
            />
          </svg>
          <div style={{ fontSize: 52, fontWeight: 800, letterSpacing: -1 }}>FlowForge</div>
          <div
            style={{
              fontSize: 24,
              fontFamily: "JetBrains Mono",
              padding: "6px 16px",
              border: "2px solid rgba(11,12,15,0.22)",
              borderRadius: 6,
              color: "#5A5E68",
              letterSpacing: 2,
              marginLeft: 8,
            }}
          >
            dashboard
          </div>
          <div
            style={{
              marginLeft: "auto",
              display: "flex",
              alignItems: "center",
              gap: 20,
              fontFamily: "JetBrains Mono",
              fontSize: 24,
              color: "#5A5E68",
              letterSpacing: 4,
            }}
          >
            <div style={{ width: 14, height: 14, borderRadius: 999, background: "#2B7A4B" }} />
            §02 · OBSERVABILITY
          </div>
        </div>

        <div
          style={{
            fontWeight: 800,
            fontSize: 176,
            lineHeight: 0.98,
            letterSpacing: -6.4,
            display: "flex",
            flexDirection: "column",
            zIndex: 1,
          }}
        >
          <div style={{ display: "flex" }}>Every run.</div>
          <div
            style={{
              display: "flex",
              fontFamily: "Instrument Serif",
              fontStyle: "italic",
              fontWeight: 400,
              letterSpacing: -2.4,
            }}
          >
            Every step.
          </div>
          <div style={{ display: "flex", alignItems: "center" }}>
            In{" "}
            <span style={{ position: "relative", display: "flex", marginLeft: 36 }}>
              real time.
              <span
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  bottom: 14,
                  height: 14,
                  background: "#2B7A4B",
                }}
              />
            </span>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            zIndex: 1,
            fontSize: 32,
            color: "#5A5E68",
          }}
        >
          <div style={{ display: "flex" }}>Monitor &amp; manage your durable AI workflows</div>
          <div
            style={{
              display: "flex",
              fontFamily: "JetBrains Mono",
              fontSize: 28,
              padding: "20px 32px",
              background: "#0B0C0F",
              color: "#F2EEE5",
              borderRadius: 8,
              letterSpacing: 1,
            }}
          >
            LIVE · SSE
          </div>
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Inter Tight", data: interTight, weight: 800, style: "normal" },
        { name: "Instrument Serif", data: instrumentSerif, weight: 400, style: "italic" },
        { name: "JetBrains Mono", data: jetbrainsMono, weight: 500, style: "normal" },
      ],
    }
  );
}
