import { useState, useEffect, useRef } from 'react'
import { Play, Loader2, Info, Sun, Moon, Bug, Lightbulb, Code, X } from 'lucide-react'
import SettingsModal from './SettingsModal'
import { API_BASE } from './lib/api'

interface BugReport {
  description: string
  suggested_solution: string
  element_selector: string
  category?: string
  screenshot_crop?: string
}

interface CrawlResult {
  browser: string
  status: string
  screenshot?: string
  error?: string
  ai_error?: string
  ai_report?: BugReport[]
}

function browserLabel(b: string): string {
  if (b === 'webkit') return 'Safari'
  if (b === 'unknown') return 'Error'
  return b.charAt(0).toUpperCase() + b.slice(1)
}

function getErrorMessage(e: unknown, res?: Response): string {
  if (e instanceof TypeError && e.message.includes('fetch')) {
    return `Cannot reach the backend at ${API_BASE}. Make sure it is running.`
  }
  if (res) {
    if (res.status === 422) return 'Invalid URL or parameters — check the address and try again.'
    if (res.status >= 500) return 'The backend encountered an unexpected error. Check the backend logs.'
  }
  return e instanceof Error ? e.message : String(e)
}

function formatElapsed(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function App() {
  const [url, setUrl] = useState('')
  const [needsAuth, setNeedsAuth] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [result, setResult] = useState<CrawlResult[] | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  const [targetBrowser, setTargetBrowser] = useState('all')
  const [lightboxImage, setLightboxImage] = useState<string | null>(null)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('VL_DARK_MODE')
    return saved !== null ? saved === 'true' : (window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false)
  })

  // Active AI config — lazy-initialised from localStorage to avoid setState-in-effect
  const [activeProvider, setActiveProvider] = useState(
    () => localStorage.getItem('VL_PROVIDER') || ''
  )
  const [activeApiKey, setActiveApiKey] = useState(() => {
    const p = localStorage.getItem('VL_PROVIDER') || ''
    return p ? localStorage.getItem(`VL_API_KEY_${p}`) || '' : ''
  })
  const [activeModel, setActiveModel] = useState(() => {
    const p = localStorage.getItem('VL_PROVIDER') || ''
    return p ? localStorage.getItem(`VL_MODEL_${p}`) || '' : ''
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode)
  }, [isDarkMode])

  useEffect(() => {
    if (!isProcessing) return
    setElapsedSeconds(0)
    const start = Date.now()
    const id = setInterval(() => setElapsedSeconds(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(id)
  }, [isProcessing])

  const toggleDarkMode = () => {
    const next = !isDarkMode
    setIsDarkMode(next)
    document.documentElement.classList.toggle('dark', next)
    localStorage.setItem('VL_DARK_MODE', String(next))
  }

  const handleSaveSettings = (providerId: string, apiKey: string, modelId: string) => {
    setActiveProvider(providerId)
    setActiveApiKey(apiKey)
    setActiveModel(modelId)
    setShowSettings(false)
  }

  const isConfigured = !!(activeProvider && activeApiKey && activeModel)


  const getNativeBrowserType = () => {
    const ua = navigator.userAgent.toLowerCase()
    if (ua.includes('firefox')) return 'firefox'
    if (ua.includes('safari') && !ua.includes('chrome')) return 'webkit'
    return 'chromium'
  }

  const handleCancel = () => {
    abortRef.current?.abort()
    setIsProcessing(false)
    setStatusMessage('')
  }

  const handleAnalyze = async () => {
    if (!url) return alert('Please enter a URL first')
    if (!isConfigured) return alert('Please configure your AI provider in Settings first.')

    const ctrl = new AbortController()
    abortRef.current = ctrl
    setIsProcessing(true)
    setResult(null)
    setAnalysisError(null)

    try {
      if (needsAuth) {
        setStatusMessage('Waiting for authentication. Please log in and close the browser window...')
        const browserType = targetBrowser === 'all' ? getNativeBrowserType() : targetBrowser;
        const r = await fetch(`${API_BASE}/api/auth/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, browser_type: browserType }),
          signal: ctrl.signal,
        })
        if (!r.ok) throw Object.assign(new Error('Authentication request failed.'), { res: r })
        const d = await r.json()
        if (d.status !== 'success') throw new Error('Authentication failed or was cancelled.')
      }

      setStatusMessage('Starting browsers...')

      const res = await fetch(`${API_BASE}/api/crawl/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          max_pages: 5,
          target_browser: targetBrowser,
          provider_id: activeProvider,
          api_key: activeApiKey,
          model_id: activeModel,
        }),
        signal: ctrl.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        const detail = (err as { detail?: string | { msg: string }[] }).detail
        const message = Array.isArray(detail)
          ? detail.map(d => d.msg).join(', ')
          : detail || getErrorMessage(null, res)
        throw new Error(message)
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      setResult([])

      outer: while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          const payload = part.slice(6).trim()
          if (payload === '[DONE]') break outer
          try {
            const browserResult = JSON.parse(payload) as CrawlResult
            if (browserResult.status === 'retrying') {
              // Remove the previous (zero-bug) result for this browser so it shows as pending again
              setResult(prev => (prev ?? []).filter(r => r.browser !== browserResult.browser))
            } else {
              // Replace any existing result for this browser (handles retry replacement)
              setResult(prev => [
                ...(prev ?? []).filter(r => r.browser !== browserResult.browser),
                browserResult,
              ])
            }
          } catch {
            // malformed SSE chunk — skip rather than crash
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') return
      const attached = (e as { res?: Response }).res
      setAnalysisError(getErrorMessage(e, attached))
    } finally {
      setIsProcessing(false)
      setStatusMessage('')
    }
  }

  // Generic selectors that are too broad to use as a dedup anchor.
  const GENERIC_SELECTORS = new Set(['div', 'span', 'p', 'section', 'article', 'main', 'header', 'footer', 'body', 'html', 'ul', 'li', 'nav'])

  const normalizeDesc = (s: string) =>
    s.toLowerCase().trim().replace(/^(the|a|an)\s+/, '').replace(/[.!?,]+$/, '')

  const jaccardSimilarity = (a: string, b: string): number => {
    const sa = new Set(a.split(/\s+/).filter(Boolean))
    const sb = new Set(b.split(/\s+/).filter(Boolean))
    let intersection = 0
    sa.forEach(w => { if (sb.has(w)) intersection++ })
    const union = new Set([...sa, ...sb]).size
    return union === 0 ? 1 : intersection / union
  }

  const DEDUP_THRESHOLD = 0.65

  type BugEntry = { desc: string; solution: string; element: string; category: string; browsers: string[]; screenshot?: string }

  const getAggregatedBugs = (): BugEntry[] => {
    if (!result) return []

    // Primary index: "element_selector::symptom" — deterministic, DOM-based.
    const bySelector: Record<string, BugEntry> = {}
    // Fallback index: normalized description — for generic/ambiguous selectors.
    const byDesc: Record<string, BugEntry> = {}

    result.forEach((res) => {
      if (!res.ai_report || !Array.isArray(res.ai_report)) return
      res.ai_report.forEach((bug) => {
        const selector = bug.element_selector.toLowerCase().trim()
        const category = bug.category ?? 'other'
        const selectorKey = !GENERIC_SELECTORS.has(selector) && selector.length > 2
          ? `${selector}::${category}`
          : null
        const descKey = normalizeDesc(bug.description)

        // 1. Try primary key: same element + same symptom type = same bug.
        if (selectorKey && bySelector[selectorKey]) {
          if (!bySelector[selectorKey].browsers.includes(res.browser))
            bySelector[selectorKey].browsers.push(res.browser)
          return
        }

        // 2. Try fallback: description similarity within the same category (catches generic selectors).
        const existingDescKey = Object.keys(byDesc).find(
          k => byDesc[k]?.category === category && jaccardSimilarity(k, descKey) >= DEDUP_THRESHOLD
        )
        if (existingDescKey) {
          if (!byDesc[existingDescKey].browsers.includes(res.browser))
            byDesc[existingDescKey].browsers.push(res.browser)
          if (selectorKey) bySelector[selectorKey] = byDesc[existingDescKey]
          return
        }

        // 3. New unique bug.
        const entry: BugEntry = {
          desc: bug.description,
          solution: bug.suggested_solution,
          element: bug.element_selector,
          category,
          browsers: [res.browser],
          screenshot: bug.screenshot_crop ? `${API_BASE}/${bug.screenshot_crop}` : undefined,
        }
        if (selectorKey) bySelector[selectorKey] = entry
        byDesc[descKey] = entry
      })
    })

    return Object.values(byDesc)
  }

  const aggregatedBugs = getAggregatedBugs()

  const expectedBrowserCount = targetBrowser === 'all' ? 3 : 1
  const pendingBrowserCount = Math.max(0, expectedBrowserCount - (result ? result.length : 0))

  const erroredResults = result ? result.filter(r => r.status === 'error' || r.ai_error) : []
  const errorMessages = erroredResults.map(r => r.error ?? r.ai_error ?? '')
  const allErrorsSame = errorMessages.length > 0 && errorMessages.every(m => m === errorMessages[0])

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 p-8 flex flex-col transition-colors duration-200">
      <div className="max-w-6xl mx-auto w-full flex-grow">

        {/* Header */}
        <div className="flex justify-between items-center mb-12">
          <h1 className="text-3xl font-extrabold text-violet-600 dark:text-violet-400 tracking-tight">VisualLens</h1>
          <div className="flex items-center gap-3">
            {/* Config status badge */}
            {isConfigured ? (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50 rounded-full text-xs font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                {activeModel.split('/').pop()}
              </div>
            ) : (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800/50 rounded-full text-xs font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                Not configured
              </div>
            )}
            <button onClick={toggleDarkMode} className="p-2.5 rounded-full text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-200/50 dark:hover:bg-zinc-800 transition" aria-label="Toggle Dark Mode">
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button onClick={() => setShowSettings(true)} className="flex items-center gap-2 text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition font-semibold bg-zinc-100 dark:bg-zinc-900/50 px-4 py-2 rounded-full border border-zinc-200 dark:border-zinc-800">
              Settings
            </button>
          </div>
        </div>

        {/* Main card */}
        <div className="bg-white dark:bg-zinc-900/80 p-8 rounded-3xl shadow-sm border border-zinc-200 dark:border-zinc-800/80 mb-8 transition-colors backdrop-blur-xl">
          <label className="block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">Target URL</label>
          <input
            type="url"
            placeholder="https://example.com"
            className="w-full p-4 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50 text-zinc-900 dark:text-white mb-6 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition shadow-inner"
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
          />

          <div className="mb-8 flex items-center gap-3">
            <input type="checkbox" id="auth-checkbox" className="w-5 h-5 rounded border-zinc-300 dark:border-zinc-700 text-violet-600 cursor-pointer" checked={needsAuth} onChange={e => setNeedsAuth(e.target.checked)} />
            <label htmlFor="auth-checkbox" className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 select-none cursor-pointer">This page requires authentication</label>
            <div className="relative group flex items-center">
              <Info size={16} className="text-zinc-400 dark:text-zinc-500 cursor-help" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-64 p-4 bg-zinc-800 text-white text-xs leading-relaxed rounded-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 text-center pointer-events-none shadow-xl border border-zinc-700">
                If checked, a browser window will open for you to manually log in. Once you close it, the automated analysis will begin.
                <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-zinc-800 border-b border-r border-zinc-700 rotate-45"></div>
              </div>
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={isProcessing}
            className="w-full flex items-center justify-center gap-2 bg-violet-600 hover:bg-violet-700 dark:bg-violet-600 dark:hover:bg-violet-500 text-white p-4 rounded-2xl font-bold transition disabled:opacity-50 shadow-lg shadow-violet-500/20 dark:shadow-none"
          >
            {isProcessing ? <Loader2 className="animate-spin" /> : <Play size={20} className="fill-current" />}
            {isProcessing ? 'Processing...' : 'Start Analysis'}
          </button>
        </div>

        {/* Error banner */}
        {analysisError && (
          <div className="flex items-start gap-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800/50 text-rose-700 dark:text-rose-400 p-4 rounded-2xl mb-6">
            <span className="flex-1 text-sm font-medium">{analysisError}</span>
            <button onClick={() => setAnalysisError(null)} className="shrink-0 hover:opacity-70 transition" aria-label="Dismiss error">
              <X size={16} />
            </button>
          </div>
        )}

        {/* Loading overlay — shown only before first result streams in */}
        {isProcessing && (!result || result.length === 0) && (
          <div className="fixed inset-0 bg-zinc-900/60 dark:bg-black/80 backdrop-blur-md flex items-center justify-center z-50">
            <div className="bg-white dark:bg-zinc-900 p-10 rounded-3xl shadow-2xl max-w-md w-full text-center border border-zinc-200 dark:border-zinc-800">
              <Loader2 className="animate-spin w-12 h-12 text-violet-600 dark:text-violet-500 mx-auto mb-6" />
              <h3 className="text-2xl font-bold text-zinc-900 dark:text-white mb-2 tracking-tight">Analyzing...</h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 font-medium mb-1">{statusMessage}</p>
              <p className="text-xs text-zinc-400 dark:text-zinc-500 mb-1">This can take a few minutes, especially when analyzing multiple browser engines.</p>
              <p className="text-lg font-mono font-bold text-violet-600 dark:text-violet-400 mb-6 tabular-nums">{formatElapsed(elapsedSeconds)}</p>
              <button
                onClick={handleCancel}
                className="inline-flex items-center gap-2 mx-auto px-4 py-2 text-sm font-semibold text-zinc-500 dark:text-zinc-400 border border-zinc-300 dark:border-zinc-700 rounded-lg hover:border-rose-400 hover:text-rose-500 dark:hover:border-rose-500 dark:hover:text-rose-400 transition"
              >
                <X size={15} /> Cancel
              </button>
            </div>
          </div>
        )}

        {/* Sticky status chip — shown once results start streaming but other engines are still running */}
        {isProcessing && result && result.length > 0 && pendingBrowserCount > 0 && (
          <div className="sticky top-4 z-40 mb-6 flex items-center gap-3 pl-4 pr-5 py-2.5 rounded-full bg-zinc-900/90 dark:bg-violet-950/60 backdrop-blur-md border border-violet-500/30 shadow-lg shadow-violet-900/20 text-white w-fit mx-auto">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-violet-500"></span>
            </span>
            <span className="text-sm font-semibold tracking-tight">
              Still analyzing {pendingBrowserCount} more engine{pendingBrowserCount === 1 ? '' : 's'}…
            </span>
            <span className="text-sm font-mono tabular-nums text-violet-300">{formatElapsed(elapsedSeconds)}</span>
          </div>
        )}

        {/* Settings modal */}
        {showSettings && (
          <SettingsModal
            onClose={() => setShowSettings(false)}
            onSave={handleSaveSettings}
            initialProviderId={activeProvider}
            initialApiKey={activeApiKey}
            initialModelId={activeModel}
            targetBrowser={targetBrowser}
            onTargetBrowserChange={setTargetBrowser}
          />
        )}

        {/* Results */}
        {result !== null && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {!isProcessing && aggregatedBugs.length > 0 ? (
              <div className="bg-violet-50/50 dark:bg-violet-900/10 border border-violet-200 dark:border-violet-800/50 p-8 rounded-3xl mb-8">
                <h3 className="text-2xl font-extrabold text-violet-900 dark:text-violet-300 mb-6 flex items-center gap-3">
                  <Bug className="text-violet-600 dark:text-violet-400" /> Detected Visual Bugs
                </h3>
                <div className="space-y-4">
                  {aggregatedBugs.map((bug, idx) => (
                    <div key={idx} className="bg-white dark:bg-zinc-900 p-6 rounded-2xl border border-violet-100 dark:border-zinc-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
                      <div className="flex-grow">
                        <p className="text-lg font-bold text-zinc-900 dark:text-white mb-2">{bug.desc}</p>
                        <div className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400 mb-3">
                          <Code size={16} /> <span className="font-mono bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded-md">{bug.element}</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400 font-medium">
                          <Lightbulb size={16} /> {bug.solution}
                        </div>
                        {bug.screenshot && (
                          <button
                            onClick={() => setLightboxImage(bug.screenshot!)}
                            className="mt-4 block w-28 h-16 rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700 hover:border-violet-400 dark:hover:border-violet-500 hover:opacity-90 transition"
                          >
                            <img src={bug.screenshot} alt="element crop" className="w-full h-full object-cover" />
                          </button>
                        )}
                      </div>
                      <div className="flex flex-col gap-2 min-w-[120px]">
                        <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider text-center">Affected Engines</span>
                        <div className="flex gap-2 flex-wrap justify-center">
                          {bug.browsers.map((b: string) => (
                            <span key={b} className="px-3 py-1 bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 text-xs font-bold rounded-full capitalize border border-violet-200 dark:border-violet-800/50">
                              {browserLabel(b)}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : !isProcessing && result && result.every(r => r.status === 'success' && !r.ai_error) ? (
              <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800/50 p-8 rounded-3xl mb-8 flex items-center justify-center">
                <p className="text-lg font-bold text-emerald-700 dark:text-emerald-400">No visual bugs detected. The UI looks great across all tested engines.</p>
              </div>
            ) : !isProcessing ? (
              <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/50 p-6 rounded-3xl mb-8">
                <p className="text-base font-bold text-amber-700 dark:text-amber-400 mb-3">Analysis incomplete — one or more browsers returned errors.</p>
                {allErrorsSame ? (
                  <p className="mt-2 text-sm font-mono break-all text-amber-900 dark:text-amber-200">{errorMessages[0]}</p>
                ) : (
                  erroredResults.map(r => (
                    <div key={r.browser} className="mt-2 flex gap-2 text-sm text-amber-900 dark:text-amber-200">
                      <span className="font-semibold capitalize shrink-0">{browserLabel(r.browser)}:</span>
                      <span className="font-mono break-all">{r.error ?? r.ai_error}</span>
                    </div>
                  ))
                )}
              </div>
            ) : null}
          </div>
        )}
      </div>

      {lightboxImage && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-6"
          onClick={() => setLightboxImage(null)}
        >
          <div className="relative max-w-4xl max-h-full" onClick={e => e.stopPropagation()}>
            <button
              onClick={() => setLightboxImage(null)}
              className="absolute -top-3 -right-3 bg-zinc-800 dark:bg-zinc-700 text-white rounded-full p-1.5 hover:bg-zinc-600 dark:hover:bg-zinc-500 transition z-10"
              aria-label="Close"
            >
              <X size={14} />
            </button>
            <img src={lightboxImage} alt="element crop" className="max-w-full max-h-[85vh] rounded-xl shadow-2xl" />
          </div>
        </div>
      )}

      <footer className="mt-12 py-8 flex justify-center border-t border-zinc-200 dark:border-zinc-800/80">
        <a href="https://github.com/b0ir/visual-lens" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300 transition text-sm font-semibold">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>
          b0ir/visual-lens
        </a>
      </footer>
    </div>
  )
}

export default App
