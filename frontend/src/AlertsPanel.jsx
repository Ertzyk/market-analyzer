import { useEffect, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

const OPERATORS = [">", "<"]; // backend obsługuje tylko above/below

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [symbol, setSymbol] = useState("");
  const [operator, setOperator] = useState(">");
  const [targetPrice, setTargetPrice] = useState("");
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [triggeredAlerts, setTriggeredAlerts] = useState([]);

  // ---- helpers --------------------------------------------------------------

  async function fetchAlerts() {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE_URL}/api/alerts`);
      if (!res.ok) throw new Error("Błąd pobierania listy alertów");
      const data = await res.json();
      setAlerts(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAlerts();
  }, []);

  // ---- handlers -------------------------------------------------------------

  async function handleAddAlert(e) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    const price = parseFloat(targetPrice.replace(",", "."));
    if (Number.isNaN(price)) {
      setError("Podaj poprawną wartość ceny.");
      return;
    }

    // mapowanie operatorów -> backend
    const condition = operator === ">" ? "above" : "below";

    try {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/api/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol.trim().toUpperCase(),
          condition,
          threshold_price: price,
        }),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Błąd zapisu alertu: ${txt || res.status}`);
      }

      setTargetPrice("");
      setMessage("Alert zapisany.");
      await fetchAlerts();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteAlert(id) {
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/alerts/${id}`, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) {
        throw new Error("Nie udało się usunąć alertu");
      }
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      setMessage("Alert usunięty.");
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleCheckAlerts() {
    setChecking(true);
    setError(null);
    setMessage(null);
    setTriggeredAlerts([]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/alerts/check`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Błąd sprawdzania alertów");
      const data = await res.json();

      const triggered = data.triggered || [];

      if (triggered.length === 0) {
        setMessage("Brak nowych wyzwolonych alertów.");
      } else {
        setTriggeredAlerts(triggered);
        setMessage(`Wyzwolono ${triggered.length} alert(y).`);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setChecking(false);
    }
  }

  // ---- render ---------------------------------------------------------------

  return (
    <div className="alerts-panel" style={{ maxWidth: 800, margin: "0 auto" }}>
      <h2>Alerty cenowe (UC4)</h2>

      <form className="alerts-form" onSubmit={handleAddAlert}>
        <div className="row" style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          <label>
            Symbol<br />
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="np. AAPL"
            />
          </label>

          <label>
            Warunek<br />
            <select
              value={operator}
              onChange={(e) => setOperator(e.target.value)}
            >
              {OPERATORS.map((op) => (
                <option key={op} value={op}>
                  Cena {op}
                </option>
              ))}
            </select>
          </label>

          <label>
            Cena docelowa<br />
            <input
              type="number"
              step="0.01"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
            />
          </label>

          <button type="submit" disabled={loading} style={{ height: 38 }}>
            {loading ? "Dodawanie..." : "Dodaj alert"}
          </button>
        </div>
      </form>

      <button
        onClick={handleCheckAlerts}
        disabled={checking}
        style={{ marginBottom: 16 }}
      >
        {checking ? "Sprawdzanie..." : "Sprawdź alerty teraz"}
      </button>

      {message && <p style={{ color: "lightgreen" }}>{message}</p>}
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h3>Aktywne alerty</h3>
      {alerts.length === 0 ? (
        <p>Brak alertów.</p>
      ) : (
        <table className="alerts-table" style={{ width: "100%", marginTop: 8 }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Symbol</th>
              <th>Warunek</th>
              <th>Aktywny</th>
              <th>Ostatnio wyzwolony</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id}>
                <td>{a.id}</td>
                <td>{a.symbol}</td>
                <td>
                  {a.condition === "above" ? ">" : "<"} {a.threshold_price}
                </td>
                <td>{a.active ? "tak" : "nie"}</td>
                <td>
                  {a.last_triggered_at
                    ? new Date(a.last_triggered_at).toLocaleString()
                    : "—"}
                </td>
                <td>
                  <button onClick={() => handleDeleteAlert(a.id)}>Usuń</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {triggeredAlerts.length > 0 && (
        <>
          <h3>Ostatnio wyzwolone alerty</h3>
          <ul>
            {triggeredAlerts.map((t, idx) => (
              <li key={idx}>
                {t.symbol} —{" "}
                {t.condition === "above" ? ">" : "<"} {t.threshold_price}{" "}
                (cena: {t.current_price ?? "?"})
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}