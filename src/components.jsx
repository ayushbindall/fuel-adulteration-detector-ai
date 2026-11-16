
import React from 'react';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

const safeNumber = (value, fallback = 0) => {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }

  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const hasValue = value =>
  value !== null && value !== undefined && value !== '';

const displayValue = (value, digits = 2) => {
  if (!hasValue(value)) return 'Not received';

  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : String(value);
};

const fmtTime = iso =>
  iso ? new Date(iso).toLocaleTimeString() : '—';

const SRC = {
  hardware: ['HARDWARE', 'ok'],
  simulation: ['SIMULATION', 'warn'],
  manual_test: ['MANUAL TEST', 'warn']
};

export const Badge = ({ source }) => {
  const [label, color] = SRC[source] || ['UNKNOWN', 'warn'];
  return <span className={`badge ${color}`}>{label}</span>;
};

export const Dot = ({ ok, label }) => (
  <div className="stat">
    <span className={`dot ${ok ? 'on' : 'off'}`} />
    {label}
  </div>
);

export const Disclaimer = () => (
  <div className="disclaimer">
    ⚠ Missing sensor readings are displayed as unavailable, not as zero.
  </div>
);

export function StatusBar({ health, down, latest }) {
  return (
    <div className="panel row">
      <Dot
        ok={!down}
        label={down ? 'Backend unreachable' : 'Backend online'}
      />

      <Dot
        ok={!!health?.model_loaded}
        label={
          health?.model_loaded
            ? `Model ${health.model_version || 'loaded'}`
            : 'Model not loaded'
        }
      />

      <Dot
        ok={!!health?.device_online}
        label={
          health?.device_online
            ? 'Hardware device online'
            : 'No hardware connected'
        }
      />

      <div className="stat muted">
        Last reading: {fmtTime(latest?.received_at)}
      </div>
    </div>
  );
}

export function ReadingCards({ r }) {
  const items = [
    {
      name: 'Fuel Type',
      value: r?.fuel_type || '—'
    },
    {
      name: 'Temperature',
      value: hasValue(r?.temperature)
        ? `${displayValue(r.temperature, 1)} °C`
        : 'Not received'
    },
    {
      name: 'Dielectric (εr)',
      value: displayValue(r?.dielectric)
    }
  ];

  return (
    <div className="cards">
      {items.map(item => (
        <div className="card" key={item.name}>
          <div className="k">{item.name}</div>
          <div className="v">{item.value}</div>
        </div>
      ))}
    </div>
  );
}

/* LIVE SENSOR READINGS */

export function SensorReadings({ r }) {
  const sensors = [
    {
      name: 'TCS34725 COLOR SENSOR',
      subtitle: 'RGB and Clear light intensity',
      values: [
        ['Red', r?.tcs_red],
        ['Green', r?.tcs_green],
        ['Blue', r?.tcs_blue],
        ['Clear', r?.tcs_clear]
      ]
    },
    {
      name: 'BMP280',
      subtitle: 'Temperature and atmospheric pressure',
      values: [
        ['Temperature', r?.temperature, '°C'],
        ['Pressure', r?.bmp_pressure, 'hPa']
      ]
    },
    {
      name: 'ADS1115 ADC',
      subtitle: 'Analog input channels',
      values: [
        ['Channel A0', r?.ads_a0],
        ['Channel A1', r?.ads_a1],
        ['Channel A2', r?.ads_a2],
        ['Channel A3', r?.ads_a3]
      ]
    },
    {
      name: 'HX711 LOAD CELL',
      subtitle: 'Load cell raw measurement',
      values: [
        ['Raw Reading', r?.hx711_raw]
      ]
    }
  ];

  return (
    <div className="panel">
      <h3>Live Sensor Readings</h3>

      <div className="grid2">
        {sensors.map(sensor => (
          <div className="panel" key={sensor.name}>
            <h4>{sensor.name}</h4>
            <p className="muted small">{sensor.subtitle}</p>

            {sensor.values.map(([label, value, unit]) => (
              <div className="row sensor-row" key={label}>
                <span>{label}</span>
                <strong>
                  {displayValue(value)}
                  {hasValue(value) && unit ? ` ${unit}` : ''}
                </strong>
              </div>
            ))}
          </div>
        ))}
      </div>

      {!r && (
        <p className="muted small">
          Waiting for hardware data. No sensor reading has arrived yet.
        </p>
      )}
    </div>
  );
}

/* AI PREDICTION - CLEAN VERSION */

export function PredictionCard({ r }) {
  if (!r || !r.prediction) {
    return (
      <div className="panel">
        <h3>AI Detection</h3>
        <p className="muted">
          Waiting for an AI prediction from the backend.
        </p>
      </div>
    );
  }

  const prediction = r.prediction;
  const bad = prediction.startsWith('Potentially');

  return (
    <div className={`panel pred ${bad ? 'bad' : 'good'}`}>
      <h3>
        AI Detection <Badge source={r.source} />
      </h3>

      <div className="verdict">{prediction}</div>
    </div>
  );
}

export function Chart({
  data,
  dataKey,
  title,
  color,
  domain
}) {
  const chartData = [...(Array.isArray(data) ? data : [])]
    .reverse()
    .filter(item => hasValue(item[dataKey]))
    .map(item => ({
      t: fmtTime(item.received_at),
      v: safeNumber(item[dataKey])
    }));

  return (
    <div className="panel chart">
      <h4>{title}</h4>

      {chartData.length === 0 ? (
        <p className="muted small">No readings available for this chart.</p>
      ) : (
        <ResponsiveContainer width="100%" height={170}>
          <LineChart data={chartData}>
            <CartesianGrid stroke="#25314a" strokeDasharray="3 3" />
            <XAxis dataKey="t" stroke="#7f8fb0" />
            <YAxis
              stroke="#7f8fb0"
              domain={domain || ['auto', 'auto']}
            />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="v"
              stroke={color}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

const MEAN = {
  Petrol: 2.15,
  Diesel: 2.74,
  Kerosene: 2.45
};

export function SimulationPanel({ onSend, busy }) {
  const [fuel, setFuel] = React.useState('Petrol');

  const send = contaminated => {
    onSend({
      device_id: 'ui_simulator',
      fuel_type: fuel,
      source: 'simulation',
      temperature: +(24 + Math.random() * 6).toFixed(1),
      dielectric: +(
        contaminated
          ? 6 + Math.random() * 14
          : MEAN[fuel] + (Math.random() - 0.5) * 0.3
      ).toFixed(2)
    });
  };

  return (
    <div className="panel sim">
      <h4>
        🧪 Simulation Mode{' '}
        <span className="badge warn">TESTING ONLY</span>
      </h4>

      <p className="muted small">
        Generates simulated values for UI testing only.
        These are not physical sensor measurements.
      </p>

      <div className="row">
        <select
          value={fuel}
          onChange={e => setFuel(e.target.value)}
        >
          {Object.keys(MEAN).map(item => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>

        <button disabled={busy} onClick={() => send(false)}>
          Send Pure-like
        </button>

        <button disabled={busy} onClick={() => send(true)}>
          Send Adulterated-like
        </button>
      </div>
    </div>
  );
}

export function HistoryTable({ rows }) {
  const safeRows = Array.isArray(rows) ? rows : [];

  return (
    <div className="tablewrap">
      <table>
        <thead>
          <tr>
            {[
              '#', 'Time', 'Source', 'Device', 'Fuel',
              '°C', 'εr', 'Prediction', 'P(adult.)'
            ].map(item => <th key={item}>{item}</th>)}
          </tr>
        </thead>

        <tbody>
          {safeRows.map(row => {
            const prediction = row.prediction || 'Unknown';
            const bad = prediction.startsWith('Potentially');

            return (
              <tr key={row.id}>
                <td>{row.id ?? '—'}</td>
                <td>
                  {row.received_at
                    ? new Date(row.received_at).toLocaleString()
                    : '—'}
                </td>
                <td><Badge source={row.source} /></td>
                <td>{row.device_id || '—'}</td>
                <td>{row.fuel_type || '—'}</td>
                <td>{displayValue(row.temperature, 1)}</td>
                <td>{displayValue(row.dielectric)}</td>
                <td className={bad ? 'badc' : 'okc'}>
                  {prediction}
                  {row.uncertain ? ' (uncertain)' : ''}
                </td>
                <td>
                  {hasValue(row.probability_adulterated)
                    ? `${(safeNumber(row.probability_adulterated) * 100).toFixed(1)}%`
                    : '—'}
                </td>
              </tr>
            );
          })}

          {!safeRows.length && (
            <tr>
              <td colSpan="9" className="muted">
                No readings available yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const pct = value => {
  if (!hasValue(value)) return '—';
  const number = safeNumber(value, NaN);
  if (!Number.isFinite(number)) return '—';
  return `${(number <= 1 ? number * 100 : number).toFixed(1)}%`;
};

const metricValue = value =>
  hasValue(value) && Number.isFinite(Number(value))
    ? Number(value).toFixed(3)
    : '—';

export function ModelInsights({ info }) {
  if (!info) {
    return (
      <div className="panel">
        <h3>Model Insights</h3>
        <p className="muted">Loading model information...</p>
      </div>
    );
  }

  const model = info.data || info.model_info || info;
  const test = model.heldout_test || model.test_metrics || {};
  const metadata = model.metadata || model.model_metadata || {};
  const dataset = metadata.dataset || model.dataset || {};
  const modelName = metadata.algorithm || model.algorithm || model.model_name || 'ML Model';
  const version = metadata.model_version || model.model_version || model.version || '—';
  const inputColumns = Array.isArray(metadata.input_columns)
    ? metadata.input_columns
    : Array.isArray(model.input_columns)
      ? model.input_columns
      : [];

  const matrix = test.confusion_matrix && test.confusion_matrix.matrix
    ? test.confusion_matrix.matrix
    : test.confusion_matrix;
  const validMatrix = Array.isArray(matrix) && matrix.length >= 2 &&
    Array.isArray(matrix[0]) && matrix[0].length >= 2 &&
    Array.isArray(matrix[1]) && matrix[1].length >= 2;

  const rawImportance =
    (model.deployed_details && model.deployed_details.feature_importance_permutation_auc) ||
    model.feature_importance_permutation_auc || {};
  const importance = Object.entries(rawImportance).map(([name, value]) => ({
    name,
    drop: safeNumber(value && typeof value === 'object' ? value.mean_auc_drop : value, 0)
  })).filter(item => Number.isFinite(item.drop));

  const rawUnseen = model.leave_one_adulterant_out || {};
  const unseen = Object.entries(rawUnseen).map(([name, value]) => ({
    name,
    recall: safeNumber(value && typeof value === 'object' ? value.recall_unseen_adulterant : value, 0) * 100
  }));

  const limitations = Array.isArray(metadata.limitations)
    ? metadata.limitations
    : Array.isArray(model.limitations)
      ? model.limitations
      : [];

  const metrics = [
    ['Accuracy', pct(test.accuracy)],
    ['Precision', pct(test.precision)],
    ['Recall', pct(test.recall)],
    ['F1 Score', metricValue(test.f1)],
    ['ROC-AUC', metricValue(test.roc_auc)],
    ['Specificity', pct(test.specificity)]
  ];

  return (
    <div className="grid2 model-insights">
      <div className="panel">
        <h3>Model Performance</h3>
        <p className="muted small">
          <strong>{modelName}</strong> · Version: {version}
        </p>
        <p className="muted small">
          Test samples: {hasValue(test.n_test) ? test.n_test : '—'}
          {inputColumns.length ? ` · Input features: ${inputColumns.length}` : ''}
        </p>

        <div className="cards">
          {metrics.map(([name, value]) => (
            <div className="card" key={name}>
              <div className="k">{name}</div>
              <div className="v">{value}</div>
            </div>
          ))}
        </div>

        <h4>Confusion Matrix</h4>
        {validMatrix ? (
          <table className="cm">
            <thead>
              <tr>
                <th></th>
                <th>Predicted Pure</th>
                <th>Predicted Adulterated</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th>Actual Pure</th>
                <td className="cmgood">{matrix[0][0]}</td>
                <td className="cmbad">{matrix[0][1]}</td>
              </tr>
              <tr>
                <th>Actual Adulterated</th>
                <td className="cmbad">{matrix[1][0]}</td>
                <td className="cmgood">{matrix[1][1]}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <p className="muted small">Confusion matrix was not provided by the model API.</p>
        )}
      </div>

      <div className="panel">
        <h3>Feature Importance</h3>
        {importance.length ? (
          <ResponsiveContainer width="100%" height={Math.max(200, importance.length * 34)}>
            <BarChart data={importance} layout="vertical" margin={{ left: 12, right: 16 }}>
              <XAxis type="number" stroke="#7f8fb0" />
              <YAxis type="category" dataKey="name" stroke="#7f8fb0" width={110} />
              <Tooltip />
              <Bar dataKey="drop" name="Mean AUC drop" fill="#4cc9f0" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted small">Feature importance data is not available in the /api/model response.</p>
        )}

        <h3>Unseen Adulterant Recall</h3>
        {unseen.length ? (
          <ResponsiveContainer width="100%" height={Math.max(180, unseen.length * 38)}>
            <BarChart data={unseen} margin={{ bottom: 24 }}>
              <XAxis dataKey="name" stroke="#7f8fb0" angle={-15} textAnchor="end" interval={0} />
              <YAxis domain={[0, 100]} stroke="#7f8fb0" />
              <Tooltip formatter={value => `${Number(value).toFixed(1)}%`} />
              <Bar dataKey="recall" name="Recall" fill="#f72585" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted small">Unseen-adulterant evaluation data is not available.</p>
        )}
      </div>

      <div className="panel wide">
        <h3>Dataset & Model Details</h3>
        <p className="muted small">
          Dataset: {dataset.file || dataset.name || 'Information unavailable'}
          {' · '}Rows: {hasValue(dataset.rows) ? dataset.rows : '—'}
        </p>
        {dataset.provenance && <p className="muted small">{dataset.provenance}</p>}
        {inputColumns.length > 0 && (
          <>
            <h4>Input Features</h4>
            <p className="muted small">{inputColumns.join(' · ')}</p>
          </>
        )}
        <h4>Limitations</h4>
        {limitations.length ? (
          <ul>{limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
        ) : (
          <p className="muted small">No limitations were included in the model API response.</p>
        )}
      </div>
    </div>
  );
}

export function DeviceTab({ health }) {
  return (
    <div className="grid2">
      <div className="panel">
        <h3>Device Status</h3>

        <Dot
          ok={!!health?.device_online}
          label={
            health?.device_online
              ? 'Hardware device online'
              : 'No hardware connected'
          }
        />

        <p className="muted small">
          Last hardware reading:{' '}
          {health?.last_hardware_reading_at
            ? new Date(health.last_hardware_reading_at).toLocaleString()
            : 'Never'}
        </p>

        <h4>Sensor Modules</h4>
        <table>
          <tbody>
            <tr><td>TCS34725</td><td>RGB / Clear</td></tr>
            <tr><td>BMP280</td><td>Temperature / Pressure</td></tr>
            <tr><td>ADS1115</td><td>Analog channels</td></tr>
            <tr><td>HX711</td><td>Load cell</td></tr>
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3>ESP32 Connection</h3>
        <ol className="small">
          <li>Start FastAPI backend on port 8000.</li>
          <li>Connect ESP32 and computer to the same Wi-Fi.</li>
          <li>Use your computer's current IPv4 address in ESP32 code.</li>
          <li>Send sensor data to <code>/api/sensors</code>.</li>
        </ol>
        <p className="muted small">
          A sensor is considered to have a reading only when the backend
          receives a non-empty value for that sensor.
        </p>
      </div>
    </div>
  );
}
