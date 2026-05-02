import { useState, useEffect } from 'react'
import { Settings, X, CheckCircle, XCircle, Loader2, ExternalLink, ChevronRight } from 'lucide-react'

interface Provider {
  name: string
  description: string
  website: string
  vision_models: { id: string; name: string }[]
}

interface Props {
  onClose: () => void
  onSave: (providerId: string, apiKey: string, modelId: string) => void
  initialProviderId: string
  initialApiKey: string
  initialModelId: string
  targetBrowser: string
  onTargetBrowserChange: (v: string) => void
}

const PROVIDER_ICONS: Record<string, string> = {
  openai: '⬡',
  anthropic: '◆',
  gemini: '✦',
  deepseek: '◉',
  xai: '✕',
  openrouter: '⌘',
  nvidia: '🅝',
}

export default function SettingsModal({
  onClose, onSave, initialProviderId, initialApiKey, initialModelId, targetBrowser, onTargetBrowserChange
}: Props) {
  const [providers, setProviders] = useState<Record<string, Provider>>({})
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [selectedProvider, setSelectedProvider] = useState(initialProviderId)
  const [apiKey, setApiKey] = useState(initialApiKey)
  const [modelId, setModelId] = useState(initialModelId)
  const [isCustomModel, setIsCustomModel] = useState(false)
  const [verifyStatus, setVerifyStatus] = useState<'idle' | 'loading' | 'valid' | 'invalid'>('idle')
  const [verifyError, setVerifyError] = useState('')
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    fetch('http://localhost:8000/api/providers')
      .then(r => r.json())
      .then(setProviders)
      .catch(console.error)
  }, [])

  useEffect(() => {
    if (initialProviderId && initialApiKey) {
      setStep(3)
      setVerifyStatus('valid')
    } else if (initialProviderId) {
      setStep(2)
    }
  }, [initialProviderId, initialApiKey])

  const handleSelectProvider = (pid: string) => {
    setSelectedProvider(pid)
    const savedKey = localStorage.getItem(`VL_API_KEY_${pid}`) || ''
    setApiKey(savedKey)
    setVerifyStatus(savedKey ? 'valid' : 'idle')
    setModelId(localStorage.getItem(`VL_MODEL_${pid}`) || '')
    setStep(2)
  }

  const handleVerify = async () => {
    setVerifyStatus('loading')
    setVerifyError('')
    try {
      const res = await fetch('http://localhost:8000/api/providers/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: selectedProvider, api_key: apiKey }),
      })
      const data = await res.json()
      if (data.valid) {
        setVerifyStatus('valid')
        localStorage.setItem(`VL_API_KEY_${selectedProvider}`, apiKey)
        setStep(3)
      } else {
        setVerifyStatus('invalid')
        setVerifyError(data.error || 'Invalid key')
      }
    } catch {
      setVerifyStatus('invalid')
      setVerifyError('Could not reach backend')
    }
  }

  const handleSave = () => {
    if (!selectedProvider || !apiKey || !modelId) return
    localStorage.setItem('VL_PROVIDER', selectedProvider)
    localStorage.setItem(`VL_API_KEY_${selectedProvider}`, apiKey)
    localStorage.setItem(`VL_MODEL_${selectedProvider}`, modelId)
    onSave(selectedProvider, apiKey, modelId)
  }

  const currentProvider = providers[selectedProvider]
  const stepLabel = step === 1 ? 'Select Provider' : step === 2 ? 'Enter API Key' : 'Select Model'

  return (
    <div className="fixed inset-0 bg-zinc-900/60 dark:bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-zinc-900 rounded-3xl shadow-2xl w-full max-w-lg border border-zinc-200 dark:border-zinc-800 relative flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-100 dark:border-zinc-800 shrink-0">
          <div>
            <h3 className="text-lg font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Settings size={18} /> Configuration
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">Step {step} of 3 — {stepLabel}</p>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition">
            <X size={20} />
          </button>
        </div>

        {/* Step breadcrumbs */}
        <div className="flex items-center gap-1 px-6 pt-4 shrink-0">
          {([1, 2, 3] as const).map((s) => (
            <div key={s} className="flex items-center gap-1 flex-1">
              <div className={`h-1.5 flex-1 rounded-full transition-colors ${s <= step ? 'bg-violet-500' : 'bg-zinc-200 dark:bg-zinc-700'}`} />
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-6 space-y-4">

          {/* Browser selector always visible */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-2">Target Browsers</label>
            <select
              className="w-full p-3 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-violet-500 cursor-pointer"
              value={targetBrowser}
              onChange={e => onTargetBrowserChange(e.target.value)}
            >
              <option value="all">All Browsers (Parallel)</option>
              <option value="chromium">Chromium</option>
              <option value="firefox">Firefox</option>
              <option value="webkit">Safari (WebKit)</option>
            </select>
          </div>

          <div className="border-t border-zinc-100 dark:border-zinc-800 pt-4">

          {/* Step 1: Provider cards */}
          {step >= 1 && (
            <div className="mb-4">
              <label className="block text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-3">AI Provider</label>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(providers).map(([pid, p]) => (
                  <button
                    key={pid}
                    onClick={() => handleSelectProvider(pid)}
                    className={`p-3 rounded-2xl border text-left transition-all ${
                      selectedProvider === pid
                        ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20 ring-2 ring-violet-500/30'
                        : 'border-zinc-200 dark:border-zinc-700 hover:border-violet-300 dark:hover:border-violet-600 bg-zinc-50 dark:bg-zinc-800/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-lg leading-none">{PROVIDER_ICONS[pid] || '●'}</span>
                      {selectedProvider === pid && <CheckCircle size={14} className="text-violet-500" />}
                    </div>
                    <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">{p.name}</p>
                    <p className="text-xs text-zinc-400 mt-0.5 leading-tight">{p.description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: API Key */}
          {step >= 2 && selectedProvider && currentProvider && (
            <div className="mb-4 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">API Key for {currentProvider.name}</label>
                <a href={currentProvider.website} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1 text-xs text-violet-500 hover:text-violet-600 transition">
                  Get key <ExternalLink size={11} />
                </a>
              </div>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  className="w-full p-3 pr-20 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-violet-500"
                  value={apiKey}
                  onChange={e => { setApiKey(e.target.value); setVerifyStatus('idle') }}
                  placeholder="Paste your API key..."
                />
                <button
                  type="button"
                  onClick={() => setShowKey(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 font-medium"
                >
                  {showKey ? 'Hide' : 'Show'}
                </button>
              </div>

              <button
                onClick={handleVerify}
                disabled={!apiKey || verifyStatus === 'loading'}
                className="w-full p-3 rounded-xl text-sm font-semibold transition disabled:opacity-50 flex items-center justify-center gap-2
                  bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200"
              >
                {verifyStatus === 'loading' ? <><Loader2 size={15} className="animate-spin" /> Verifying...</>
                 : verifyStatus === 'valid' ? <><CheckCircle size={15} className="text-emerald-500" /> Key Verified</>
                 : verifyStatus === 'invalid' ? <><XCircle size={15} className="text-rose-500" /> Try Again</>
                 : <>Verify Key <ChevronRight size={15} /></>}
              </button>

              {verifyStatus === 'invalid' && verifyError && (
                <p className="text-xs text-rose-500 font-medium">{verifyError}</p>
              )}
            </div>
          )}

          {/* Step 3: Model selection */}
          {step >= 3 && selectedProvider && currentProvider && (
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Vision Model</label>

              {!isCustomModel ? (
                <div className="space-y-2">
                  {currentProvider.vision_models.map(m => (
                    <button
                      key={m.id}
                      onClick={() => setModelId(m.id)}
                      className={`w-full p-3 rounded-xl border text-left transition-all flex items-center justify-between ${
                        modelId === m.id
                          ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20 ring-2 ring-violet-500/30'
                          : 'border-zinc-200 dark:border-zinc-700 hover:border-violet-300 dark:hover:border-violet-600 bg-zinc-50 dark:bg-zinc-800/50'
                      }`}
                    >
                      <div>
                        <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">{m.name}</p>
                        <p className="text-xs text-zinc-400 font-mono">{m.id}</p>
                      </div>
                      {modelId === m.id && <CheckCircle size={16} className="text-violet-500 shrink-0" />}
                    </button>
                  ))}
                  <button
                    onClick={() => { setIsCustomModel(true); setModelId('') }}
                    className="w-full p-3 rounded-xl border border-dashed border-zinc-300 dark:border-zinc-600 text-xs text-zinc-400 hover:text-violet-500 hover:border-violet-400 transition"
                  >
                    + Use custom model ID
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <input
                    type="text"
                    autoFocus
                    className="w-full p-3 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-violet-500 font-mono"
                    value={modelId}
                    onChange={e => setModelId(e.target.value)}
                    placeholder="e.g. openai/gpt-4.1"
                  />
                  <button
                    onClick={() => { setIsCustomModel(false); setModelId(localStorage.getItem(`VL_MODEL_${selectedProvider}`) || '') }}
                    className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition"
                  >
                    Back to model list
                  </button>
                </div>
              )}
            </div>
          )}

          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
          <button
            onClick={handleSave}
            disabled={!selectedProvider || !apiKey || !modelId || verifyStatus !== 'valid'}
            className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-40 text-white p-4 rounded-2xl font-bold transition"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  )
}
