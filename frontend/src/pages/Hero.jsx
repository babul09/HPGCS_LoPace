import React from 'react';
import { Database, GitCompare, BookOpen, ArrowRight, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Hero() {
  return (
    <div className="hero-container">
      <section className="hero-section">
        <h1 className="display-large hero-title">HPGCS</h1>
        <h2 className="headline-large hero-subtitle">
          Lossless Corpus-Aware Prompt Compression for LLM Workloads
        </h2>
        <p className="body-large" style={{ marginBottom: '2.5rem', color: 'var(--md-sys-color-secondary)' }}>
          Exploiting structural redundancy in production prompt corpora — where system instructions, 
          tool schemas, and RAG context blocks repeat across thousands of prompts — to achieve 
          compression ratios far beyond per-prompt methods.
        </p>
        
        <div className="hero-actions">
          <Link to="/demo" className="material-button-primary">
            Try Live Demo <ArrowRight size={20} />
          </Link>
          <a href="https://github.com/babul09/HPGCS_LoPace" className="material-button-tertiary">
            <FileText size={20} /> View Source
          </a>
        </div>
      </section>

      <section className="features-grid">
        <div className="material-card feature-card">
          <div className="feature-icon-wrapper">
            <Database size={32} />
          </div>
          <h3 className="feature-title">Corpus Deduplication</h3>
          <p className="body-large">
            6.2× compression ratio via content-addressable component storage. 
            Shared prompt components are extracted, hashed with SHA-256, and stored only once.
          </p>
        </div>

        <div className="material-card feature-card">
          <div className="feature-icon-wrapper">
            <GitCompare size={32} />
          </div>
          <h3 className="feature-title">Delta Compression</h3>
          <p className="body-large">
            Store similar prompts as compact diffs against cluster centroids. 
            Ideal for conversational data and multi-turn chat architectures.
          </p>
        </div>

        <div className="material-card feature-card">
          <div className="feature-icon-wrapper">
            <BookOpen size={32} />
          </div>
          <h3 className="feature-title">Zstd Dictionary</h3>
          <p className="body-large">
            Train highly-optimized shared dictionaries from your specific corpus samples 
            to dramatically boost dictionary-assisted per-prompt baseline compression.
          </p>
        </div>
      </section>

      <section className="stats-banner">
        <div className="stat-item">
          <h3>70.2%</h3>
          <p>Less storage vs Zstd</p>
        </div>
        <div className="stat-item">
          <h3>83.9%</h3>
          <p>Absolute space savings</p>
        </div>
        <div className="stat-item">
          <h3>100%</h3>
          <p>Lossless guarantee</p>
        </div>
        <div className="stat-item">
          <h3>6.21×</h3>
          <p>Mean compression ratio</p>
        </div>
      </section>
    </div>
  );
}
