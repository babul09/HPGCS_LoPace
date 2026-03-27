import React, { useState } from 'react';
import { PlayCircle, ShieldCheck } from 'lucide-react';

const MULTITURN_DATA = `System: You are a helpful AI assistant specialized in Python programming. Always provide code examples with detailed explanations.
User: How do I sort a dictionary by value?
---
System: You are a helpful AI assistant specialized in Python programming. Always provide code examples with detailed explanations.
User: Explain async/await in Python.
---
System: You are a coding assistant. Write clean, well-documented code.
User: Write a Fibonacci function.`;

export default function Demo() {
  const [compressing, setCompressing] = useState(false);
  const [results, setResults] = useState(null);

  const mockRun = () => {
    setCompressing(true);
    setTimeout(() => {
      setResults(true);
      setCompressing(false);
    }, 1200);
  };

  return (
    <div className="demo-container" style={{ animation: 'fadeIn 0.5s ease', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
      
      <div style={{ flex: '1 1 500px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        <div style={{ textAlign: 'left', marginBottom: '1rem' }}>
          <h1 className="display-large" style={{ color: 'var(--md-sys-color-primary)' }}>Try It Live</h1>
          <p className="headline-large" style={{ color: 'var(--md-sys-color-secondary)' }}>See corpus-level chunk deduplication resolving the marginal costs.</p>
        </div>

        <div className="material-card" style={{ padding: '1rem', background: '#202124' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 1rem', background: '#303134', borderRadius: '8px', marginBottom: '1rem', color: '#E8EAED', fontFamily: 'monospace' }}>
            <span>Input Prompts Payload</span>
            <span className="material-chip" style={{ background: '#5F6368', color: '#FFFFFF', padding: '0.1rem 0.5rem' }}>3 loaded</span>
          </div>
          <textarea 
            readOnly 
            value={MULTITURN_DATA} 
            style={{ 
              width: '100%', height: '300px', background: 'transparent', color: '#E8EAED', 
              border: 'none', resize: 'none', fontFamily: 'monospace', fontSize: '1rem', lineHeight: '1.5' 
            }}
          />
        </div>

        <button 
          className="material-button-primary" 
          style={{ width: '100%', justifyContent: 'center', padding: '1.5rem', fontSize: '1.25rem', opacity: compressing ? 0.7 : 1 }}
          onClick={mockRun}
          disabled={compressing}
        >
          {compressing ? 'Processing Tokens...' : <><PlayCircle size={28} /> Compress Corpus Sandbox</>}
        </button>
      </div>

      <div style={{ flex: '1 1 500px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
         <div className="material-card" style={{ flex: 1, minHeight: '400px', display: 'flex', flexDirection: 'column' }}>
            <h2 className="headline-large" style={{ marginBottom: '1.5rem' }}>Resolution Results</h2>
            
            {!results && !compressing && (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--md-sys-color-outline)' }}>
                <p>Awaiting corpus payload compression run...</p>
              </div>
            )}

            {compressing && (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--md-sys-color-primary)' }}>
                 <p className="headline-large" style={{ animation: 'pulse 1s infinite' }}>Extracting semantic components...</p>
              </div>
            )}

            {results && (
              <div style={{ animation: 'fadeIn 0.4s ease' }}>
                 
                 <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
                    <div style={{ flex: 1, background: 'var(--md-sys-color-surface-container-high)', padding: '1rem', borderRadius: 'var(--md-sys-shape-corner-medium)' }}>
                      <p className="label-large" style={{ color: 'var(--md-sys-color-primary)' }}>Prompt #1</p>
                      <p className="headline-large" style={{ margin: '0.5rem 0' }}>1,247 B ➔ <strong style={{color:'var(--md-sys-color-primary)'}}>312 B</strong></p>
                      <span className="material-chip" style={{ background: '#eaddff', color: '#21005d' }}><ShieldCheck size={16} style={{marginRight: '0.2rem'}}/> Hashes Match</span>
                    </div>
                    <div style={{ flex: 1, background: 'var(--md-sys-color-surface-container-high)', padding: '1rem', borderRadius: 'var(--md-sys-shape-corner-medium)' }}>
                      <p className="label-large" style={{ color: 'var(--md-sys-color-primary)' }}>Prompt #2</p>
                      <p className="headline-large" style={{ margin: '0.5rem 0' }}>1,198 B ➔ <strong style={{color:'var(--md-sys-color-tertiary)'}}>48 B</strong> <span style={{fontSize: '1rem', fontWeight: 400}}>(Marginal)</span></p>
                      <span className="material-chip" style={{ background: '#eaddff', color: '#21005d' }}><ShieldCheck size={16} style={{marginRight: '0.2rem'}}/> Hashes Match</span>
                    </div>
                    <div style={{ flex: 1, background: 'var(--md-sys-color-surface-container-high)', padding: '1rem', borderRadius: 'var(--md-sys-shape-corner-medium)' }}>
                      <p className="label-large" style={{ color: 'var(--md-sys-color-primary)' }}>Prompt #3</p>
                      <p className="headline-large" style={{ margin: '0.5rem 0' }}>987 B ➔ <strong style={{color:'var(--md-sys-color-primary)'}}>298 B</strong></p>
                      <span className="material-chip" style={{ background: '#eaddff', color: '#21005d' }}><ShieldCheck size={16} style={{marginRight: '0.2rem'}}/> Hashes Match</span>
                    </div>
                 </div>

                 <div style={{ background: 'var(--md-sys-color-surface-container-highest)', padding: '1.5rem', borderRadius: 'var(--md-sys-shape-corner-large)' }}>
                    <h3 className="label-large" style={{ marginBottom: '1rem', color: 'var(--md-sys-color-on-surface)' }}>Marginal Cost Insight</h3>
                    <p style={{ lineHeight: '1.6' }}>
                      Notice how <b>Prompt #2 costs only 48 bytes</b>. Because its system instructions were identical to Prompt #1, the model simply mapped a <i>reference hash</i> into the blueprint array. The only new bytes stored physically corresponded to the unique user query "Explain async/await in Python."
                    </p>
                 </div>

              </div>
            )}
         </div>
      </div>
    </div>
  );
}
