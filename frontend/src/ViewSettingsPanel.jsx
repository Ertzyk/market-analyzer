import { useState, useEffect } from "react";

const DEFAULT_SETTINGS = {
  priceColor: "#4cc9f0",
  priceWidth: 2,
  showPoints: false,
  tension: 0.1,

  showSMA: true,
  smaColor: "#f72585",
  smaWidth: 2,
};

export default function ViewSettingsPanel({ onSave }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [message, setMessage] = useState("");

  // Load current settings from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("chartSettings");
    if (stored) {
      try {
        setSettings(JSON.parse(stored));
      } catch {
        setSettings(DEFAULT_SETTINGS);
      }
    }
  }, []);

  function updateField(field, value) {
    setSettings((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  function saveSettings() {
    localStorage.setItem("chartSettings", JSON.stringify(settings));
    setMessage("Ustawienia zapisane.");
    if (onSave) onSave(settings);
  }

  function resetSettings() {
    setSettings(DEFAULT_SETTINGS);
    localStorage.setItem("chartSettings", JSON.stringify(DEFAULT_SETTINGS));
    setMessage("Przywrócono ustawienia domyślne.");
    if (onSave) onSave(DEFAULT_SETTINGS);
  }

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      <h2>Konfiguracja widoku danych (UC5)</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* COLOR OF PRICE LINE */}
        <div>
          <label>Kolor linii ceny:</label>
          <input
            type="color"
            value={settings.priceColor}
            onChange={(e) => updateField("priceColor", e.target.value)}
          />
        </div>

        {/* WIDTH OF PRICE LINE */}
        <div>
          <label>Grubość linii ceny:</label>
          <input
            type="range"
            min="1"
            max="5"
            value={settings.priceWidth}
            onChange={(e) => updateField("priceWidth", Number(e.target.value))}
          />
        </div>

        {/* PRICE POINTS */}
        <div>
          <label>
            <input
              type="checkbox"
              checked={settings.showPoints}
              onChange={(e) => updateField("showPoints", e.target.checked)}
            />
            Pokaż punkty na wykresie
          </label>
        </div>

        {/* TENSION */}
        <div>
          <label>Wygładzenie linii (tension):</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={settings.tension}
            onChange={(e) => updateField("tension", Number(e.target.value))}
          />
        </div>

        {/* SMA ---------------------------------------------------------- */}
        <div>
          <label>
            <input
              type="checkbox"
              checked={settings.showSMA}
              onChange={(e) => updateField("showSMA", e.target.checked)}
            />
            Pokaż SMA(20)
          </label>
        </div>

        <div>
          <label>Kolor SMA:</label>
          <input
            type="color"
            value={settings.smaColor}
            onChange={(e) => updateField("smaColor", e.target.value)}
          />
        </div>

        <div>
          <label>Grubość SMA:</label>
          <input
            type="range"
            min="1"
            max="5"
            value={settings.smaWidth}
            onChange={(e) => updateField("smaWidth", Number(e.target.value))}
          />
        </div>

        {/* ACTION BUTTONS */}
        <button onClick={saveSettings} style={{ padding: 8 }}>
          Zapisz ustawienia
        </button>
        <button onClick={resetSettings} style={{ padding: 8, marginTop: 8 }}>
          Przywróć domyślne
        </button>

        {message && <p style={{ color: "lightgreen" }}>{message}</p>}
      </div>
    </div>
  );
}