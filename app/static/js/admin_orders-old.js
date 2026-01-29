// static/js/admin_orders.js
document.addEventListener('DOMContentLoaded', () => {
  const listEl = document.getElementById('orders-list');
  const detailEl = document.getElementById('order-detail');
  const titleEl = document.getElementById('order-detail-title');
  const filterStatus = document.getElementById('filter-status');
  const searchInput = document.getElementById('search-order');

  let currentPage = 1;
  let perPage = 30;
  let currentOrders = [];

  async function loadOrders() {
    const status = filterStatus.value || '';
    const q = (searchInput.value || '').trim();
    listEl.innerHTML = '<p>Loading orders…</p>';
    try {
      const params = new URLSearchParams();
      params.set('page', currentPage);
      params.set('per_page', perPage);
      if (status) params.set('status', status);
      if (q) params.set('q', q);
      const res = await fetch('/api/admin/orders?' + params.toString(), { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to load orders');
      const data = await res.json();
      currentOrders = data.orders || [];
      renderList();
    } catch (err) {
      listEl.innerHTML = '<p>Error loading orders.</p>';
      console.error(err);
    }
  }

  function renderList() {
    listEl.innerHTML = '';
    if (!currentOrders.length) {
      listEl.innerHTML = '<p>No orders found.</p>';
      return;
    }
    currentOrders.forEach(o => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.justifyContent = 'space-between';
      row.style.alignItems = 'center';
      row.style.padding = '8px';
      row.style.borderBottom = '1px solid #eee';
      row.style.cursor = 'pointer';

      const left = document.createElement('div');
      left.innerHTML = `<strong>${o.public_order_id}</strong><div style="font-size:0.9rem;color:#666">${new Date(o.created_at).toLocaleString()}</div>`;

      const right = document.createElement('div');
      right.style.textAlign = 'right';
      right.innerHTML = `<div>${(o.total_cents/100).toFixed(2)} ${o.currency||''}</div><div style="font-size:0.85rem;color:#333">${o.status}</div>`;

      row.appendChild(left);
      row.appendChild(right);
      row.addEventListener('click', () => loadOrderDetails(o.public_order_id));
      listEl.appendChild(row);
    });
  }

  async function loadOrderDetails(public_order_id) {
    titleEl.textContent = `Order ${public_order_id}`;
    detailEl.innerHTML = '<p>Loading…</p>';
    try {
      const res = await fetch(`/api/admin/orders/${encodeURIComponent(public_order_id)}`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Order not found');
      const o = await res.json();
      renderOrderDetail(o);
    } catch (err) {
      detailEl.innerHTML = '<p>Could not load order details.</p>';
      console.error(err);
    }
  }

  function renderOrderDetail(o) {
    const wrap = document.createElement('div');
    wrap.style.display = 'grid';
    wrap.style.gridTemplateColumns = '1fr 320px';
    wrap.style.gap = '12px';

    // left: items and amounts
    const left = document.createElement('div');
    const itemsList = document.createElement('ul');
    itemsList.style.listStyle = 'none';
    itemsList.style.padding = '0';

    (o.items || []).forEach(it => {
      const li = document.createElement('li');
      li.style.borderBottom = '1px solid #eee';
      li.style.padding = '8px 0';
      const name = it.product_snapshot && it.product_snapshot.name ? it.product_snapshot.name : it.variant_sku;
      li.innerHTML = `<strong>${name}</strong><div>SKU: ${it.variant_sku} — Qty: ${it.quantity} — Unit: ${(it.unit_price_cents/100).toFixed(2)}</div>`;
      itemsList.appendChild(li);
    });

    left.appendChild(el('h3', {}, 'Items'));
    left.appendChild(itemsList);
    left.appendChild(document.createElement('hr'));
    left.appendChild(el('p', {}, `Subtotal: $${(o.subtotal_cents/100).toFixed(2)}`));
    left.appendChild(el('p', {}, `Discount: $${(o.discount_cents/100).toFixed(2)}`));
    left.appendChild(el('p', {}, `VAT: $${(o.vat_cents/100).toFixed(2)}`));
    left.appendChild(el('p', {}, `Shipping: $${(o.shipping_cost_cents/100).toFixed(2)}`));
    left.appendChild(el('h3', {}, `Total: $${(o.total_cents/100).toFixed(2)}`));

    // right: workflow controls
    const right = document.createElement('div');
    right.style.borderLeft = '1px solid #eee';
    right.style.paddingLeft = '12px';

    // status selector
    const statusLabel = el('label', {}, 'Status');
    const statusSel = el('select', { class: 'form-input' });
    ['PENDING','PAID','READY_FOR_SHIPPING','SHIPPED','DELIVERED','CANCELLED','RETURNED'].forEach(s => {
      const opt = el('option', { value: s }, s);
      if (s === o.status) opt.selected = true;
      statusSel.appendChild(opt);
    });

    const updStatusBtn = el('button', { class: 'btn btn-primary' }, 'Update Status');
    updStatusBtn.onclick = async () => {
      const newStatus = statusSel.value;
      try {
        const res = await fetch(`/api/admin/orders/${encodeURIComponent(o.public_order_id)}/status`, {
          method: 'PUT', credentials: 'same-origin',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ status: newStatus })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed');
        alert(`Status updated: ${newStatus}`);
        await loadOrders();
        await loadOrderDetails(o.public_order_id);
      } catch (err) {
        alert('Error updating status: ' + err.message);
      }
    };

    // shipment info
    const shipProv = el('input', { class: 'form-input', placeholder: 'Carrier (e.g. UPS)' }); shipProv.value = o.shipping_provider || '';
    const trackIn = el('input', { class: 'form-input', placeholder: 'Tracking number' }); trackIn.value = o.tracking_number || '';
    const markShippedChk = el('input', { type:'checkbox' }); // mark as shipped
    const markShippedLabel = el('label', {}, 'Mark as shipped');

    const saveShipBtn = el('button', { class: 'btn' }, 'Save Shipment');
    saveShipBtn.onclick = async () => {
      try {
        const res = await fetch(`/api/admin/orders/${encodeURIComponent(o.public_order_id)}/shipment`, {
          method: 'PUT', credentials: 'same-origin',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            shipping_provider: shipProv.value || null,
            tracking_number: trackIn.value || null,
            mark_as_shipped: markShippedChk.checked
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to save');
        alert('Shipment info saved.');
        await loadOrders();
        await loadOrderDetails(o.public_order_id);
      } catch (err) {
        alert('Error saving shipment: ' + err.message);
      }
    };

    // packing slip / printable info
    const packBtn = el('button', { class:'btn' }, 'Print Packing Slip');
    packBtn.onclick = () => {
      // simple printable view: open a new window with order summary
      const w = window.open('', '_blank', 'width=800,height=600');
      const html = `
        <html><head><title>Packing Slip ${o.public_order_id}</title></head><body>
        <h1>Packing Slip: ${o.public_order_id}</h1>
        <p>Items:</p>
        <ul>
          ${(o.items || []).map(i => `<li>${i.product_snapshot && i.product_snapshot.name ? i.product_snapshot.name : i.variant_sku} — Qty: ${i.quantity}</li>`).join('')}
        </ul>
        <p>Total: $${(o.total_cents/100).toFixed(2)}</p>
        </body></html>`;
      w.document.write(html); w.document.close();
    };

    // assemble right column
    right.appendChild(el('h3', {}, 'Workflow'));
    right.appendChild(statusLabel);
    right.appendChild(statusSel);
    right.appendChild(updStatusBtn);
    right.appendChild(el('hr'));
    right.appendChild(el('h4', {}, 'Shipment'));
    right.appendChild(shipProv);
    right.appendChild(trackIn);
    right.appendChild(el('div', {}, markShippedChk, el('span', {}, ' '), markShippedLabel));
    right.appendChild(saveShipBtn);
    right.appendChild(el('hr'));
    right.appendChild(packBtn);

    wrap.appendChild(left);
    wrap.appendChild(right);

    detailEl.innerHTML = '';
    detailEl.appendChild(wrap);
  }

  // helper element creator (simple)
  function el(tag, props={}, ...children) {
    const e = document.createElement(tag);
    for (const k in props) {
      if (k === 'class') e.className = props[k];
      else if (k === 'html') e.innerHTML = props[k];
      else if (k === 'for') e.htmlFor = props[k];
      else e.setAttribute(k, props[k]);
    }
    children.forEach(c => { if (typeof c === 'string') e.appendChild(document.createTextNode(c)); else if (c) e.appendChild(c); });
    return e;
  }

  filterStatus.addEventListener('change', loadOrders);
  searchInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') loadOrders();
  });

  // initial load
  loadOrders();
});
