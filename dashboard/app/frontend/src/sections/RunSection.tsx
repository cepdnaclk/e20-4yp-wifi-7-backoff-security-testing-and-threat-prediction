import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import SectionTitle from '../components/common/SectionTitle'
import Badge from '../components/common/Badge'
import { useRunStatus, useRunHistory, launchExperiment, cancelRun } from '../hooks/useRun'
import type { LaunchRequest } from '../hooks/useRun'

const PIPELINE_STAGES = ['ns3', 'exporter', 'kafka', 'windowizer', 'gcn', 'db'] as const
const STAGE_LABELS: Record<string, string> = {
  ns3: 'NS-3 Simulation',
  exporter: 'Telemetry Exporter',
  kafka: 'Kafka / Redpanda',
  windowizer: 'Windowizer',
  gcn: 'GCN Detector',
  db: 'Database',
}

const SCENARIO_OPTIONS = [
  { value: 'normal',   label: 'Normal',    description: 'No attack (bias = 0)' },
  { value: 'positive', label: 'Attack (+)', description: 'Positive backoff bias' },
  { value: 'negative', label: 'Attack (−)', description: 'Negative backoff bias' },
] as const

const SEGMENT_LENGTHS = [32, 64, 128, 256] as const

function generateExpId(scenario: string, numAp: number, seed: number): string {
  const now = new Date()
  const ts = now.toISOString().slice(0, 16).replace('T', '-').replace(':', '')
  return `${ts}-${scenario}-${numAp}ap-seed${seed}`
}

export default function RunSection() {
  const { setSelectedExperimentId } = useApp()
  const { status, refresh } = useRunStatus(2000)
  const { history, reload: reloadHistory } = useRunHistory()

  // Form state
  const [scenario, setScenario] = useState<'normal' | 'positive' | 'negative'>('positive')
  const [seed, setSeed] = useState(42)
  const [simTime, setSimTime] = useState(80)
  const [bias, setBias] = useState(5000)
  const [numAp, setNumAp] = useState(1)
  const [numSta, setNumSta] = useState(2)
  const [segmentLength, setSegmentLength] = useState<32 | 64 | 128 | 256>(256)
  const [customExpId, setCustomExpId] = useState('')

  // UI state
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)
  const [completedExpId, setCompletedExpId] = useState<string | null>(null)

  const isRunning = status?.active === true
  const autoExpId = generateExpId(scenario, numAp, seed)

  // Detect when a run transitions from active → complete
  useEffect(() => {
    if (!isRunning && status?.experiment_id && status.state !== 'error') {
      const latestHistory = history[0]
      if (latestHistory?.outcome === 'success') {
        setCompletedExpId(latestHistory.experiment_id)
      }
    }
  }, [isRunning, status, history])

  const handleLaunch = async () => {
    setLaunching(true)
    setLaunchError(null)
    setCompletedExpId(null)
    try {
      const req: LaunchRequest = {
        scenario,
        seed,
        sim_time: simTime,
        bias: scenario === 'normal' ? 0 : bias,
        num_ap: numAp,
        num_sta: numSta,
        segment_length: segmentLength,
        experiment_id: customExpId || undefined,
      }
      await launchExperiment(req)
      refresh()
      reloadHistory()
    } catch (e) {
      setLaunchError(String(e))
    } finally {
      setLaunching(false)
    }
  }

  const handleCancel = async () => {
    try {
      await cancelRun()
      refresh()
    } catch (e) {
      setLaunchError(String(e))
    }
  }

  const handleViewResults = () => {
    if (completedExpId) {
      setSelectedExperimentId(completedExpId)
      window.dispatchEvent(new CustomEvent('navigate', { detail: { section: 'experiment' } }))
    }
  }

  const needsV3Warning = numAp > 1 || segmentLength < 256

  return (
    <div className="flex flex-col gap-5">
      <SectionTitle
        title="Run Experiment"
        subtitle="Configure and launch NS-3 scenarios from the dashboard"
      />

      {/* Model compatibility warning */}
      {needsV3Warning && (
        <div
          className="neu-card text-sm"
          style={{ borderLeft: '3px solid var(--color-warning)', color: 'var(--color-warning)' }}
        >
          Multi-AP or short segment configurations require <strong>GCN v3.0.0</strong>.
          If the active model is v2.x, predictions will be unreliable. Deploy v3 first.
        </div>
      )}

      {/* Configuration form — hide when run is active */}
      {!isRunning && (
        <div className="neu-card flex flex-col gap-4">
          <div className="section-title text-base">Simulation Configuration</div>

          {/* Scenario */}
          <div>
            <div className="text-xs font-semibold mb-2" style={{ color: 'var(--color-muted)' }}>SCENARIO</div>
            <div className="flex gap-2 flex-wrap">
              {SCENARIO_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={`neu-btn text-sm ${scenario === opt.value ? 'neu-btn-primary' : ''}`}
                  onClick={() => setScenario(opt.value)}
                >
                  {opt.label}
                  <span className="ml-1 text-xs opacity-60">{opt.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Numeric params grid */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="neu-inset flex flex-col gap-1 p-3">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SEED</label>
              <input
                type="number" min={1} max={9999}
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>

            <div className="neu-inset flex flex-col gap-1 p-3">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SIM TIME (s)</label>
              <input
                type="number" min={10} max={600} step={10}
                value={simTime}
                onChange={(e) => setSimTime(Number(e.target.value))}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>

            <div className="neu-inset flex flex-col gap-1 p-3" style={{ opacity: scenario === 'normal' ? 0.4 : 1 }}>
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>BIAS</label>
              <input
                type="number" step={500}
                value={scenario === 'normal' ? 0 : bias}
                disabled={scenario === 'normal'}
                onChange={(e) => setBias(Number(e.target.value))}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>

            <div className="neu-inset flex flex-col gap-1 p-3">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>ACCESS POINTS</label>
              <input
                type="number" min={1} max={6}
                value={numAp}
                onChange={(e) => {
                  const n = Number(e.target.value)
                  setNumAp(n)
                  setNumSta(n * 2)
                }}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>
          </div>

          {/* Second row */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="neu-inset flex flex-col gap-1 p-3">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>STATIONS / AP</label>
              <input
                type="number" min={1} max={12}
                value={numSta}
                onChange={(e) => setNumSta(Number(e.target.value))}
                className="bg-transparent text-sm font-mono outline-none w-full"
              />
            </div>

            <div className="neu-inset flex flex-col gap-1 p-3 lg:col-span-2">
              <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>SEGMENT LENGTH</label>
              <div className="flex gap-2 mt-1">
                {SEGMENT_LENGTHS.map((l) => (
                  <button
                    key={l}
                    className={`neu-btn text-xs py-1 px-2 ${segmentLength === l ? 'neu-btn-primary' : ''}`}
                    onClick={() => setSegmentLength(l as typeof segmentLength)}
                  >
                    {l}w
                  </button>
                ))}
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
                ~{(segmentLength * 0.1).toFixed(1)}s context window
              </div>
            </div>
          </div>

          {/* Experiment ID */}
          <div className="neu-inset flex flex-col gap-1 p-3">
            <label className="text-xs font-semibold" style={{ color: 'var(--color-muted)' }}>EXPERIMENT ID (auto-generated)</label>
            <input
              type="text"
              placeholder={autoExpId}
              value={customExpId}
              onChange={(e) => setCustomExpId(e.target.value)}
              className="bg-transparent text-sm font-mono outline-none w-full"
            />
          </div>

          {launchError && (
            <div className="text-sm" style={{ color: 'var(--color-attack)' }}>
              {launchError}
            </div>
          )}

          <button
            className="neu-btn neu-btn-primary w-full py-3 text-base font-semibold"
            onClick={handleLaunch}
            disabled={launching}
          >
            {launching ? 'Launching...' : 'Launch Experiment'}
          </button>
        </div>
      )}

      {/* Live progress panel */}
      {isRunning && status && (
        <div className="neu-card flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="section-title text-base">Running Experiment</div>
            <button
              className="neu-btn text-xs"
              style={{ color: 'var(--color-attack)' }}
              onClick={handleCancel}
            >
              Cancel
            </button>
          </div>

          <div className="font-mono text-sm" style={{ color: 'var(--color-brand)' }}>
            {status.experiment_id}
          </div>

          {status.message && (
            <div className="text-sm" style={{ color: 'var(--color-muted)' }}>
              {status.message}
            </div>
          )}

          {/* Stage progress */}
          <div className="flex flex-col gap-2">
            {PIPELINE_STAGES.map((stage) => {
              const currentIdx = status.stage ? PIPELINE_STAGES.indexOf(status.stage as typeof PIPELINE_STAGES[number]) : -1
              const stageIdx = PIPELINE_STAGES.indexOf(stage)
              const isCurrent = status.stage === stage
              const isComplete = currentIdx >= 0 && stageIdx < currentIdx
              return (
                <div
                  key={stage}
                  className="neu-inset flex items-center gap-3 py-2 px-3"
                  style={{ opacity: isComplete || isCurrent ? 1 : 0.4 }}
                >
                  <span style={{
                    color: isCurrent ? 'var(--color-brand)' : isComplete ? 'var(--color-normal)' : 'var(--color-muted)',
                    fontSize: 16,
                  }}>
                    {isCurrent ? '⚙' : isComplete ? '✓' : '○'}
                  </span>
                  <span className="text-sm">{STAGE_LABELS[stage]}</span>
                  {isCurrent && (
                    <span className="text-xs ml-auto" style={{ color: 'var(--color-brand)' }}>RUNNING</span>
                  )}
                  {isComplete && (
                    <span className="text-xs ml-auto" style={{ color: 'var(--color-normal)' }}>DONE</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Post-run results card */}
      {completedExpId && !isRunning && (
        <div className="neu-card flex flex-col gap-3">
          <div className="section-title text-base" style={{ color: 'var(--color-normal)' }}>
            Experiment Complete
          </div>
          <div className="font-mono text-sm" style={{ color: 'var(--color-muted)' }}>
            {completedExpId}
          </div>
          <button
            className="neu-btn neu-btn-primary w-full py-2"
            onClick={handleViewResults}
          >
            View Full Results
          </button>
        </div>
      )}

      {/* Run history */}
      {history.length > 0 && (
        <div className="neu-card">
          <div className="section-title text-base mb-3">Recent Runs</div>
          <div className="flex flex-col gap-2">
            {history.map((entry) => (
              <div
                key={entry.experiment_id}
                className="neu-inset flex items-center gap-3 py-2 px-3 flex-wrap"
              >
                <span className="font-mono text-xs flex-1" style={{ color: 'var(--color-muted)' }}>
                  {entry.experiment_id}
                </span>
                <span className="text-xs">
                  {entry.num_ap}AP · {entry.sim_time}s · seg={entry.segment_length}
                </span>
                <Badge
                  variant={
                    entry.outcome === 'success' ? 'normal' :
                    entry.outcome === 'running' ? 'brand' :
                    'attack'
                  }
                  label={entry.outcome}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
