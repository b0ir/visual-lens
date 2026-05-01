import { useState } from 'react'
import { Settings, Play, Loader2, Info, X } from 'lucide-react'

function App() {
  const [url, setUrl] = useState('')
  const [needsAuth, setNeedsAuth] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [result, setResult] = useState<any>(null)
  
  // Settings State
  const [showSettings, setShowSettings] = useState(false)
  const [targetBrowser, setTargetBrowser] = useState('all')

  const handleAnalyze = async () => {
    if (!url) return alert("Please enter a URL first");
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
      
      const crawlRes = await fetch('http://localhost:8000/api/crawl/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, max_pages: 5, target_browser: targetBrowser })
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

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8 flex flex-col">
      <div className="max-w-5xl mx-auto w-full flex-grow">
        <div className="flex justify-between items-center mb-12">
          <h1 className="text-3xl font-bold text-blue-600 flex items-center gap-2">
            VisualLens
          </h1>
          <div className="flex items-center gap-6">
            <button 
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-2 text-slate-500 hover:text-slate-900 transition font-medium"
            >
              <Settings size={20} /> Settings
            </button>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8">
          <label className="block text-sm font-medium text-slate-700 mb-2">Target URL</label>
          <input 
            type="url" 
            placeholder="https://example.com"
            className="w-full p-4 rounded-xl border border-slate-200 mb-4 focus:ring-2 focus:ring-blue-500 outline-none transition"
            value={url}
            onChange={e => setUrl(e.target.value)}
          />

          <div className="mb-6 flex items-center gap-2">
            <input 
              type="checkbox" 
              id="auth-checkbox"
              className="w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
              checked={needsAuth}
              onChange={(e) => setNeedsAuth(e.target.checked)}
            />
            <label htmlFor="auth-checkbox" className="text-sm font-medium text-slate-700 select-none cursor-pointer">
              This page requires authentication
            </label>
            <div className="relative group flex items-center">
              <Info size={16} className="text-slate-400 cursor-help" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 text-center pointer-events-none shadow-xl">
                If checked, a browser window will open for you to manually log in. Once you close it, the automated analysis will begin.
                <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 rotate-45"></div>
              </div>
            </div>
          </div>
          
          <button 
            onClick={handleAnalyze}
            disabled={isProcessing}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-xl font-medium transition disabled:opacity-50 shadow-md shadow-blue-200"
          >
            {isProcessing ? <Loader2 className="animate-spin" /> : <Play size={20} />}
            {isProcessing ? 'Processing...' : 'Start Analysis'}
          </button>
        </div>

        {/* Loading Overlay State */}
        {isProcessing && statusMessage && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50">
             <div className="bg-white p-8 rounded-2xl shadow-2xl max-w-md w-full text-center border border-slate-200">
                <Loader2 className="animate-spin w-12 h-12 text-blue-600 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-slate-900 mb-2">Analyzing...</h3>
                <p className="text-sm text-slate-600 font-medium">{statusMessage}</p>
             </div>
          </div>
        )}

        {/* Settings Modal */}
        {showSettings && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50">
             <div className="bg-white p-6 rounded-2xl shadow-2xl max-w-sm w-full border border-slate-200 relative">
                <button 
                  onClick={() => setShowSettings(false)}
                  className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 transition"
                >
                  <X size={20} />
                </button>
                <h3 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
                  <Settings size={20} /> Settings
                </h3>
                
                <div className="mb-6">
                  <label className="block text-sm font-medium text-slate-700 mb-2">Target Browsers</label>
                  <select 
                    className="w-full p-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none transition bg-slate-50"
                    value={targetBrowser}
                    onChange={(e) => setTargetBrowser(e.target.value)}
                  >
                    <option value="all">All Browsers (Parallel)</option>
                    <option value="chromium">Chromium</option>
                    <option value="firefox">Firefox</option>
                    <option value="webkit">Safari (WebKit)</option>
                  </select>
                </div>

                <button 
                  onClick={() => setShowSettings(false)}
                  className="w-full bg-slate-900 hover:bg-slate-800 text-white p-3 rounded-xl font-medium transition"
                >
                  Done
                </button>
             </div>
          </div>
        )}

        {/* Result Grid */}
        {result && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold">Analysis Results</h2>
            <div className={`grid grid-cols-1 ${result.length > 1 ? 'md:grid-cols-3' : 'max-w-md'} gap-6`}>
              {result.map((res: any, idx: number) => (
                <div key={idx} className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
                  <div className="flex items-center justify-between mb-4">
                    <span className="px-3 py-1 bg-slate-100 text-slate-700 text-sm font-semibold rounded-full capitalize flex items-center gap-2">
                      {res.browser === 'webkit' ? 'Safari' : res.browser}
                    </span>
                    {res.status === 'success' ? (
                       <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">Success</span>
                    ) : (
                       <span className="text-xs font-bold text-red-600 bg-red-50 px-2 py-1 rounded-full">Error</span>
                    )}
                  </div>
                  
                  {res.screenshot && (
                    <img src={`http://localhost:8000/${res.screenshot}`} alt={`${res.browser} Screenshot`} className="w-full h-auto rounded-xl border border-slate-200 mb-4 object-cover" />
                  )}
                  
                  {res.error && (
                    <div className="text-sm text-red-600 bg-red-50 p-3 rounded-xl mb-4">
                      {res.error}
                    </div>
                  )}

                  <div className="bg-slate-900 text-green-400 p-3 rounded-xl overflow-x-auto text-xs h-32">
                    <pre>{res.dom_snippet ? res.dom_snippet + '...' : 'No DOM captured.'}</pre>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Future aggregated AI Bug report will go here */}
            <div className="bg-blue-50 border border-blue-200 p-6 rounded-2xl mb-8">
               <h3 className="text-lg font-bold text-blue-900 mb-2">Aggregate AI Report (Preview)</h3>
               <p className="text-sm text-blue-700">Once the AI Provider is integrated, if a bug is found across multiple engines, it will be listed here as: <strong>"Bug found in: Chromium, Firefox"</strong></p>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-auto py-6 flex justify-center border-t border-slate-200">
        <a 
          href="https://github.com/b0ir/visual-lens" 
          target="_blank" 
          rel="noreferrer" 
          className="flex items-center gap-1.5 text-slate-400 hover:text-slate-600 transition text-sm font-medium"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg> 
          b0ir/visual-lens
        </a>
      </footer>
    </div>
  )
}

export default App
