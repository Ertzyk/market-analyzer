import { useEffect, useState } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";
import "chartjs-adapter-date-fns";
import {
  Chart as ChartJS,
  TimeScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import AlertsPanel from "./AlertsPanel.jsx";

ChartJS.register(TimeScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

// prosta SMA
function sma(values, windowSize = 20) {
  const out = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v == null || Number.isNaN(v)) {
      out[i] = null;
      continue;
    }
    sum += v;
    if (i >= windowSize) {
      sum -= values[i - windowSize];
    }
    if (i >= windowSize - 1) {
      out[i] = +(sum / windowSize).toFixed(4);
    }
  }
  return out;
}

const BACKEND_URL = "http://127.0.0.1:8000";

export default function App() {
  const [view, setView] = useState("single"); // single | compare | portfolio

  // --- SINGLE INSTRUMENT (UC1–UC3) ---
  const [symbol, setSymbol] = useState("AAPL");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-01-31");
  const [points, setPoints] = useState([]);
  const [lastQuote, setLastQuote] = useState(null);
  const [singleLoading, setSingleLoading] = useState(false);
  const [singleErr, setSingleErr] = useState("");

  // --- COMPARE ---
  const [cmpSymbols, setCmpSymbols] = useState("AAPL,MSFT,TSLA");
  const [cmpStart, setCmpStart] = useState("2024-01-01");
  const [cmpEnd, setCmpEnd] = useState("2024-03-31");
  const [cmpData, setCmpData] = useState(null); // pełna odpowiedź z API
  const [cmpLoading, setCmpLoading] = useState(false);
  const [cmpErr, setCmpErr] = useState("");

  // --- PORTFOLIO ---
  const [portfolio, setPortfolio] = useState(null);
  const [pfSymbol, setPfSymbol] = useState("AAPL");
  const [pfQty, setPfQty] = useState("10");
  const [pfPrice, setPfPrice] = useState("180");
  const [pfLoading, setPfLoading] = useState(false);
  const [pfErr, setPfErr] = useState("");

  // --------- SINGLE: BACKEND CALLS ---------

  const loadHistory = async () => {
    try {
      setSingleErr("");
      setSingleLoading(true);
      const url = `${BACKEND_URL}/api/history`;
      const res = await axios.get(url, {
        params: {
          symbol,
          start: startDate,
          end: endDate,
        },
      });
      setPoints(res.data.quotes || []);
    } catch (e) {
      console.error(e);
      setSingleErr("Błąd pobierania historii (sprawdź backend / symbol / daty).");
      setPoints([]);
    } finally {
      setSingleLoading(false);
    }
  };

  const loadCurrent = async () => {
    try {
      setSingleErr("");
      setSingleLoading(true);
      const res = await axios.get(`${BACKEND_URL}/api/current`, {
        params: { symbol },
      });
      setLastQuote(res.data.quote);
    } catch (e) {
      console.error(e);
      setSingleErr("Błąd pobierania bieżących danych.");
      setLastQuote(null);
    } finally {
      setSingleLoading(false);
    }
  };

  const downloadCsv = () => {
    const url = `${BACKEND_URL}/api/export/csv?symbol=${encodeURIComponent(
      symbol
    )}&start=${startDate}&end=${endDate}`;
    window.open(url, "_blank");
  };

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // SINGLE: dane do wykresu
  const closes = points.map((p) => Number(p.close));
  const sma20 = sma(closes, 20);

  const closeSeries = points.map((p) => ({
    x: p.date,
    y: Number(p.close),
  }));

  const smaSeries = points
    .map((p, i) => ({
      x: p.date,
      y: sma20[i],
    }))
    .filter((p) => p.y != null);

  const singleChartData = {
    datasets: [
      {
        label: `${symbol} — Close`,
        data: closeSeries,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.1,
        borderColor: "#4cc9f0",
      },
      {
        label: "SMA(20)",
        data: smaSeries,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.1,
        borderColor: "#f72585",
      },
    ],
  };

  const timeChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: "time",
        time: { unit: "day" },
        ticks: { maxRotation: 0, autoSkip: true },
      },
      y: {
        beginAtZero: false,
      },
    },
    plugins: {
      legend: { position: "bottom" },
      tooltip: { mode: "index", intersect: false },
    },
  };

  // --------- COMPARE: BACKEND CALLS & DATA ---------

  const loadCompare = async () => {
    try {
      setCmpErr("");
      setCmpLoading(true);
      const res = await axios.get(`${BACKEND_URL}/api/compare`, {
        params: {
          symbols: cmpSymbols,
          start: cmpStart,
          end: cmpEnd,
        },
      });
      setCmpData(res.data);
    } catch (e) {
      console.error(e);
      if (e.response?.data?.detail) {
        setCmpErr(`Błąd porównania: ${e.response.data.detail}`);
      } else {
        setCmpErr("Błąd porównania instrumentów.");
      }
      setCmpData(null);
    } finally {
      setCmpLoading(false);
    }
  };

  const compareChartData = (() => {
    if (!cmpData) return { datasets: [] };

    const palette = [
      "#4cc9f0",
      "#f72585",
      "#f77f00",
      "#2a9d8f",
      "#e9c46a",
      "#9b5de5",
    ];

    const datasets = cmpData.symbols.map((sym, index) => {
      const series = cmpData.series[sym] || [];
      return {
        label: `${sym} — znormalizowane (100 = start)`,
        data: series.map((p) => ({
          x: p.date,
          y: p.normalized,
        })),
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.1,
        borderColor: palette[index % palette.length],
      };
    });

    return { datasets };
  })();

  // --------- PORTFOLIO: BACKEND CALLS ---------

  const loadPortfolio = async () => {
    try {
      setPfErr("");
      setPfLoading(true);
      const res = await axios.get(`${BACKEND_URL}/api/portfolio`);
      setPortfolio(res.data);
    } catch (e) {
      console.error(e);
      setPfErr("Błąd pobierania portfela.");
      setPortfolio(null);
    } finally {
      setPfLoading(false);
    }
  };

  const submitPosition = async (e) => {
    e.preventDefault();
    const qty = parseFloat(pfQty);
    const price = parseFloat(pfPrice);
    if (Number.isNaN(qty) || Number.isNaN(price)) {
      setPfErr("Podaj poprawne wartości liczbowo.");
      return;
    }

    try {
      setPfErr("");
      setPfLoading(true);
      const res = await axios.post(`${BACKEND_URL}/api/portfolio/positions`, {
        symbol: pfSymbol.toUpperCase(),
        quantity: qty,
        avg_open_price: price,
      });
      setPortfolio(res.data);
    } catch (e2) {
      console.error(e2);
      if (e2.response?.data?.detail) {
        setPfErr(`Błąd zapisu pozycji: ${e2.response.data.detail}`);
      } else {
        setPfErr("Błąd zapisu pozycji w portfelu.");
      }
    } finally {
      setPfLoading(false);
    }
  };

  // automatyczne pierwsze pobranie portfela przy wejściu na zakładkę
  useEffect(() => {
    if (view === "portfolio" && !portfolio) {
      loadPortfolio();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  // --------- RENDER ---------

  return (
    <div
      style={{
        maxWidth: 1200,
        margin: "24px auto",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        color: "white",
      }}
    >
      <h1 style={{ marginBottom: 8 }}>
        System analizy danych rynkowych — prototyp UI
      </h1>

      {/* NAV */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => setView("single")}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "none",
            cursor: "pointer",
            background: view === "single" ? "#1f2937" : "#111",
            color: "white",
          }}
        >
          UC1–UC3: pojedynczy instrument
        </button>
        <button
          onClick={() => setView("compare")}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "none",
            cursor: "pointer",
            background: view === "compare" ? "#1f2937" : "#111",
            color: "white",
          }}
        >
          Porównanie instrumentów
        </button>
        <button
          onClick={() => setView("portfolio")}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "none",
            cursor: "pointer",
            background: view === "portfolio" ? "#1f2937" : "#111",
            color: "white",
          }}
        >
          Portfel (demo)
        </button>
      </div>

      {view === "single" && (
        <section>
          <h2 style={{ marginBottom: 8 }}>UC1–UC3 — pojedynczy instrument</h2>

          <div
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 12,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="Symbol (np. AAPL)"
              style={{
                padding: 8,
                borderRadius: 4,
                border: "1px solid #444",
                minWidth: 90,
              }}
            />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{ padding: 8, borderRadius: 4, border: "1px solid #444" }}
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ padding: 8, borderRadius: 4, border: "1px solid #444" }}
            />

            <button
              onClick={loadHistory}
              disabled={singleLoading}
              style={{
                padding: "8px 16px",
                borderRadius: 4,
                border: "none",
                background: "#111",
                color: "white",
                cursor: "pointer",
              }}
            >
              {singleLoading ? "Pobieram..." : "Pobierz historię"}
            </button>

            <button
              onClick={loadCurrent}
              disabled={singleLoading}
              style={{
                padding: "8px 16px",
                borderRadius: 4,
                border: "none",
                background: "#111",
                color: "white",
                cursor: "pointer",
              }}
            >
              Bieżące dane
            </button>

            <button
              onClick={downloadCsv}
              disabled={singleLoading || !points.length}
              style={{
                padding: "8px 16px",
                borderRadius: 4,
                border: "none",
                background: "#111",
                color: "white",
                cursor: "pointer",
              }}
            >
              Eksport CSV
            </button>
          </div>

          {singleErr && (
            <div style={{ color: "crimson", marginBottom: 8 }}>{singleErr}</div>
          )}

          {lastQuote && (
            <div style={{ marginBottom: 12, fontSize: 14 }}>
              <strong>Bieżące dane ({symbol}):</strong>{" "}
              {lastQuote.date} | O: {lastQuote.open} H: {lastQuote.high} L:{" "}
              {lastQuote.low} C: {lastQuote.close} V: {lastQuote.volume}
            </div>
          )}

          <div
            style={{
              height: 420,
              border: "1px solid #444",
              borderRadius: 8,
              padding: 8,
              background: "#111",
            }}
          >
            <Line data={singleChartData} options={timeChartOptions} />
          </div>
        </section>
      )}

      {view === "compare" && (
        <section>
          <h2 style={{ marginBottom: 8 }}>Porównanie instrumentów</h2>

          <div
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 12,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <input
              value={cmpSymbols}
              onChange={(e) => setCmpSymbols(e.target.value)}
              placeholder="Symbole, np. AAPL,MSFT,TSLA"
              style={{
                padding: 8,
                borderRadius: 4,
                border: "1px solid #444",
                minWidth: 260,
              }}
            />
            <input
              type="date"
              value={cmpStart}
              onChange={(e) => setCmpStart(e.target.value)}
              style={{ padding: 8, borderRadius: 4, border: "1px solid #444" }}
            />
            <input
              type="date"
              value={cmpEnd}
              onChange={(e) => setCmpEnd(e.target.value)}
              style={{ padding: 8, borderRadius: 4, border: "1px solid #444" }}
            />

            <button
              onClick={loadCompare}
              disabled={cmpLoading}
              style={{
                padding: "8px 16px",
                borderRadius: 4,
                border: "none",
                background: "#111",
                color: "white",
                cursor: "pointer",
              }}
            >
              {cmpLoading ? "Porównuję..." : "Porównaj"}
            </button>
          </div>

          {cmpErr && (
            <div style={{ color: "crimson", marginBottom: 8 }}>{cmpErr}</div>
          )}

          <div
            style={{
              height: 420,
              border: "1px solid #444",
              borderRadius: 8,
              padding: 8,
              background: "#111",
              marginBottom: 16,
            }}
          >
            {cmpData ? (
              <Line data={compareChartData} options={timeChartOptions} />
            ) : (
              <div style={{ color: "#aaa", padding: 12 }}>
                Wpisz symbole i kliknij „Porównaj”.
              </div>
            )}
          </div>

          {cmpData && (
            <div>
              <h3>Podstawowe metryki</h3>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  marginTop: 8,
                }}
              >
                <thead>
                  <tr>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Symbol
                    </th>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Zwrot [%]
                    </th>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Zmienność dzienna [%]
                    </th>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Max drawdown [%]
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {cmpData.metrics.map((m) => (
                    <tr key={m.symbol}>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "center",
                        }}
                      >
                        {m.symbol}
                      </td>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "right",
                        }}
                      >
                        {m.return_pct.toFixed(2)}
                      </td>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "right",
                        }}
                      >
                        {m.volatility_pct.toFixed(2)}
                      </td>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "right",
                        }}
                      >
                        {m.max_drawdown_pct.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {view === "portfolio" && (
        <section>
          <h2 style={{ marginBottom: 8 }}>Portfel demo (backend UC rozszerzony)</h2>

          <form
            onSubmit={submitPosition}
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 12,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <input
              value={pfSymbol}
              onChange={(e) => setPfSymbol(e.target.value.toUpperCase())}
              placeholder="Symbol (np. AAPL)"
              style={{
                padding: 8,
                borderRadius: 4,
                border: "1px solid #444",
                minWidth: 90,
              }}
            />
            <input
              type="number"
              step="0.01"
              value={pfQty}
              onChange={(e) => setPfQty(e.target.value)}
              placeholder="Ilość"
              style={{
                padding: 8,
                borderRadius: 4,
                border: "1px solid #444",
                width: 90,
              }}
            />
            <input
              type="number"
              step="0.01"
              value={pfPrice}
              onChange={(e) => setPfPrice(e.target.value)}
              placeholder="Śr. cena zakupu"
              style={{
                padding: 8,
                borderRadius: 4,
                border: "1px solid #444",
                width: 130,
              }}
            />
            <button
              type="submit"
              disabled={pfLoading}
              style={{
                padding: "8px 16px",
                borderRadius: 4,
                border: "none",
                background: "#111",
                color: "white",
                cursor: "pointer",
              }}
            >
              {pfLoading ? "Zapisuję..." : "Dodaj / zaktualizuj pozycję"}
            </button>
            <button
              type="button"
              onClick={loadPortfolio}
              disabled={pfLoading}
              style={{
                padding: "8px 16px",
                borderRadius: 4,
                border: "none",
                background: "#111",
                color: "white",
                cursor: "pointer",
              }}
            >
              Odśwież portfel
            </button>
          </form>

          {pfErr && (
            <div style={{ color: "crimson", marginBottom: 8 }}>{pfErr}</div>
          )}

          {portfolio ? (
            <div>
              <div style={{ marginBottom: 8 }}>
                <strong>{portfolio.name}</strong> | Wartość całkowita:{" "}
                {portfolio.total_value.toFixed(2)}{" "}
                {portfolio.base_currency || ""}
              </div>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  marginTop: 8,
                }}
              >
                <thead>
                  <tr>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Instrument
                    </th>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Ilość
                    </th>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Śr. cena zakupu
                    </th>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Bieżąca cena
                    </th>
                    <th style={{ borderBottom: "1px solid #444", padding: 6 }}>
                      Wartość pozycji
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.positions.map((p) => (
                    <tr key={p.instrument}>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "center",
                        }}
                      >
                        {p.instrument}
                      </td>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "right",
                        }}
                      >
                        {p.quantity.toFixed(2)}
                      </td>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "right",
                        }}
                      >
                        {p.avg_open_price.toFixed(2)}
                      </td>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "right",
                        }}
                      >
                        {p.current_price.toFixed(2)}
                      </td>
                      <td
                        style={{
                          borderBottom: "1px solid #333",
                          padding: 6,
                          textAlign: "right",
                        }}
                      >
                        {p.position_value.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: "#aaa", padding: 12 }}>
              Brak danych portfela — dodaj pozycję lub kliknij „Odśwież portfel”.
            </div>
          )}
        </section>
      )}
      <div style={{ marginTop: "2rem" }}>
        <AlertsPanel />
      </div>
    </div>
  );
}