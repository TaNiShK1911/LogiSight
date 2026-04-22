import { Link } from 'react-router-dom';
import {
  Zap,
  ArrowRight,
  CheckCircle2,
  FileSearch,
  GitMerge,
  BarChart3,
  MessageSquare,
  ShieldCheck,
  TrendingUp,
  Users,
  Globe,
  ChevronRight,
} from 'lucide-react';

const HOW_IT_WORKS = [
  {
    step: '01',
    title: 'Forwarder Submits Quote',
    desc: 'Freight forwarders submit quotes using their own charge terminology — no need to learn your internal naming.',
    color: 'text-sky-400',
    border: 'border-sky-800',
    bg: 'bg-sky-950/30',
  },
  {
    step: '02',
    title: 'AI Maps to Charge Master',
    desc: 'A three-tier pipeline (synonym dictionary → vector similarity → LLM fallback) maps every charge to your internal standard.',
    color: 'text-violet-400',
    border: 'border-violet-800',
    bg: 'bg-violet-950/30',
  },
  {
    step: '03',
    title: 'Client Reviews & Accepts',
    desc: 'You see quotes in your own nomenclature. Low-confidence mappings are surfaced for one-click correction.',
    color: 'text-emerald-400',
    border: 'border-emerald-800',
    bg: 'bg-emerald-950/30',
  },
  {
    step: '04',
    title: 'Invoice Uploaded & Analysed',
    desc: 'The forwarder uploads the PDF invoice. OCR extraction + the same mapping pipeline runs automatically.',
    color: 'text-amber-400',
    border: 'border-amber-800',
    bg: 'bg-amber-950/30',
  },
  {
    step: '05',
    title: 'Anomalies Flagged',
    desc: 'Amount mismatches, rate changes, unexpected charges, and duplicates are detected and surfaced instantly.',
    color: 'text-red-400',
    border: 'border-red-800',
    bg: 'bg-red-950/30',
  },
  {
    step: '06',
    title: 'Copilot Answers Questions',
    desc: 'Ask plain English questions about your freight spend. LogiSight translates to SQL and returns precise answers.',
    color: 'text-cyan-400',
    border: 'border-cyan-800',
    bg: 'bg-cyan-950/30',
  },
];

const ROLES = [
  {
    title: 'For Buyers & Importers',
    subtitle: 'Take control of your freight spend',
    Icon: ShieldCheck,
    color: 'text-emerald-400',
    border: 'border-emerald-800',
    bg: 'bg-emerald-950/20',
    points: [
      'Receive quotes mapped to your Charge Master automatically',
      'Review low-confidence mappings with one-click correction',
      'Accept or reject quotes with optional notes to forwarders',
      'Compare every invoice charge against the approved quote',
      'Get anomaly flags on mismatches, unexpected charges, and duplicates',
      'Query your entire freight history in plain English via Copilot',
    ],
  },
  {
    title: 'For Freight Forwarders',
    subtitle: 'Submit quotes and invoices your way',
    Icon: Globe,
    color: 'text-sky-400',
    border: 'border-sky-800',
    bg: 'bg-sky-950/20',
    points: [
      'Use your own charge terminology — no mapping required on your end',
      'Submit structured quotes with dynamic charge lines',
      'Track quote status and read rejection notes in real time',
      'Upload PDF invoices directly against accepted quotes',
      'Clean, simple interface — no freight audit complexity exposed',
    ],
  },
  {
    title: 'For Platform Administrators',
    subtitle: 'Full control over the platform',
    Icon: Users,
    color: 'text-amber-400',
    border: 'border-amber-800',
    bg: 'bg-amber-950/20',
    points: [
      'Create and manage client and forwarder companies',
      'Provision first admin users for each company',
      'Activate or deactivate companies at any time',
      'Cross-company visibility for platform-level oversight',
      'Single database, multi-tenant architecture',
    ],
  },
];

const FEATURES = [
  { Icon: FileSearch, title: 'Veryfi OCR Extraction', desc: 'Purpose-built freight invoice extraction from any PDF format.' },
  { Icon: GitMerge, title: 'Three-Tier Mapping', desc: 'Synonym dictionary, vector similarity, and LLM fallback for near-100% accuracy.' },
  { Icon: BarChart3, title: 'Anomaly Detection', desc: 'Six flag types including amount mismatch, unexpected charges, and duplicates.' },
  { Icon: MessageSquare, title: 'LangChain Copilot', desc: 'Natural language to SQL — ask any question about your freight data.' },
  { Icon: TrendingUp, title: 'Audit Dashboard', desc: 'Charge-level comparison table with confidence badges and anomaly flags.' },
  { Icon: ShieldCheck, title: 'Role-Based Access', desc: 'Strict data isolation — forwarders never see your internal Charge Master.' },
];

export function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">LogiSight</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              to="/login"
              className="text-sm text-slate-400 hover:text-slate-100 transition-colors"
            >
              Sign in
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-white text-sm font-medium transition-colors"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </nav>

      <section className="relative pt-32 pb-24 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-sky-900/20 via-transparent to-transparent pointer-events-none" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-sky-600/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-sky-800/60 bg-sky-950/40 text-sky-400 text-xs font-medium mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
            AI-Powered Freight Audit Intelligence
          </div>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6 leading-tight">
            Stop Overpaying on
            <br />
            <span className="text-sky-400">Freight Invoices</span>
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-10">
            LogiSight automatically maps forwarder charge names to your internal standards,
            detects anomalies at the charge level, and lets you interrogate your entire
            freight spend in plain English.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-semibold transition-colors shadow-lg shadow-sky-500/20"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-lg border border-slate-700 hover:border-slate-600 text-slate-300 hover:text-white font-medium transition-colors"
            >
              See How It Works
            </a>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="py-24 px-6 border-t border-slate-800/60">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">How It Works</h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              From quote submission to anomaly detection — fully automated, end to end.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {HOW_IT_WORKS.map(({ step, title, desc, color, border, bg }) => (
              <div
                key={step}
                className={`relative p-6 rounded-xl border ${border} ${bg} flex flex-col gap-3`}
              >
                <span className={`text-xs font-mono font-bold ${color} opacity-60`}>STEP {step}</span>
                <div className="flex items-start gap-3">
                  <ChevronRight className={`w-5 h-5 mt-0.5 flex-shrink-0 ${color}`} />
                  <div>
                    <h3 className="font-semibold text-slate-100 mb-1">{title}</h3>
                    <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-24 px-6 border-t border-slate-800/60 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">Built for Your Role</h2>
            <p className="text-slate-400">Different personas, different needs — all served precisely.</p>
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {ROLES.map(({ title, subtitle, Icon, color, border, bg, points }) => (
              <div key={title} className={`p-6 rounded-xl border ${border} ${bg}`}>
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-10 h-10 rounded-lg bg-slate-900 border ${border} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${color}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-100">{title}</h3>
                    <p className={`text-xs ${color}`}>{subtitle}</p>
                  </div>
                </div>
                <ul className="space-y-2.5">
                  {points.map((p) => (
                    <li key={p} className="flex items-start gap-2">
                      <CheckCircle2 className={`w-4 h-4 mt-0.5 flex-shrink-0 ${color}`} />
                      <span className="text-sm text-slate-300">{p}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-24 px-6 border-t border-slate-800/60">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">Platform Capabilities</h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map(({ Icon, title, desc }) => (
              <div key={title} className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 flex gap-4">
                <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-5 h-5 text-sky-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-100 mb-1">{title}</h3>
                  <p className="text-sm text-slate-400">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-24 px-6 border-t border-slate-800/60">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to audit smarter?</h2>
          <p className="text-slate-400 mb-8">
            Automate your freight invoice reconciliation with AI-powered charge mapping and anomaly detection.
          </p>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-semibold transition-colors shadow-lg shadow-sky-500/20"
          >
            Get Started Now <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-800 py-8 px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-sky-500 flex items-center justify-center">
              <Zap className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-semibold text-slate-300">LogiSight</span>
          </div>
          <p className="text-xs text-slate-600">
            &copy; {new Date().getFullYear()} LogiSight. AI-Powered Freight Audit Intelligence.
          </p>
        </div>
      </footer>
    </div>
  );
}
