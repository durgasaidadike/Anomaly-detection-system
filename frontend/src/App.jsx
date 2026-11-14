import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bell,
  ChartNoAxesCombined,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  FileText,
  Folder,
  FolderKanban,
  HardDrive,
  House,
  Layers3,
  RotateCcw,
  Settings,
  ShieldCheck,
  ShieldPlus,
  UserRound,
  Workflow,
  CheckCircle2,
} from 'lucide-react'

import './App.css'
import useBackendHealth from './hooks/useBackendHealth'

const mainNavigation = [
  { label: 'Dashboard', Icon: House, active: true },
  { label: 'Event Monitor', Icon: Activity },
  { label: 'Pattern Viewer', Icon: Workflow },
  { label: 'Risk Panel', Icon: AlertTriangle },
  { label: 'Recovery Panel', Icon: ShieldPlus },
  { label: 'System Health', Icon: ShieldCheck },
  { label: 'Analytics', Icon: ChartNoAxesCombined },
]

const secondaryNavigation = [
  { label: 'Projects', Icon: FolderKanban },
  { label: 'Configuration', Icon: Settings },
  { label: 'Logs & Audit', Icon: FileText },
]

const metrics = [
  { label: 'Events (24h)', Icon: Folder, color: 'blue' },
  { label: 'Patterns', Icon: Layers3, color: 'purple' },
  { label: 'Anomalies', Icon: AlertTriangle, color: 'red' },
  { label: 'Blocked Risks', Icon: ShieldCheck, color: 'green' },
  { label: 'Recoveries', Icon: RotateCcw, color: 'green' },
]

const monitoredServices = [
  'Spring Boot API',
  'Watchdog',
  'ML Engine',
  'Recovery Manager',
]

function Sidebar({ backendStatus }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <ShieldCheck className="brand-icon" size={35} />
        <span>PRISM</span>
      </div>

      <nav className="navigation" aria-label="Main navigation">
        <div className="navigation-group">
          {mainNavigation.map(({ label, Icon, active }) => (
            <div
              className={`nav-item ${active ? 'active' : ''}`}
              key={label}
              aria-current={active ? 'page' : undefined}
            >
              <Icon size={19} strokeWidth={2} />
              <span>{label}</span>
            </div>
          ))}
        </div>

        <div className="navigation-divider" />

        <div className="navigation-group">
          {secondaryNavigation.map(({ label, Icon }) => (
            <div className="nav-item" key={label}>
              <Icon size={19} strokeWidth={2} />
              <span>{label}</span>
            </div>
          ))}
        </div>
      </nav>

      <div className="sidebar-bottom">
        <div className={`sidebar-status ${backendStatus}`}>
          {backendStatus === 'connected'
            ? <CheckCircle2 size={20} />
            : <CircleHelp size={20} />
          }

          <div>
            <strong>
              {backendStatus === 'connected'
                ? 'Backend Connected'
                : backendStatus === 'checking'
                  ? 'Checking Backend'
                  : backendStatus === 'degraded'
                    ? 'Backend Degraded'
                    : 'Backend Unavailable'}
            </strong>

            <span>
              {backendStatus === 'connected'
                ? 'Spring Boot API reachable'
                : 'Other PRISM services not yet verified'}
            </span>
          </div>
        </div>

        <div className="sidebar-decoration">
          <div className="mountain mountain-one" />
          <div className="mountain mountain-two" />
        </div>
      </div>
    </aside>
  )
}

function Topbar({ backendStatus, isRefreshing, onRefresh }) {
  return (
    <header className="topbar">
      <div className="topbar-heading">
        <h1>PRISM</h1>
        <p>Pattern Recognition in Integration System for Anomaly Monitoring</p>
      </div>

      <div className="topbar-actions">
        <button
          type="button"
          className={`connection-badge ${backendStatus}`}
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Click to refresh Spring Boot health"
        >
          <span className={`neutral-dot ${backendStatus}`} />

          {backendStatus === 'connected'
            ? 'Backend Connected'
            : backendStatus === 'checking'
              ? 'Checking Backend'
              : backendStatus === 'degraded'
                ? 'Backend Degraded'
                : 'Backend Unavailable'}
        </button>

        <div className="project-selector">
          Project: Not selected
          <ChevronDown size={17} />
        </div>

        <div className="header-icon" aria-label="Notifications">
          <Bell size={23} />
          <span className="notification-dot" />
        </div>

        <div className="header-icon" aria-label="User profile">
          <UserRound size={25} />
        </div>
      </div>
    </header>
  )
}

function MetricCard({ metric }) {
  const { label, Icon, color } = metric

  return (
    <article className="metric-card">
      <div className={`metric-icon ${color}`}>
        <Icon size={29} strokeWidth={2.2} />
      </div>

      <div className="metric-content">
        <span className="metric-label">{label}</span>
        <strong className="metric-value">—</strong>
        <span className="metric-description">Awaiting API data</span>
      </div>
    </article>
  )
}

function PanelHeader({ icon: Icon, title, action }) {
  return (
    <div className="panel-header">
      <div className="panel-title">
        <Icon size={21} strokeWidth={2.3} />
        <h2>{title}</h2>
      </div>

      {action && <span className="panel-action">{action}</span>}
    </div>
  )
}

function EmptyData({ message = 'No data available yet' }) {
  return (
    <div className="empty-data">
      <Database size={23} />
      <span>{message}</span>
    </div>
  )
}

function EventMonitor() {
  return (
    <section className="panel event-panel">
      <PanelHeader
        icon={Activity}
        title="Real-Time Event Monitor"
        action={
          <span className="live-label">
            <span className="neutral-dot" />
            Awaiting events
          </span>
        }
      />

      <div className="event-table-wrapper">
        <table className="event-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Path</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan="4">
                <EmptyData message="Event records will appear here" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}

function RiskPanel() {
  return (
    <section className="panel risk-panel">
      <PanelHeader
        icon={Layers3}
        title="Risk Status"
        action={<CircleHelp size={17} />}
      />

      <div className="risk-content">
        <div className="risk-gauge">
          <div className="gauge-inner">
            <strong>—</strong>
            <span>Risk Score</span>
            <small>Awaiting assessment</small>
          </div>
        </div>
      </div>
    </section>
  )
}

function PatternPanel() {
  return (
    <section className="panel pattern-panel">
      <PanelHeader
        icon={Layers3}
        title="Behavioral Patterns"
        action={
          <span className="panel-action">
            View All <ArrowUpRight size={14} />
          </span>
        }
      />

      <EmptyData message="Learned patterns will appear here" />
    </section>
  )
}

function SystemHealthPanel({ backendStatus }) {
  return (
    <section className="panel health-panel">
      <PanelHeader icon={Activity} title="System Health" />

      <div className="service-list">
        {monitoredServices.map((service) => {
          const isBackend = service === 'Spring Boot API'

          const statusLabel = isBackend
            ? {
                connected: 'Connected',
                checking: 'Checking',
                degraded: 'Degraded',
                unavailable: 'Unavailable',
              }[backendStatus]
            : 'Unknown'

          return (
            <div className="service-row" key={service}>
              <div className="service-name">
                <span
                  className={
                    isBackend
                      ? `neutral-dot ${backendStatus}`
                      : 'neutral-dot'
                  }
                />
                {service}
              </div>

              <span
                className={
                  isBackend
                    ? `service-status ${backendStatus}`
                    : 'unknown-status'
                }
              >
                {statusLabel}
              </span>
            </div>
          )
        })}
      </div>

      <div className="resource-placeholder">
        <div className="resource-item">
          <span>CPU</span>
          <strong>—</strong>
          <div className="resource-track" />
        </div>

        <div className="resource-item">
          <span>Memory</span>
          <strong>—</strong>
          <div className="resource-track" />
        </div>

        <div className="resource-item">
          <span>Disk</span>
          <strong>—</strong>
          <div className="resource-track" />
        </div>

        <small>Resource metrics pending</small>
      </div>
    </section>
  )
}

function RecoveryPanel() {
  return (
    <section className="panel recovery-panel">
      <PanelHeader
        icon={RotateCcw}
        title="Recovery Panel"
        action={
          <span className="panel-action">
            View All <ArrowUpRight size={14} />
          </span>
        }
      />
      <EmptyData message="Recovery history will appear here" />
    </section>
  )
}

function AnalyticsPanel() {
  return (
    <section className="panel analytics-panel">
      <PanelHeader
        icon={ChartNoAxesCombined}
        title="Analytics"
        action={<span className="period-label">Last 24 Hours</span>}
      />

      <ChartPlaceholder />
    </section>
  )
}

function ChartPlaceholder() {
  return (
    <div className="chart-placeholder">
      <div className="chart-y-labels">
        <span>—</span>
        <span>—</span>
        <span>—</span>
        <span>—</span>
      </div>

      <div className="chart-area">
        <div className="chart-grid-lines">
          <span />
          <span />
          <span />
          <span />
        </div>

        <div className="chart-message">
          <ChartNoAxesCombined size={24} />
          <span>Waiting for metric data</span>
        </div>

        <div className="chart-x-labels">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
        </div>
      </div>
    </div>
  )
}

function DistributionPanel() {
  return (
    <section className="panel distribution-panel">
      <PanelHeader icon={Workflow} title="Event Distribution" />

      <div className="distribution-content">
        <div className="donut-placeholder">
          <div>
            <strong>—</strong>
            <span>Events</span>
          </div>
        </div>

        <div className="distribution-legend">
          {['Create', 'Modify', 'Delete', 'Rename', 'Others'].map(
            (item) => (
              <div className="legend-row" key={item}>
                <span className="legend-label">{item}</span>
                <strong>—</strong>
              </div>
            ),
          )}
        </div>
      </div>
      <p className="panel-footnote">Distribution unavailable until data arrives</p>
    </section>
  )
}

function RiskTrendPanel() {
  return (
    <section className="panel trend-panel">
      <PanelHeader icon={Activity} title="Risk Trend" />
      <ChartPlaceholder />
    </section>
  )
}

function RecentActivityPanel() {
  return (
    <section className="panel activity-panel">
      <PanelHeader
        icon={Clock3}
        title="Recent Activity"
        action={
          <span className="panel-action">
            View Logs <ArrowUpRight size={14} />
          </span>
        }
      />

      <EmptyData message="Recent system activity will appear here" />
    </section>
  )
}

function Dashboard({ backendStatus }) {
  return (
    <>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </div>

      <div className="dashboard-grid primary-grid">
        <EventMonitor />
        <RiskPanel />
        <PatternPanel />
      </div>

      <div className="dashboard-grid secondary-grid">
        <SystemHealthPanel backendStatus={backendStatus} />
        <RecoveryPanel />
        <AnalyticsPanel />
      </div>

      <div className="dashboard-grid bottom-grid">
        <DistributionPanel />
        <RiskTrendPanel />
        <RecentActivityPanel />
      </div>
    </>
  )
}

function App() {
  const backendHealth = useBackendHealth()

  const backendStatus = backendHealth.status

  return (
    <div className="app-layout">
      <Sidebar backendStatus={backendStatus} />

      <div className="main-area">
        <Topbar
          backendStatus={backendStatus}
          isRefreshing={backendHealth.isRefreshing}
          onRefresh={backendHealth.refresh}
        />

        <main className="dashboard-content" id="dashboard">
          <div className="page-intro">
            <div>
              <span className="eyebrow">
                SECURITY OPERATIONS CENTER
              </span>

              <h2>Dashboard Overview</h2>

              <p>
                Monitor behavioral intelligence, risk assessments
                and system operations.
              </p>
            </div>

            <div
              className={`data-status ${backendStatus}`}
              title={backendHealth.error || 'Spring Boot health status'}
            >
              <span className={`neutral-dot ${backendStatus}`} />

              {backendStatus === 'connected'
                ? 'Spring Boot API connected'
                : backendStatus === 'checking'
                  ? 'Checking backend connection'
                  : backendStatus === 'degraded'
                    ? 'Backend reports degraded status'
                    : 'Spring Boot API unavailable'}
            </div>
          </div>

          <Dashboard backendStatus={backendStatus} />

          <footer className="dashboard-footer">
            <span>
              PRISM · Pattern Recognition in Integration System
              for Anomaly Monitoring
            </span>

            <span>Presentation Layer · V1</span>
          </footer>
        </main>
      </div>
    </div>
  )
}

export default App
