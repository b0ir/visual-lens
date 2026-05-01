import { useState, useEffect } from 'react'
import { Settings, Play, Loader2, Info, X, Sun, Moon, Bug, Lightbulb, Code } from 'lucide-react'

function App() {
  const [url, setUrl] = useState('')
  const [needsAuth, setNeedsAuth] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [result, setResult] = useState<any>(null)
  
  // Settings State
  const [showSettings, setShowSettings] = useState(false)
  const [targetBrowser, setTargetBrowser] = useState('all')
  
  // Dynamic Models State
  const [providerModels, setProviderModels] = useState<Record<string, { id: string, name: string }[]>>({})
  
  // AI Settings State
  const [provider, setProvider] = useState('')
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({ gemini: '', openai: '', anthropic: '', deepseek: '', nvidia: '' })
  const [aiModel, setAiModel] = useState('')
  const [isCustomModel, setIsCustomModel] = useState(false)

  // Dark Mode State
  const [isDarkMode, setIsDarkMode] = useState(false)

  useEffect(() => {
    // Fetch dynamic models from backend
    fetch('http://localhost:8000/api/models')
      .then(res => res.json())
      .then(data => {
         setProviderModels(data);
         
         // After models load, initialize settings
         const savedKeys = {
           gemini: localStorage.getItem('GEMINI_API_KEY') || '',
           openai: localStorage.getItem('OPENAI_API_KEY') || '',
           anthropic: localStorage.getItem('ANTHROPIC_API_KEY') || '',
           deepseek: localStorage.getItem('DEEPSEEK_API_KEY') || '',
           nvidia: localStorage.getItem('NVIDIA_API_KEY') || ''
         };
         const savedProvider = localStorage.getItem('AI_PROVIDER') || '';
         const savedModel = localStorage.getItem('AI_MODEL') || '';
         
         setApiKeys(savedKeys);
         setProvider(savedProvider);
         setAiModel(savedModel);

         // Check if the saved model is a custom one not in the list
         if (savedProvider && savedModel && data[savedProvider]) {
            const isKnownModel = data[savedProvider].some((m: any) => m.id === savedModel);
            if (!isKnownModel) {
               setIsCustomModel(true);
            }
         }
      })
      .catch(err => console.error("Failed to load models configuration", err));

    // Init Theme
    if (document.documentElement.classList.contains('dark') || 
       (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDarkMode(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const saveSettings = () => {
    localStorage.setItem('GEMINI_API_KEY', apiKeys.gemini);
    localStorage.setItem('OPENAI_API_KEY', apiKeys.openai);
    localStorage.setItem('ANTHROPIC_API_KEY', apiKeys.anthropic);
    localStorage.setItem('DEEPSEEK_API_KEY', apiKeys.deepseek);
    localStorage.setItem('NVIDIA_API_KEY', apiKeys.nvidia);
    localStorage.setItem('AI_PROVIDER', provider);
    localStorage.setItem('AI_MODEL', aiModel);
    setShowSettings(false);
  }

  const toggleDarkMode = () => {
    const willBeDark = !isDarkMode;
    setIsDarkMode(willBeDark);
    if (willBeDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const handleAnalyze = async () => {
    if (!url) return alert("Please enter a URL first");
    if (!provider || !aiModel || !apiKeys[provider]) {
      return alert("Please configure your AI Provider, API Key, and Model in Settings before running an analysis.");
    }

    setIsProcessing(true);
    setResult(null);
    
    try {
      if (needsAuth) {
        setStatusMessage("Waiting for authentication. Please log in using the opened browser window and close it when done...");
        const authRes = await fetch('http://localhost:8000/api/auth/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        const authData = await authRes.json();
        if (authData.status !== 'success') {
          throw new Error("Authentication failed or was cancelled.");
        }
      }

      const browserMsg = targetBrowser === 'all' ? 'Chromium, Firefox, and WebKit' : targetBrowser;
      setStatusMessage(`Running automated analysis on ${browserMsg}...`);
      
      const payload = {
        url,
        max_pages: 5,
        target_browser: targetBrowser,
        ai_model: aiModel,
        api_keys: {
          "GEMINI_API_KEY": apiKeys.gemini,
          "OPENAI_API_KEY": apiKeys.openai,
          "ANTHROPIC_API_KEY": apiKeys.anthropic,
          "DEEPSEEK_API_KEY": apiKeys.deepseek,
          "NVIDIA_API_KEY": apiKeys.nvidia
        }
      };

      const crawlRes = await fetch('http://localhost:8000/api/crawl/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const crawlData = await crawlRes.json();
      setResult(crawlData.results);
    } catch (error) {
      console.error(error);
      alert("Error during the process. Check console for details.");
    } finally {
      setIsProcessing(false);
      setStatusMessage("");
    }
  }

  const getAggregatedBugs = () => {
    if (!result) return [];
    const bugMap: Record<string, { desc: string, solution: string, element: string, browsers: string[] }> = {};
    
    result.forEach((res: any) => {
      if (res.ai_report && Array.isArray(res.ai_report)) {
        res.ai_report.forEach((bug: any) => {
          if (!bugMap[bug.description]) {
            bugMap[bug.description] = {
              desc: bug.description,
              solution: bug.suggested_solution,
              element: bug.element_selector,
              browsers: [res.browser]
            };
          } else if (!bugMap[bug.description].browsers.includes(res.browser)) {
            bugMap[bug.description].browsers.push(res.browser);
          }
        });
      }
    });
    return Object.values(bugMap);
  };

  const aggregatedBugs = getAggregatedBugs();

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 p-8 flex flex-col transition-colors duration-200">
      <div className="max-w-6xl mx-auto w-full flex-grow">
        <div className="flex justify-between items-center mb-12">
          <h1 className="text-3xl font-extrabold text-violet-600 dark:text-violet-400 tracking-tight flex items-center gap-2">
            VisualLens
          </h1>
          <div className="flex items-center gap-4">
            <button 
              onClick={toggleDarkMode}
              className="p-2.5 rounded-full text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-200/50 dark:hover:bg-zinc-800 transition"
              aria-label="Toggle Dark Mode"
            >
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button 
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-2 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition font-medium bg-zinc-100 dark:bg-zinc-900/50 px-4 py-2 rounded-full border border-zinc-200 dark:border-zinc-800"
            >
              <Settings size={18} /> Settings
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900/80 p-8 rounded-3xl shadow-sm border border-zinc-200 dark:border-zinc-800/80 mb-8 transition-colors backdrop-blur-xl">
          <label className="block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">Target URL</label>
          <input 
            type="url" 
            placeholder="https://example.com"
            className="w-full p-4 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50 text-zinc-900 dark:text-white mb-6 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition shadow-inner"
            value={url}
            onChange={e => setUrl(e.target.value)}
          />

          <div className="mb-8 flex items-center gap-3">
            <input 
              type="checkbox" 
              id="auth-checkbox"
              className="w-5 h-5 rounded border-zinc-300 dark:border-zinc-700 bg-transparent text-violet-600 focus:ring-violet-500 cursor-pointer"
              checked={needsAuth}
              onChange={(e) => setNeedsAuth(e.target.checked)}
            />
            <label htmlFor="auth-checkbox" className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 select-none cursor-pointer">
              This page requires authentication
            </label>
            <div className="relative group flex items-center">
              <Info size={16} className="text-zinc-400 dark:text-zinc-500 cursor-help" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-64 p-4 bg-zinc-800 dark:bg-zinc-800 text-white text-xs leading-relaxed rounded-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 text-center pointer-events-none shadow-xl border border-zinc-700">
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

        {/* Loading Overlay */}
        {isProcessing && statusMessage && (
          <div className="fixed inset-0 bg-zinc-900/60 dark:bg-black/80 backdrop-blur-md flex items-center justify-center z-50">
             <div className="bg-white dark:bg-zinc-900 p-10 rounded-3xl shadow-2xl max-w-md w-full text-center border border-zinc-200 dark:border-zinc-800">
                <Loader2 className="animate-spin w-12 h-12 text-violet-600 dark:text-violet-500 mx-auto mb-6" />
                <h3 className="text-2xl font-bold text-zinc-900 dark:text-white mb-2 tracking-tight">Analyzing...</h3>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 font-medium">{statusMessage}</p>
             </div>
          </div>
        )}

        {/* Settings Modal */}
        {showSettings && (
          <div className="fixed inset-0 bg-zinc-900/60 dark:bg-black/80 backdrop-blur-md flex items-center justify-center z-50">
             <div className="bg-white dark:bg-zinc-900 p-8 rounded-3xl shadow-2xl max-w-md w-full border border-zinc-200 dark:border-zinc-800 relative">
                <button 
                  onClick={() => setShowSettings(false)}
                  className="absolute top-6 right-6 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition"
                >
                  <X size={20} />
                </button>
                <h3 className="text-xl font-bold text-zinc-900 dark:text-white mb-8 flex items-center gap-2">
                  <Settings size={20} /> Configuration
                </h3>
                
                <div className="space-y-6 mb-8">
                  <div>
                    <label className="block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2">Target Browsers</label>
                    <select 
                      className="w-full p-3 rounded-2xl border border-zinc-200 dark:border-zinc-700 focus:ring-2 focus:ring-violet-500 outline-none transition bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white appearance-none cursor-pointer"
                      value={targetBrowser}
                      onChange={(e) => setTargetBrowser(e.target.value)}
                    >
                      <option value="all">All Browsers (Parallel)</option>
                      <option value="chromium">Chromium</option>
                      <option value="firefox">Firefox</option>
                      <option value="webkit">Safari (WebKit)</option>
                    </select>
                  </div>

                  <div className="border-t border-zinc-200 dark:border-zinc-800 pt-6">
                    <label className="block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2">1. Select AI Provider</label>
                    <select 
                      className="w-full p-3 rounded-xl border border-zinc-200 dark:border-zinc-700 focus:ring-2 focus:ring-violet-500 outline-none transition bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white appearance-none cursor-pointer"
                      value={provider}
                      onChange={(e) => {
                        setProvider(e.target.value);
                        setAiModel(''); 
                        setIsCustomModel(false);
                      }}
                    >
                      <option value="" disabled>Select a provider...</option>
                      <option value="gemini">Google Gemini</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="deepseek">DeepSeek</option>
                      <option value="nvidia">NVIDIA NIM</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2 flex justify-between">
                      <span>2. API Key</span>
                      {!provider && <span className="text-xs text-zinc-400 font-normal">Select a provider first</span>}
                    </label>
                    <input 
                      type="password" 
                      className="w-full p-3 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white outline-none focus:ring-2 focus:ring-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      value={provider ? apiKeys[provider] : ''}
                      onChange={(e) => setApiKeys({...apiKeys, [provider]: e.target.value})}
                      placeholder="Enter API Key"
                      disabled={!provider}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2 flex justify-between">
                      <span>3. Vision Model</span>
                      {(!provider || !apiKeys[provider]) && <span className="text-xs text-zinc-400 font-normal">Enter key first</span>}
                    </label>
                    
                    {!isCustomModel ? (
                      <select 
                        className="w-full p-3 rounded-xl border border-zinc-200 dark:border-zinc-700 focus:ring-2 focus:ring-violet-500 outline-none transition bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        value={aiModel}
                        onChange={(e) => {
                          if (e.target.value === 'custom') {
                            setIsCustomModel(true);
                            setAiModel('');
                          } else {
                            setAiModel(e.target.value);
                          }
                        }}
                        disabled={!provider || !apiKeys[provider]}
                      >
                        <option value="" disabled>Select a model...</option>
                        {provider && providerModels[provider]?.map((m: any) => (
                          <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                        <option value="custom" className="font-bold text-violet-600 dark:text-violet-400">
                          -- Type Custom Model ID --
                        </option>
                      </select>
                    ) : (
                      <div className="flex gap-2">
                        <input 
                          type="text" 
                          className="flex-grow p-3 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-white outline-none focus:ring-2 focus:ring-violet-500"
                          value={aiModel}
                          onChange={(e) => setAiModel(e.target.value)}
                          placeholder="e.g. provider/model-name"
                          autoFocus
                        />
                        <button 
                          onClick={() => {
                            setIsCustomModel(false);
                            setAiModel('');
                          }}
                          className="px-4 bg-zinc-200 hover:bg-zinc-300 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-xl font-medium transition"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <button 
                  onClick={saveSettings}
                  className="w-full bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white dark:text-zinc-900 text-white p-4 rounded-2xl font-bold transition"
                >
                  Save Settings
                </button>
             </div>
          </div>
        )}

        {/* Result Grid */}
        {result && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-2xl font-extrabold text-zinc-900 dark:text-white tracking-tight">Crawl Results</h2>
            <div className={`grid grid-cols-1 ${result.length > 1 ? 'md:grid-cols-3' : 'max-w-md'} gap-6`}>
              {result.map((res: any, idx: number) => (
                <div key={idx} className="bg-white dark:bg-zinc-900/80 p-5 rounded-3xl shadow-sm border border-zinc-200 dark:border-zinc-800 transition-colors backdrop-blur-xl flex flex-col">
                  <div className="flex items-center justify-between mb-5">
                    <span className="px-4 py-1.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-sm font-bold rounded-full capitalize flex items-center gap-2">
                      {res.browser === 'webkit' ? 'Safari' : res.browser}
                    </span>
                    {res.status === 'success' ? (
                       <span className="text-xs font-extrabold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1.5 rounded-full border border-emerald-200 dark:border-emerald-800/50">SUCCESS</span>
                    ) : (
                       <span className="text-xs font-extrabold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/30 px-3 py-1.5 rounded-full border border-rose-200 dark:border-rose-800/50">ERROR</span>
                    )}
                  </div>
                  
                  {res.screenshot && (
                    <img src={`http://localhost:8000/${res.screenshot}`} alt={`${res.browser} Screenshot`} className="w-full h-auto rounded-2xl border border-zinc-200 dark:border-zinc-700 mb-5 object-cover" />
                  )}
                  
                  {res.error && (
                    <div className="text-sm font-medium text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 p-4 rounded-2xl mb-5 border border-rose-100 dark:border-rose-900/50">
                      {res.error}
                    </div>
                  )}

                  <div className="mt-auto pt-4">
                     <p className="text-xs font-bold text-zinc-500 mb-2">RAW AI OUTPUT (Debug)</p>
                     <div className="bg-zinc-950 text-emerald-400 p-4 rounded-2xl overflow-y-auto text-xs h-32 border border-zinc-800 font-mono shadow-inner">
                       <pre>{res.ai_report ? JSON.stringify(res.ai_report, null, 2) : 'No AI report.'}</pre>
                     </div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Aggregated AI Bug Report */}
            {aggregatedBugs.length > 0 ? (
              <div className="bg-violet-50/50 dark:bg-violet-900/10 border border-violet-200 dark:border-violet-800/50 p-8 rounded-3xl mb-8">
                 <h3 className="text-2xl font-extrabold text-violet-900 dark:text-violet-300 mb-6 flex items-center gap-3">
                   <Bug className="text-violet-600 dark:text-violet-400" /> Detected Visual Bugs
                 </h3>
                 <div className="space-y-4">
                   {aggregatedBugs.map((bug: any, idx: number) => (
                     <div key={idx} className="bg-white dark:bg-zinc-900 p-6 rounded-2xl border border-violet-100 dark:border-zinc-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
                        <div className="flex-grow">
                          <p className="text-lg font-bold text-zinc-900 dark:text-white mb-2">{bug.desc}</p>
                          <div className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400 mb-3">
                             <Code size={16} /> <span className="font-mono bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded-md">{bug.element}</span>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400 font-medium">
                             <Lightbulb size={16} /> {bug.solution}
                          </div>
                        </div>
                        <div className="flex flex-col gap-2 min-w-[120px]">
                           <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider text-center">Affected Engines</span>
                           <div className="flex gap-2 flex-wrap justify-center">
                             {bug.browsers.map((b: string) => (
                               <span key={b} className="px-3 py-1 bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 text-xs font-bold rounded-full capitalize border border-violet-200 dark:border-violet-800/50">
                                 {b === 'webkit' ? 'Safari' : b}
                               </span>
                             ))}
                           </div>
                        </div>
                     </div>
                   ))}
                 </div>
              </div>
            ) : (
              <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800/50 p-8 rounded-3xl mb-8 flex items-center justify-center">
                 <p className="text-lg font-bold text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
                   No visual bugs detected. The UI looks great across all tested engines.
                 </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-12 py-8 flex justify-center border-t border-zinc-200 dark:border-zinc-800/80">
        <a 
          href="https://github.com/b0ir/visual-lens" 
          target="_blank" 
          rel="noreferrer" 
          className="flex items-center gap-2 text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300 transition text-sm font-semibold"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg> 
          b0ir/visual-lens
        </a>
      </footer>
    </div>
  )
}

export default App
