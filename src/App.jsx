
import React, { useEffect, useState, useCallback } from 'react';
import { api } from './api.js';

import {
  ReadingCards,
  PredictionCard,
  SensorReadings,
  Chart,
  HistoryTable,
  ModelInsights,
  DeviceTab,
  Badge
} from './components.jsx';

const TABS = ['Live', 'History', 'Model Insights', 'Device'];

export default function App() {
  const [tab, setTab] = useState('Live');
  const [health, setHealth] = useState(null);
  const [latest, setLatest] = useState(null);
  const [recent, setRecent] = useState([]);
  const [down, setDown] = useState(false);
  const [err, setErr] = useState('');
  const [info, setInfo] = useState(null);
  const [hist, setHist] = useState({ items: [], total: 0 });

  const [f, setF] = useState({
    search: '',
    source: '',
    prediction: ''
  });

  const poll = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      setDown(false);

      const [l, r] = await Promise.all([
        api.latest('hardware'),
        api.history({ limit: 40, source: 'hardware' })
      ]);

      const items = Array.isArray(r?.items) ? r.items : [];
      setRecent(items);
      setLatest(l?.reading ?? l ?? items[0] ?? null);
    } catch (error) {
      console.error('Dashboard polling error:', error);
      setDown(true);
    }
  }, []);

  useEffect(() => {
    poll();
    const timer = setInterval(poll, 5000);
    return () => clearInterval(timer);
  }, [poll]);

  const loadHistory = useCallback(async () => {
    try {
      const data = await api.history({
        limit: 200,
        ...f
      });

      setHist({
        items: Array.isArray(data?.items) ? data.items : [],
        total: data?.total ?? 0
      });
    } catch (error) {
      console.error('History error:', error);
      setHist({ items: [], total: 0 });
    }
  }, [f]);

  useEffect(() => {
    if (tab === 'History') loadHistory();
  }, [tab, loadHistory, latest?.id]);

  useEffect(() => {
    if (tab === 'Model Insights') {
      api.model()
        .then(setInfo)
        .catch(error => setErr(error.message));
    }
  }, [tab]);

  const csvHref =
    '/api/history/export.csv' +
    (f.source ? `?source=${encodeURIComponent(f.source)}` : '');

  return (
    <div className="app animated-app">

      <style>{`
        @keyframes livePulse {
          0% { box-shadow: 0 0 0 0 rgba(0,230,150,.6); }
          70% { box-shadow: 0 0 0 9px rgba(0,230,150,0); }
          100% { box-shadow: 0 0 0 0 rgba(0,230,150,0); }
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes scan {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(300%); }
        }

        .live-heading {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .live-indicator {
          display: inline-flex;
          align-items: center;
          gap: 9px;
          padding: 7px 13px;
          border-radius: 30px;
          background: rgba(0,230,150,.09);
          color: #00e69a;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 1px;
        }

        .live-dot {
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background: #00e69a;
          animation: livePulse 1.5s infinite;
        }

        .live-line {
          height: 3px;
          width: 100%;
          overflow: hidden;
          background: rgba(0,230,150,.12);
          border-radius: 10px;
          margin: 14px 0 22px;
        }

        .live-line::after {
          content: "";
          display: block;
          height: 100%;
          width: 30%;
          background: linear-gradient(90deg, transparent, #00e69a, transparent);
          animation: scan 3s linear infinite;
        }

        .animated-app .panel,
        .animated-app .card {
          animation: fadeUp .55s ease both;
        }

        .animated-app .panel:hover,
        .animated-app .card:hover {
          transform: translateY(-3px);
          transition: transform .25s ease, border-color .25s ease;
        }

        .last-update {
          color: #8b9bb8;
          font-size: 12px;
          margin: 8px 0 18px;
        }
      `}</style>

      <header>
        <h1>⛽ Fuel Adulteration Detector</h1>

        <nav>
          {TABS.map(item => (
            <button
              key={item}
              className={item === tab ? 'active' : ''}
              onClick={() => setTab(item)}
            >
              {item}
            </button>
          ))}
        </nav>
      </header>

      {err && <div className="error">Error: {err}</div>}

      {tab === 'Live' && (
        <div className="live-dashboard">

          <div className="live-heading">
            <h2>Live Sensor Dashboard</h2>

            <div className="live-indicator">
              <span
                className="live-dot"
                style={{
                  background: down ? '#ff5252' : '#00e69a'
                }}
              />
              {down ? 'DISCONNECTED' : 'LIVE MONITORING'}
            </div>
          </div>

          <div className="live-line" />

          <div className="last-update">
            {latest?.received_at
              ? `Last hardware reading: ${new Date(latest.received_at).toLocaleString()}`
              : 'Waiting for hardware reading...'}
            {' · '}
            Auto refresh every 5 seconds
          </div>

          {latest && latest.source !== 'hardware' && (
            <div className="simbanner">
              <Badge source={latest.source} />
              {' '}This is not a physical hardware measurement.
            </div>
          )}

          <ReadingCards r={latest} />

          <PredictionCard r={latest} />

          <SensorReadings r={latest} />

          <div className="grid3">
            <Chart
              data={recent}
              dataKey="dielectric"
              title="Dielectric (εr)"
              color="#4cc9f0"
            />

            <Chart
              data={recent}
              dataKey="probability_adulterated"
              title="Adulteration Probability"
              color="#f72585"
              domain={[0, 1]}
            />

            <Chart
              data={recent}
              dataKey="temperature"
              title="Temperature (°C)"
              color="#ffd166"
            />
          </div>

        </div>
      )}

      {tab === 'History' && (
        <div className="panel">
          <h2>Reading History</h2>

          <div className="row">
            <input
              placeholder="Search device / fuel / result..."
              value={f.search}
              onChange={e =>
                setF({ ...f, search: e.target.value })
              }
            />

            <select
              value={f.source}
              onChange={e =>
                setF({ ...f, source: e.target.value })
              }
            >
              <option value="">All sources</option>
              <option value="hardware">Hardware</option>
              <option value="simulation">Simulation</option>
              <option value="manual_test">Manual test</option>
            </select>

            <select
              value={f.prediction}
              onChange={e =>
                setF({ ...f, prediction: e.target.value })
              }
            >
              <option value="">All results</option>
              <option value="Pure">Pure</option>
              <option value="Potentially">Potentially Adulterated</option>
            </select>

            <a className="btn" href={csvHref}>
              Download CSV
            </a>
          </div>

          <p className="muted small">
            {hist.total} matching readings
          </p>

          <HistoryTable rows={hist.items} />
        </div>
      )}

      {tab === 'Model Insights' && (
        <ModelInsights info={info} />
      )}

      {tab === 'Device' && (
        <DeviceTab health={health} />
      )}

    </div>
  );
}
