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

ChartJS.register(TimeScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

function sma(arr, win = 20) {
  const out = new Array(arr.length).fill(null);
  let sum = 0;
  for (let i = 0; i < arr.length; i++) {
    sum += arr[i];
    if (i >= win) sum -= arr[i - win];
    if (i >= win - 1) out[i] = +(sum / win).toFixed(4);
  }
  return out;
}

export default function App() {
  const [symbol, setSymbol] = useState("AAPL");
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      setErr("");
      setLoading(true);
      const url = `http://127.0.0.1:8000/api/fetch?symbol=${symbol}&period=1y&interval=1d`;
      const res = await axios.get(url);
      console.log("API:", url, "len=", res.data.points?.length, "sample=", res.data.points?.[0]);
      setPoints(res.data.points || []);
    } catch (e) {
      console.error(e);
      setErr("Błąd pobierania (sprawdź backend / symbol / limity API).");
      setPoints([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(); // pierwsze pobranie
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const closes = points.map((p) => Number(p.close));
  const sma20 = sma(closes, 20);

  const data = {
  datasets: [
    {
      label: `${symbol} — Close`,
      // podajemy całe obiekty z backendu
      data: points, 
      parsing: { xAxisKey: "date", yAxisKey: "close" },
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.1,
      borderColor: "#4cc9f0",
    },
    {
      label: "SMA(20)",
      // tworzymy drugi strumień: {date, sma}
      data: points
        .map((p, i) => ({ date: p.date, sma: sma20[i] }))
        .filter(d => d.sma), 
      parsing: { xAxisKey: "date", yAxisKey: "sma" },
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.1,
      borderColor: "#f72585",
    },
  ],
};

  const options = {
  // UWAGA: wyłączamy parsing:false, żeby zadziałały xAxisKey/yAxisKey
  maintainAspectRatio: false,
  spanGaps: true,
  scales: {
    x: { type: "time", time: { unit: "day" } }, // wymuś „dzień”
    y: { beginAtZero: false },
  },
};

  return (
    <div style={{ maxWidth: 980, margin: "24px auto", fontFamily: "system-ui" }}>
      <h2 style={{ marginBottom: 12 }}>Analiza akcji — prototyp (AAPL + SMA20)</h2>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="Symbol (np. AAPL)"
        />
        <button onClick={load} disabled={loading}>
          {loading ? "Pobieram..." : "Pobierz"}
        </button>
      </div>

      {err && <div style={{ color: "crimson", marginBottom: 8 }}>{err}</div>}

      <div style={{ height: 420, border: "1px solid #eee", borderRadius: 8, padding: 8 }}>
        <Line data={data} options={options} />
      </div>
    </div>
  );
}