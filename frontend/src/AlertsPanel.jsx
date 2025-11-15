// src/AlertsPanel.jsx
import { useEffect, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

const OPERATORS = [">", ">=", "<", "<="];

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [symbol, setSymbol] = useState("AAPL");
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

    try {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/api/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol.trim().toUpperCase(),
          operator,
          target_price: price, // jeśli w backendzie nazwa jest inna, zmień klucz
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

      // obsłuż 2 możliwe formaty: [] albo {triggered: []}
      const triggered = Array.isArray(data)
        ? data
        : Array.isArray(data.triggered)
        ? data.triggered
        : [];

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
    <div className="alerts-panel">
      <h2>UC4 — Zarządzanie alertami cenowymi</h2>

      <form className="alerts-form" onSubmit={handleAddAlert}>
        <div className="row">
          <label>
            Symbol
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
            />
          </label>

          <label>
            Warunek
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
            Cena docelowa
            <input
              type="number"
              step="0.01"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
            />
          </label>

          <button type="submit" disabled={loading}>
            Dodaj alert
          </button>
        </div>
      </form>

      <div className="alerts-actions">
        <button onClick={handleCheckAlerts} disabled={checking}>
          {checking ? "Sprawdzanie..." : "Sprawdź alerty teraz"}
        </button>
      </div>

      {message && <p className="info-msg">{message}</p>}
      {error && <p className="error-msg">{error}</p>}

      <h3>Aktywne alerty</h3>
      {loading && alerts.length === 0 ? (
        <p>Ładowanie…</p>
      ) : alerts.length === 0 ? (
        <p>Brak zapisanych alertów.</p>
      ) : (
        <table className="alerts-table">
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
                  {a.operator} {a.target_price ?? a.threshold_price}
                </td>
                <td>{a.active ? "tak" : "nie"}</td>
                <td>
                  {a.last_triggered_at
                    ? new Date(a.last_triggered_at).toLocaleString()
                    : "–"}
                </td>
                <td>
                  <button onClick={() => handleDeleteAlert(a.id)}>
                    Usuń
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {triggeredAlerts.length > 0 && (
        <>
          <h3>Ostatnio wyzwolone alerty</h3>
          <ul className="triggered-list">
            {triggeredAlerts.map((t, idx) => (
              <li key={t.id ?? idx}>
                {t.symbol} – {t.operator} {t.target_price ?? t.threshold_price}{" "}
                (aktualna cena: {t.current_price ?? t.price ?? "?"})
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
