import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

/* eslint-disable @typescript-eslint/no-explicit-any */
export type Row = Record<string, any>
export type Driver = { factor: string; points: number; detail: string }
export type Portfolio = {
  source: string; as_of: string; n_customers: number; pct_high_risk: number; premium_at_risk: number
  expected_premium_loss: number; total_premium: number; avg_sentiment: number; n_transcripts: number
  risk_bands: Record<string, number>; intents: Record<string, number>; actions: Record<string, number>
  risk_histogram: { bucket: string; count: number }[]
}

export type Store = {
  meta: Row; portfolio: Portfolio
  customers: Row[]; nba: Row[]
  c360ById: Map<string, Row>; nbaById: Map<string, Row>
  insightsByCust: Map<string, Row[]>; insightById: Map<string, Row>
  policiesByCust: Map<string, Row[]>; claimsByCust: Map<string, Row[]>; paymentsByCust: Map<string, Row[]>
}

const Ctx = createContext<{ store: Store | null; error: string | null }>({ store: null, error: null })

const group = (rows: Row[]) => {
  const m = new Map<string, Row[]>()
  for (const r of rows) { const k = r.CUSTOMER_ID; if (!m.has(k)) m.set(k, []); m.get(k)!.push(r) }
  return m
}

const load = (name: string) =>
  fetch(`${import.meta.env.BASE_URL}data/${name}.json`, { cache: 'no-cache' }).then((r) => {
    if (!r.ok) throw new Error(`${name}: ${r.status}`)
    return r.json()
  })

export function DataProvider({ children }: { children: ReactNode }) {
  const [store, setStore] = useState<Store | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    Promise.all(['meta', 'portfolio', 'customers_360', 'next_best_actions', 'interaction_insights', 'policies', 'claims', 'payments'].map(load))
      .then(([meta, portfolio, customers, nba, ins, pol, clm, pay]) => {
        setStore({
          meta, portfolio, customers, nba,
          c360ById: new Map(customers.map((c: Row) => [c.CUSTOMER_ID, c])),
          nbaById: new Map(nba.map((c: Row) => [c.CUSTOMER_ID, c])),
          insightsByCust: group(ins), insightById: new Map(ins.map((i: Row) => [i.TRANSCRIPT_ID, i])),
          policiesByCust: group(pol), claimsByCust: group(clm), paymentsByCust: group(pay),
        })
      })
      .catch((e) => setError(String(e)))
  }, [])
  const v = useMemo(() => ({ store, error }), [store, error])
  return <Ctx.Provider value={v}>{children}</Ctx.Provider>
}

export const useStore = () => useContext(Ctx)

export const inr = (n: number | null | undefined, compact = true) => {
  if (n == null || isNaN(n)) return '—'
  if (compact) {
    if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
    if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  }
  return `₹${Math.round(n).toLocaleString('en-IN')}`
}
export const fmtDate = (s?: string | null) =>
  s ? new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

export const bandColor = (b?: string) => (b === 'High' ? '#ff5c6c' : b === 'Medium' ? '#ffb547' : '#34d399')
export const healthColor = (h: 'good' | 'warn' | 'bad') => (h === 'bad' ? '#ff5c6c' : h === 'warn' ? '#ffb547' : '#34d399')

export const INTENT_COLORS: Record<string, string> = {
  cancellation_intent: '#ff5c6c', claim_issue: '#ffb547', price_concern: '#f472b6',
  general_service: '#94a3b8', service_praise: '#34d399', upsell_interest: '#38d9f5',
}
export const intentLabel = (s: string) => s?.replace(/_/g, ' ') ?? ''
