import { useEffect, useState } from "react";

const BACKEND_URL = "http://127.0.0.1:8000";

export default function LogsPanel() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [level, setLevel] = useState("");
  const [source, setSource] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const fetchLogs = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (level) params.append("level", level);
      if (source) params.append("source", source);
      if (dateFrom) params.append("date_from", new Date(dateFrom).toISOString());
      if (dateTo) params.append("date_to", new Date(dateTo).toISOString());

      const res = await fetch(`${BACKEND_URL}/api/logs?${params.toString()}`);
      if (!res.ok) throw new Error("Błąd pobierania logów");
      const data = await res.json();
      setLogs(data);
    } catch (e) {
      console.error(e);
      setError(e.message || "Błąd pobierania logów");
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const exportCsv = () => {
    const params = new URLSearchParams();
    if (level) params.append("level", level);
    if (source) params.append("source", source);
    if (dateFrom) params.append("date_from", new Date(dateFrom).toISOString());
    if (dateTo) params.append("date_to", new Date(dateTo).toISOString());

    const url = `${BACKEND_URL}/api/logs/export?${params.toString()}`;
    window.open(url, "_blank");
  };

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearLogs = async () => {
  setError("");
  try {
    const res = await fetch(`${BACKEND_URL}/api/logs`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Błąd czyszczenia logów");
    await fetchLogs(); // przeładuj tabelę
  } catch (e) {
    console.error(e);
    setError(e.message || "Błąd czyszczenia logów");
  }
};

  return (
    <div>
      <h2 style={{ marginBottom: 8 }}>UC6 — Panel logów systemowych</h2>

      {/* FILTRY */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          marginBottom: 12,
          alignItems: "center",
        }}
      >
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          style={{
            padding: 8,
            borderRadius: 4,
            border: "1px solid #444",
            minWidth: 120,
          }}
        >
          <option value="">Poziom: wszystkie</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>

        <input
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="Źródło (np. UC2, PORTFOLIO)"
          style={{
            padding: 8,
            borderRadius: 4,
            border: "1px solid #444",
            minWidth: 160,
          }}
        />

        <input
          type="datetime-local"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          style={{
            padding: 8,
            borderRadius: 4,
            border: "1px solid #444",
          }}
        />

        <input
          type="datetime-local"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          style={{
            padding: 8,
            borderRadius: 4,
            border: "1px solid #444",
          }}
        />

        <button
          onClick={fetchLogs}
          disabled={loading}
          style={{
            padding: "8px 16px",
            borderRadius: 4,
            border: "none",
            background: "#111",
            color: "white",
            cursor: "pointer",
          }}
        >
          {loading ? "Ładowanie..." : "Pobierz logi"}
        </button>

        <button
          onClick={exportCsv}
          disabled={loading || logs.length === 0}
          style={{
            padding: "8px 16px",
            borderRadius: 4,
            border: "none",
            background: "#111",
            color: "white",
            cursor: "pointer",
          }}
        >
          Eksportuj logi (CSV)
        </button>

        <button
  onClick={clearLogs}
  disabled={loading}
  style={{
    padding: "8px 16px",
    borderRadius: 4,
    border: "none",
    background: "#111",
    color: "white",
    cursor: "pointer",
  }}
>
  Wyczyść logi
</button>
      </div>

      {error && (
        <div style={{ color: "crimson", marginBottom: 8 }}>{error}</div>
      )}

      {logs.length === 0 && !loading ? (
        <div style={{ color: "#aaa", padding: 12 }}>Brak danych logów.</div>
      ) : (
        <div style={{ maxHeight: 400, overflow: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
            }}
          >
            <thead>
              <tr>
                <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                  Czas
                </th>
                <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                  Poziom
                </th>
                <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                  Źródło
                </th>
                <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                  Wiadomość
                </th>
                <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                  Użytkownik
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td
                    style={{
                      borderBottom: "1px solid #333",
                      padding: 6,
                      fontSize: 12,
                    }}
                  >
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td
                    style={{
                      borderBottom: "1px solid #333",
                      padding: 6,
                      fontSize: 12,
                    }}
                  >
                    {log.level}
                  </td>
                  <td
                    style={{
                      borderBottom: "1px solid #333",
                      padding: 6,
                      fontSize: 12,
                    }}
                  >
                    {log.source || "—"}
                  </td>
                  <td
                    style={{
                      borderBottom: "1px solid #333",
                      padding: 6,
                      fontSize: 12,
                    }}
                  >
                    {log.message}
                  </td>
                  <td
                    style={{
                      borderBottom: "1px solid #333",
                      padding: 6,
                      fontSize: 12,
                    }}
                  >
                    {log.user_email || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}