import React from 'react';
import { Layers, Database, Lock, GitMerge, Combine } from 'lucide-react';

export default function Architecture() {
  return (
    <div className="architecture-container" style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 className="display-large" style={{ color: 'var(--md-sys-color-primary)' }}>System Architecture</h1>
        <p className="headline-large" style={{ color: 'var(--md-sys-color-secondary)' }}>How HPGCS compresses LLM prompt corpora</p>
      </div>

      <div className="material-card" style={{ marginBottom: '3rem' }}>
        <h2 className="headline-large" style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Layers color="var(--md-sys-color-primary)" /> Track A: Corpus-Level Deduplication (Active)
        </h2>
        
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
          {['Prompt Input', 'Structural Parser', 'SHA-256 Hashing', 'Content Node Store', 'Blueprint Generation', 'SQLite Persistence'].map((step, i) => (
            <React.Fragment key={i}>
              <div style={{
                background: i === 3 ? 'var(--md-sys-color-primary)' : 'var(--md-sys-color-secondary-container)',
                color: i === 3 ? 'var(--md-sys-color-on-primary)' : 'var(--md-sys-color-on-secondary-container)',
                padding: '1rem 1.5rem',
                borderRadius: 'var(--md-sys-shape-corner-full)',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                boxShadow: 'var(--md-sys-elevation-1)'
              }}>
                {step}
              </div>
              {i < 5 && <div style={{ display: 'flex', alignItems: 'center', color: 'var(--md-sys-color-outline)' }}>➔</div>}
            </React.Fragment>
          ))}
        </div>
        
        <div style={{ marginTop: '2rem', padding: '1rem', background: 'var(--md-sys-color-surface-container-highest)', borderRadius: 'var(--md-sys-shape-corner-large)', textAlign: 'center' }}>
          <p className="label-large" style={{ color: 'var(--md-sys-color-primary)' }}>Reconstruction Pipeline</p>
          <p style={{ marginTop: '0.5rem' }}>Blueprint ➔ Resolve Nodes ➔ Decompress ➔ Verify SHA-256 ➔ Original Prompt</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
        <div className="material-card">
           <h2 className="headline-large" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <GitMerge color="var(--md-sys-color-tertiary)" /> Track B: Delta Compression
          </h2>
          <ol style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li><b>Prompt Input</b> arrives for cluster insertion.</li>
            <li><b>Similarity Matching</b> against existing stored centroids.</li>
            <li>If Match: Compute <b>Unified Diff</b>. If New: Store full text.</li>
            <li>Compress Delta payload using <b>Zstandard</b>.</li>
            <li>Store in SQLite `deltas` mapping.</li>
          </ol>
        </div>

        <div className="material-card">
           <h2 className="headline-large" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
             <Database color="var(--md-sys-color-secondary)" /> Storage Schema
          </h2>
          <div style={{ background: 'var(--md-sys-color-surface-container)', padding: '1rem', borderRadius: 'var(--md-sys-shape-corner-medium)', fontFamily: 'monospace', fontSize: '0.9rem', marginBottom: '1rem' }}>
             <strong style={{ color: 'var(--md-sys-color-primary)' }}>content_nodes</strong>(content_hash, compressed_data, original_size, compressed_size, component_type, ref_count)
          </div>
          <div style={{ background: 'var(--md-sys-color-surface-container)', padding: '1rem', borderRadius: 'var(--md-sys-shape-corner-medium)', fontFamily: 'monospace', fontSize: '0.9rem' }}>
             <strong style={{ color: 'var(--md-sys-color-tertiary)' }}>prompt_blueprints</strong>(prompt_id, original_hash, blueprint, original_size, marginal_bytes)
          </div>
        </div>
      </div>
      
      <div className="material-card" style={{ marginTop: '2rem', border: '2px solid var(--md-sys-color-tertiary-container)' }}>
         <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--md-sys-color-tertiary)' }}><Lock /> 100% Losslessness Guarantee</h3>
         <p style={{ marginTop: '1rem' }}>All reconstruction paths securely verify the rebuilt prompts natively via a strict SHA-256 hash match against the original payload. Zero information loss — guaranteed.</p>
      </div>
    </div>
  );
}
