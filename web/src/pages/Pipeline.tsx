import { motion } from 'framer-motion'
import { Brain, Database, Layers, MonitorSmartphone, Target } from 'lucide-react'
import { Card } from '../components/ui'
import { useStore } from '../data'

const STEPS = [
  { icon: Database, title: 'RAW sources', skill: 'Snowflake RAW schema', body: 'Customers · policies · claims · payments · call transcripts', tags: ['Policy admin', 'Claims', 'Billing', 'Call centre'] },
  { icon: Layers, title: '$c360-unify', skill: 'CoCo skill 1', body: 'SQL views → CURATED.CUSTOMER_360, one row per customer with 60+ signals', tags: ['Snowflake SQL', 'AS_OF_DATE()'] },
  { icon: Brain, title: '$interaction-intel', skill: 'CoCo skill 2', body: 'Unstructured transcripts → sentiment, intent, 1-line summary (incremental)', tags: ['CORTEX.SENTIMENT', 'AI_CLASSIFY', 'AI_COMPLETE', 'Cortex Search'] },
  { icon: Target, title: '$next-best-action', skill: 'CoCo skill 3', body: 'Explainable 8-driver churn score + grounded action, reason, evidence, message', tags: ['APP.CHURN_RISK', 'APP.NEXT_BEST_ACTIONS', 'AI_COMPLETE'] },
  { icon: MonitorSmartphone, title: 'Command Center', skill: 'This app + Streamlit', body: 'Agents go from question to action in one screen', tags: ['React', 'Streamlit in Snowflake'] },
]

export default function Pipeline() {
  const { store } = useStore()
  return (
    <div className="space-y-5">
      <Card className="p-6">
        <div className="label">Architecture inside the product</div>
        <div className="mt-1 text-2xl font-extrabold text-white">Three modular Cortex Code CLI skills, chained on Snowflake</div>
        <div className="mt-1 text-sm text-slate-400">Each skill is a SKILL.md plus SQL, runnable alone or chained. Tables are the contract between them.</div>
      </Card>
      <div className="relative grid grid-cols-1 gap-4 lg:grid-cols-5">
        <svg className="pointer-events-none absolute inset-x-0 top-1/2 hidden h-2 w-full -translate-y-1/2 lg:block" preserveAspectRatio="none" viewBox="0 0 100 2">
          <line x1="2" y1="1" x2="98" y2="1" stroke="rgba(56,217,245,0.25)" strokeWidth="0.4" />
          <motion.line x1="2" y1="1" x2="98" y2="1" stroke="#38d9f5" strokeWidth="0.6" strokeDasharray="3 9" animate={{ strokeDashoffset: [0, -24] }} transition={{ repeat: Infinity, duration: 1.6, ease: 'linear' }} />
        </svg>
        {STEPS.map((s, i) => {
          const isSkill = s.title.startsWith('$')
          return (
            <motion.div key={s.title} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.15, duration: 0.5 }}
              className={`glass relative z-10 p-5 ${isSkill ? '!border-cyan-400/30 shadow-[0_0_40px_-12px_rgba(56,217,245,0.5)]' : ''}`}>
              <div className="flex items-center justify-between">
                <div className={`grid h-10 w-10 place-items-center rounded-xl ${isSkill ? 'bg-cyan-400/15 text-cyan-300' : 'bg-white/5 text-slate-300'}`}><s.icon size={20} /></div>
                <span className="font-mono text-[10.5px] text-slate-500">0{i + 1}</span>
              </div>
              <div className={`mt-3 font-mono text-[15px] font-bold ${isSkill ? 'text-cyan-300' : 'text-white'}`}>{s.title}</div>
              <div className="text-[11px] uppercase tracking-wider text-slate-500">{s.skill}</div>
              <div className="mt-2 text-[13px] leading-relaxed text-slate-300">{s.body}</div>
              <div className="mt-3 flex flex-wrap gap-1">{s.tags.map((t) => <span key={t} className="chip border-white/10 font-mono text-[10px] text-slate-400">{t}</span>)}</div>
            </motion.div>
          )
        })}
      </div>
      <Card className="p-5" delay={0.6}>
        <div className="label">Run provenance</div>
        <div className="mt-2 grid grid-cols-1 gap-3 font-mono text-[12px] text-slate-300 md:grid-cols-3">
          <div><span className="text-slate-500">source </span>{store?.meta?.source ?? '—'}</div>
          <div><span className="text-slate-500">as_of </span>{store?.meta?.as_of ?? '—'}</div>
          <div><span className="text-slate-500">generated_at </span>{store?.meta?.generated_at ?? '—'}</div>
        </div>
        {store?.meta?.note && <div className="mt-2 text-xs text-slate-500">{store.meta.note}</div>}
      </Card>
    </div>
  )
}
