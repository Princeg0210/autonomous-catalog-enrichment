/**
 * UniHack 2026 Dashboard Client Application
 * Handles tab navigation, real-time telemetry, live ingestion, and drawer inspections.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const pageTitle = document.getElementById('page-title');
  const pageDesc = document.getElementById('page-desc');

  // Stats
  const statTotalProducts = document.getElementById('stat-total-products');
  const statTotalAttributes = document.getElementById('stat-total-attributes');
  const statTotalDescriptions = document.getElementById('stat-total-descriptions');
  const statPendingHitl = document.getElementById('stat-pending-hitl');
  const countProducts = document.getElementById('count-products');
  const countHitl = document.getElementById('count-hitl');

  // Tables & Content
  const productsTbody = document.getElementById('products-tbody');
  const hitlTbody = document.getElementById('hitl-tbody');
  const catalogSearch = document.getElementById('catalog-search');
  const presetsContainer = document.getElementById('presets-container');
  const jobConsole = document.getElementById('job-console');
  const formIngest = document.getElementById('form-ingest');

  // Drawer
  const drawerBackdrop = document.getElementById('drawer-backdrop');
  const btnCloseDrawer = document.getElementById('btn-close-drawer');
  const drawerTitle = document.getElementById('drawer-title');
  const drawerBrandManuf = document.getElementById('drawer-brand-manuf');
  const drawerTaxonomy = document.getElementById('drawer-taxonomy');
  const drawerAttrsTbody = document.getElementById('drawer-attrs-tbody');
  const drawerFeaturesTbody = document.getElementById('drawer-features-tbody');
  const drawerCertsTbody = document.getElementById('drawer-certs-tbody');

  // Descriptions
  const descShort = document.getElementById('desc-short');
  const descLong = document.getElementById('desc-long');
  const descMobile = document.getElementById('desc-mobile');
  const descInvoice = document.getElementById('desc-invoice');
  const descRetail = document.getElementById('desc-retail');
  const charShort = document.getElementById('char-short');
  const charLong = document.getElementById('char-long');
  const charMobile = document.getElementById('char-mobile');
  const charInvoice = document.getElementById('char-invoice');
  const charRetail = document.getElementById('char-retail');

  // Telemetry
  const statusApi = document.getElementById('status-api');
  const statusRedis = document.getElementById('status-redis');

  let allProducts = [];

  // Tab titles
  const TAB_METADATA = {
    catalog: {
      title: 'Catalog Explorer',
      desc: 'Real-time repository of categorized and enriched product specifications.',
    },
    ingest: {
      title: 'Ingest & Enrich Engine',
      desc: 'Dispatch single SKUs or batch simulation into Celery worker cluster.',
    },
    hitl: {
      title: 'Human-In-The-Loop (HITL) Queue',
      desc: 'Review pipeline exceptions, missing mandatory attributes, and schema mismatches.',
    },
  };

  // ── Tab Switching ──────────────────────────────────────────────────────────
  document.querySelectorAll('.nav-item').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      button.classList.add('active');
      const targetTab = button.getAttribute('data-tab');
      const pane = document.getElementById(`tab-${targetTab}`);
      if (pane) pane.classList.add('active');

      if (TAB_METADATA[targetTab]) {
        pageTitle.textContent = TAB_METADATA[targetTab].title;
        pageDesc.textContent = TAB_METADATA[targetTab].desc;
      }
    });
  });

  document.getElementById('btn-quick-ingest')?.addEventListener('click', () => {
    document.getElementById('nav-ingest-btn')?.click();
  });

  document.getElementById('btn-refresh')?.addEventListener('click', () => {
    refreshAllData();
    showToast('Catalog & Telemetry Refreshed');
  });

  document.getElementById('btn-reset')?.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to clear the catalog and cache for a fresh demo?')) return;
    try {
      const res = await fetch('/api/reset', { method: 'POST' });
      const data = await res.json();
      showToast(data.message || 'Demo reset complete!');
      refreshAllData();
    } catch (e) {
      showToast(`Reset error: ${e.message}`, 'error');
    }
  });

  // ── Telemetry & Data Fetching ─────────────────────────────────────────────
  async function fetchHealth() {
    try {
      const res = await fetch('/health');
      const data = await res.json();
      if (data.status === 'healthy') {
        statusApi.textContent = 'ONLINE';
        statusApi.className = 'status-pill status-pill-online';
      }
      if (data.redis === 'online') {
        statusRedis.textContent = 'ONLINE';
        statusRedis.className = 'status-pill status-pill-online';
      } else {
        statusRedis.textContent = 'OFFLINE';
        statusRedis.className = 'status-pill status-pill-offline';
      }
    } catch {
      statusApi.textContent = 'OFFLINE';
      statusApi.className = 'status-pill status-pill-offline';
    }
  }

  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      statTotalProducts.textContent = data.total_products || 0;
      statTotalAttributes.textContent = data.total_attributes || 0;
      statTotalDescriptions.textContent = data.total_descriptions || 0;
      statPendingHitl.textContent = data.pending_hitl || 0;

      countProducts.textContent = data.total_products || 0;
      countHitl.textContent = data.pending_hitl || 0;
    } catch (e) {
      console.warn('Failed to load stats', e);
    }
  }

  async function fetchProducts() {
    try {
      const res = await fetch('/api/products');
      allProducts = await res.json();
      renderProductsTable(allProducts);
    } catch (e) {
      productsTbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">Failed to load products: ${e.message}</td></tr>`;
    }
  }

  function renderProductsTable(products) {
    if (!products || products.length === 0) {
      productsTbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No products enriched yet. Ingest a SKU to get started!</td></tr>`;
      return;
    }

    productsTbody.innerHTML = products.map(p => `
      <tr data-product-id="${p.product_id}" onclick="openProductDrawer(${p.product_id})">
        <td class="text-mono">#${p.product_id}</td>
        <td><strong class="text-mono" style="color: var(--accent-cyan);">${escapeHtml(p.mfg_part_num)}</strong></td>
        <td>${escapeHtml(p.part_manuf)}</td>
        <td>${escapeHtml(p.brand_name || '—')}</td>
        <td><span class="text-muted">${escapeHtml(p.category_path || 'Uncategorized')}</span></td>
        <td><span class="badge badge-enriched">${p.attribute_count || 0} Specs</span></td>
        <td><span class="badge badge-enriched">${escapeHtml(p.status)}</span></td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openProductDrawer(${p.product_id})">Inspect</button>
        </td>
      </tr>
    `).join('');
  }

  // ── Search Filter ─────────────────────────────────────────────────────────
  catalogSearch?.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) {
      renderProductsTable(allProducts);
      return;
    }
    const filtered = allProducts.filter(p =>
      (p.mfg_part_num && p.mfg_part_num.toLowerCase().includes(q)) ||
      (p.part_manuf && p.part_manuf.toLowerCase().includes(q)) ||
      (p.brand_name && p.brand_name.toLowerCase().includes(q)) ||
      (p.category_path && p.category_path.toLowerCase().includes(q))
    );
    renderProductsTable(filtered);
  });

  // ── Drawer Inspection ─────────────────────────────────────────────────────
  window.openProductDrawer = async function(productId) {
    try {
      // 1. Explicitly clear all previous product-specific state
      drawerTitle.textContent = 'Loading SKU...';
      drawerBrandManuf.textContent = 'Fetching isolated product record...';
      drawerTaxonomy.textContent = '...';
      drawerAttrsTbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">Loading technical attributes...</td></tr>`;
      if (drawerFeaturesTbody) drawerFeaturesTbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">Loading features...</td></tr>`;
      if (drawerCertsTbody) drawerCertsTbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">Loading certifications...</td></tr>`;
      setDesc(descShort, charShort, '—', 50);
      setDesc(descLong, charLong, '—', 250);
      setDesc(descMobile, charMobile, '—', 30);
      setDesc(descInvoice, charInvoice, '—', 100);
      setDesc(descRetail, charRetail, '—', 150);

      const res = await fetch(`/api/products/${productId}`);
      const data = await res.json();
      if (!data || !data.product) return;

      const p = data.product;
      const techAttrs = data.technical_attributes || data.attributes || [];
      const features = data.features || [];
      const certs = data.certifications || [];
      const descs = data.descriptions || {};

      drawerTitle.textContent = `${p.mfg_part_num}`;
      drawerBrandManuf.textContent = `${p.brand_name || p.part_manuf} • SKU #${p.product_id}`;
      drawerTaxonomy.textContent = p.category_path || 'General Industrial Equipment > Uncategorized';

      // Multi-channel copy
      setDesc(descShort, charShort, descs.short_desc || '—', 50);
      setDesc(descLong, charLong, descs.long_desc || '—', 250);
      setDesc(descMobile, charMobile, descs.mobile_desc || '—', 30);
      setDesc(descInvoice, charInvoice, descs.invoice_desc || '—', 100);
      setDesc(descRetail, charRetail, descs.retail_desc || '—', 150);

      // 1. Technical Attributes (Strictly specs only)
      if (techAttrs.length === 0) {
        drawerAttrsTbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No verified technical attributes found.</td></tr>`;
      } else {
        drawerAttrsTbody.innerHTML = techAttrs.map(a => `
          <tr>
            <td><strong>${escapeHtml(a.attribute || a.attribute_label)}</strong></td>
            <td class="text-mono">${escapeHtml(a.value || a.attribute_value)}</td>
            <td><span class="badge ${a.unit || a.attribute_uom ? 'badge-hitl' : 'badge-pending'}">${escapeHtml(a.unit || a.attribute_uom || 'Unitless')}</span></td>
            <td><span class="text-muted">${Math.round((a.confidence || 0.9) * 100)}%</span></td>
            <td><span class="text-muted" style="font-size:0.75rem;">${escapeHtml(a.provenance || a.extracted_by || 'provenance:[verified]')}</span></td>
          </tr>
        `).join('');
      }
      
      // 2. Distinct Features Section
      if (drawerFeaturesTbody) {
        if (features.length === 0) {
          drawerFeaturesTbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No verified features found.</td></tr>`;
        } else {
          drawerFeaturesTbody.innerHTML = features.map(f => `
            <tr>
              <td><strong style="color: var(--accent-cyan);">${escapeHtml(f.feature)}</strong></td>
              <td><span class="text-muted">${Math.round((f.confidence || 0.9) * 100)}%</span></td>
              <td><span class="text-muted" style="font-size:0.75rem;">${escapeHtml(f.provenance || 'provenance:[verified]')}</span></td>
            </tr>
          `).join('');
        }
      }

      // 3. Certifications & Standards Section
      if (drawerCertsTbody) {
        if (certs.length === 0) {
          drawerCertsTbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No verified certifications found.</td></tr>`;
        } else {
          drawerCertsTbody.innerHTML = certs.map(c => `
            <tr>
              <td><strong style="color: var(--accent-emerald);">${escapeHtml(c.certification)}</strong></td>
              <td><span class="text-muted">${Math.round((c.confidence || 0.9) * 100)}%</span></td>
              <td><span class="text-muted" style="font-size:0.75rem;">${escapeHtml(c.provenance || 'provenance:[verified]')}</span></td>
            </tr>
          `).join('');
        }
      }

      drawerBackdrop.classList.add('active');
    } catch (e) {
      showToast(`Failed to load product details: ${e.message}`, 'error');
    }
  };

  function setDesc(elem, charElem, text, limit) {
    elem.textContent = text;
    charElem.textContent = text === '—' ? 0 : text.length;
  }

  function closeDrawer() {
    drawerBackdrop.classList.remove('active');
  }

  btnCloseDrawer?.addEventListener('click', closeDrawer);
  drawerBackdrop?.addEventListener('click', (e) => {
    if (e.target === drawerBackdrop) closeDrawer();
  });

  // ── HITL Review Queue ─────────────────────────────────────────────────────
  async function fetchHitlQueue() {
    try {
      const res = await fetch('/api/hitl');
      const items = await res.json();
      if (!items || items.length === 0) {
        hitlTbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No flagged exceptions in HITL queue. All products passed quality gates!</td></tr>`;
        return;
      }

      hitlTbody.innerHTML = items.map(item => `
        <tr>
          <td class="text-mono">#${item.id}</td>
          <td><strong class="text-mono">${escapeHtml(item.mfg_part_num || 'N/A')}</strong></td>
          <td>${escapeHtml(item.part_manuf || 'N/A')}</td>
          <td><span class="text-warn">${escapeHtml(item.reason)}</span></td>
          <td><span class="text-muted">${new Date(item.created_at).toLocaleTimeString()}</span></td>
          <td>
            <span class="badge ${item.resolved ? 'badge-enriched' : 'badge-pending'}">
              ${item.resolved ? 'Resolved' : 'Needs Review'}
            </span>
          </td>
          <td>
            ${!item.resolved ? `
              <button class="btn btn-primary btn-sm" onclick="approveHitl(${item.product_id}, ${item.id})">
                Approve & Resolve
              </button>
            ` : '<span class="text-muted">Approved</span>'}
          </td>
        </tr>
      `).join('');
    } catch (e) {
      hitlTbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Failed to load HITL queue: ${e.message}</td></tr>`;
    }
  }

  window.approveHitl = async function(productId, itemId) {
    try {
      const res = await fetch('/hitl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId,
          reviewer: 'Human-Reviewer-Admin',
          correction: { status: 'approved' },
        }),
      });
      const data = await res.json();
      if (data.status === 'resolved') {
        showToast(`Item #${itemId} approved & resolved!`);
        refreshAllData();
      }
    } catch (e) {
      showToast(`Failed to approve: ${e.message}`, 'error');
    }
  };

  // ── Sample Presets & Ingestion ────────────────────────────────────────────
  async function fetchSamples() {
    try {
      const res = await fetch('/api/samples');
      const samples = await res.json();
      presetsContainer.innerHTML = samples.map((s, idx) => `
        <button class="preset-btn" onclick="populateAndIngest(${JSON.stringify(s).replace(/"/g, '&quot;')})">
          <div>
            <div class="preset-mpn">${escapeHtml(s.mfg_part_num)}</div>
            <div class="preset-manuf">${escapeHtml(s.brand_name)} • ${escapeHtml(s.manufacturer)}</div>
          </div>
          <span class="badge badge-enriched">Test Ingest</span>
        </button>
      `).join('');
    } catch (e) {
      presetsContainer.innerHTML = `<div class="text-muted">No presets available</div>`;
    }
  }

  window.populateAndIngest = function(sample) {
    document.getElementById('inp-mpn').value = sample.mfg_part_num;
    document.getElementById('inp-manuf').value = sample.manufacturer;
    document.getElementById('inp-brand').value = sample.brand_name;
    if (sample.mfr_url) document.getElementById('inp-url').value = sample.mfr_url;
    dispatchIngest(sample);
  };

  formIngest?.addEventListener('submit', (e) => {
    e.preventDefault();
    const payload = {
      mfg_part_num: document.getElementById('inp-mpn').value.trim(),
      manufacturer: document.getElementById('inp-manuf').value.trim(),
      brand_name: document.getElementById('inp-brand').value.trim(),
      mfr_url: document.getElementById('inp-url').value.trim() || null,
    };
    dispatchIngest(payload);
  });

  async function dispatchIngest(payload) {
    const btnSubmit = document.getElementById('btn-submit-ingest');
    const origBtnText = btnSubmit ? btnSubmit.innerHTML : '';
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = `<span>Enriching ${payload.mfg_part_num}...</span>`;
    }

    logToConsole(`[Dispatch] Sending SKU: ${payload.mfg_part_num} (${payload.manufacturer})...`, 'text-info');
    try {
      const start = performance.now();
      const res = await fetch('/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const duration = ((performance.now() - start) / 1000).toFixed(2);
      const data = await res.json();

      if (res.ok) {
        logToConsole(`[${payload.mfg_part_num}] ${data.message || 'Success'} (${duration}s)`, 'text-success');
        showToast(`SKU ${payload.mfg_part_num} enriched successfully!`);
        refreshAllData();

        // Switch to Catalog view so user sees enriched row
        setTimeout(() => {
          refreshAllData();
          document.getElementById('nav-catalog-btn')?.click();
        }, 1200);
      } else {
        logToConsole(`[${payload.mfg_part_num}] Error (${res.status}): ${JSON.stringify(data)}`, 'text-warn');
        showToast(`Error: ${data.detail || data.message || 'Failed'}`, 'error');
      }
    } catch (e) {
      logToConsole(`[Error] Ingestion failed: ${e.message}`, 'text-warn');
      showToast(`Ingestion error: ${e.message}`, 'error');
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = origBtnText;
      }
    }
  }

  function logToConsole(msg, cls = '') {
    const line = document.createElement('div');
    line.className = `console-line ${cls}`;
    const time = new Date().toLocaleTimeString();
    line.textContent = `[${time}] ${msg}`;
    jobConsole.appendChild(line);
    jobConsole.scrollTop = jobConsole.scrollHeight;
  }

  // ── Batch Dataset Ingestion ──────────────────────────────────────────────
  document.getElementById('btn-batch-50')?.addEventListener('click', async () => {
    logToConsole('[Batch] Dispatching 50 SKUs from dataset.csv...', 'text-info');
    try {
      const res = await fetch('/api/batch-ingest?limit=50', { method: 'POST' });
      const data = await res.json();
      logToConsole(`[Batch] ${data.message}`, 'text-success');
      showToast('Dispatched 50 SKUs from dataset.csv to Celery cluster!');
      setTimeout(refreshAllData, 2000);
    } catch (e) {
      logToConsole(`[Batch Error] ${e.message}`, 'text-warn');
    }
  });

  document.getElementById('btn-batch-all')?.addEventListener('click', async () => {
    logToConsole('[Batch] Dispatching full dataset (260+ SKUs) from dataset.csv...', 'text-info');
    try {
      const res = await fetch('/api/batch-ingest?limit=300', { method: 'POST' });
      const data = await res.json();
      logToConsole(`[Batch] ${data.message}`, 'text-success');
      showToast('Dispatched full dataset (260+ SKUs) to Celery cluster!');
      setTimeout(refreshAllData, 3000);
    } catch (e) {
      logToConsole(`[Batch Error] ${e.message}`, 'text-warn');
    }
  });

  // ── Toast Helper ──────────────────────────────────────────────────────────
  function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function refreshAllData() {
    fetchHealth();
    fetchStats();
    fetchProducts();
    fetchHitlQueue();
  }

  // Initial Load
  refreshAllData();
  fetchSamples();

  // URL Query Param Helpers for automated views & screenshots
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('drawer')) {
    setTimeout(async () => {
      const res = await fetch('/api/products');
      const prods = await res.json();
      if (prods && prods.length > 0) {
        openProductDrawer(prods[0].product_id);
      }
    }, 600);
  } else if (urlParams.get('tab') === 'hitl') {
    setTimeout(() => {
      document.querySelector('[data-tab="hitl"]')?.click();
    }, 400);
  }

  // Auto-refresh telemetry & tables every 10 seconds
  setInterval(refreshAllData, 10000);
});
