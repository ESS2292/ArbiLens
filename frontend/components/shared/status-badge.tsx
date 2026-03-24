import { getDocumentStatusTone } from "@/lib/documents";

const toneStyles = {
  neutral: { background: "#eef2f6", color: "#415366" },
  warning: { background: "#fff4db", color: "#8a5b00" },
  success: { background: "#dff3eb", color: "#0b6b57" },
  danger: { background: "#fde8e7", color: "#9b2c2c" },
};

export function StatusBadge({ label }: { label: string }) {
  const tone = getDocumentStatusTone(label);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        borderRadius: "999px",
        padding: "6px 10px",
        fontSize: "12px",
        fontWeight: 700,
        textTransform: "capitalize",
        ...toneStyles[tone],
      }}
    >
      {label.replaceAll("_", " ")}
    </span>
  );
}
