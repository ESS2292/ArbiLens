export function ErrorState({
  title = "Something went wrong",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div
      className="panel"
      style={{ padding: "24px", borderColor: "#f2c7c4", background: "#fff8f7" }}
    >
      <h2 style={{ margin: "0 0 8px", fontSize: "18px" }}>{title}</h2>
      <p style={{ margin: 0, color: "#8c4941", lineHeight: 1.6 }}>{message}</p>
    </div>
  );
}
