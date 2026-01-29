// static/js/admin_orders.js
// Admin Orders UI: list orders, view order detail, update status and shipment via fetch PUT calls.
// Works for /admin/orders (list) and /admin/orders/<public_order_id> (detail).

(function () {
  'use strict';

  // Helper to create elements quickly
  function el(tag, attrs = {}, ...children) {
    const e = document.createElement(tag);
    for (const k in attrs) {
      if (k === 'class') e.className = attrs[k];
      else if (k === 'html') e.innerHTML = attrs[k];
      else if (k === 'for') e.htmlFor = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    children.forEach(c => {
      if (typeof c === 'string') e.appendChild(document.createTextNode(c));
      else if (c instanceof Node) e.appendChild(c);
    });
    return e;
  }

  // Simple toast / snackbar
  function showToast(message, type = 'info', timeout = 3500) {
    let node = document.getElementById('admin-toast');
    if (!node) {
      node = el('div', { id: 'admin-toast' });
      Object.assign(node.style, {
        position: 'fixed',
        right: '16px',
        bottom: '16px',
        zIndex: 9999,
        minWidth: '200px',
        fontFamily: 'sans-serif'
      });
      document.body.appendChild(node);
    }
    const msg = el('div', { class: `toast ${type}` }, message);
    Object.assign(msg.style, {
      marginTop: '8px',
      padding: '10px 14px',
      borderRadius: '6px',
      color: '#fff',
      background: type === 'error' ? '#c0392b' : (type === 'success' ? '#2ecc71' : '#333'),
      boxShadow: '0 6px 18px rgba(0,0,0,0.08)'
    });
    node.appendChild(msg);
    setTimeout(() => {
      msg.remove();
      if (!node.hasChildNodes()) node.remove();
    }, timeout);
  }

  // Format cents to currency string (simple)
  function formatPrice(cents) {
    cents = Number(cents || 0);
    return `$${(cents / 100).toFixed(2)}`;
  }

  // -------------------------------
  // Orders list page logic
  // -------------------------------
  async function loadOrdersList(containerSelector = '#orders-list') {
    const listEl = document.querySelector(containerSelector);
    if (!listEl) return;

    // Optionally read filters if present in DOM
    const statusFilter = document.querySelector('#filter-status') ? document.querySelector('#filter-status').value : '';
    const qFilter = document.querySelector('#search-order') ? document.querySelector('#search-order').value.trim() : '';
    listEl.innerHTML = '<p>Loading orders…</p>';

    try {
      const params = new URLSearchParams();
      params.set('page', 1);
      params.set('per_page', 50);
      if (statusFilter) params.set('status', statusFilter);
      if (qFilter) params.set('q', qFilter);

      const res = await fetch('/api/admin/orders?' + params.toString(), { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to load orders');
      const data = await res.json();

      const orders = data.orders || [];
      if (!orders.length) {
        listEl.innerHTML = '<p>No orders found.</p>';
        return;
      }

      listEl.innerHTML = '';
      orders.forEach(o => {
        const row = el('div', { class: 'order-row' });
        Object.assign(row.style, { display: 'flex', justifyContent: 'space-between', padding: '10px', borderBottom: '1px solid #eee', cursor: 'pointer' });

        const left = el('div', { class: 'order-left' },
          el('div', { class: 'order-id' }, o.public_order_id),
          el('div', { class: 'order-meta' }, `${new Date(o.created_at).toLocaleString()} • items: ${o.item_count}`)
        );

        const right = el('div', { class: 'order-right' },
          el('div', { class: 'order-total' }, formatPrice(o.total_cents)),
          el('div', { class: 'order-status' }, o.status)
        );
        Object.assign(right.style, { textAlign: 'right' });

        row.appendChild(left);
        row.appendChild(right);

        row.addEventListener('click', () => {
          // Navigate to order detail page - assume route exists /admin/orders/<public_order_id>
          // If your detail page is a SPA panel, you could instead call loadOrderDetails here
          window.location.href = `/admin/orders/${encodeURIComponent(o.public_order_id)}`;
        });

        listEl.appendChild(row);
      });

    } catch (err) {
      console.error('loadOrdersList error', err);
      listEl.innerHTML = '<p>Error loading orders.</p>';
      showToast('Failed to load orders', 'error');
    }
  }

  // -------------------------------
  // Order detail page logic
  // -------------------------------
  async function loadOrderDetail(publicOrderId, detailContainerSelector = '#order-detail') {
    const detailEl = document.querySelector(detailContainerSelector);
    if (!detailEl) return;

    detailEl.innerHTML = '<p>Loading order…</p>';
    try {
      const res = await fetch(`/api/admin/orders/${encodeURIComponent(publicOrderId)}`, { credentials: 'same-origin' });
      if (!res.ok) {
        if (res.status === 404) detailEl.innerHTML = '<p>Order not found.</p>';
        else throw new Error('Failed to load order');
        return;
      }
      const o = await res.json();
      renderOrderDetail(o, detailEl);
    } catch (err) {
      console.error('loadOrderDetail', err);
      detailEl.innerHTML = '<p>Error loading order details.</p>';
      showToast('Failed to load order details', 'error');
    }
  }

  function renderOrderDetail(o, container) {
    container.innerHTML = ''; // clear

    // header / basic summary
    const header = el('div', { class: 'order-header' },
      el('h2', {}, `Order ${o.public_order_id}`),
      el('div', {}, `Created: ${new Date(o.created_at).toLocaleString()}`)
    );
    container.appendChild(header);

    // items list
    const itemsWrap = el('div', { class: 'order-items' });
    itemsWrap.appendChild(el('h3', {}, 'Items'));
    const ul = el('ul', {});
    (o.items || []).forEach(it => {
      const name = (it.product_snapshot && it.product_snapshot.name) ? it.product_snapshot.name : it.variant_sku;
      ul.appendChild(el('li', {}, `${name} — SKU ${it.variant_sku} — Qty ${it.quantity} — Unit ${formatPrice(it.unit_price_cents)}`));
    });
    itemsWrap.appendChild(ul);
    container.appendChild(itemsWrap);

    // amounts
    const amounts = el('div', { class: 'order-amounts' },
      el('p', {}, `Subtotal: ${formatPrice(o.subtotal_cents)}`),
      el('p', {}, `Discount: ${formatPrice(o.discount_cents)}`),
      el('p', {}, `VAT: ${formatPrice(o.vat_cents)}`),
      el('p', {}, `Shipping: ${formatPrice(o.shipping_cost_cents)}`),
      el('h3', {}, `Total: ${formatPrice(o.total_cents)}`)
    );
    container.appendChild(amounts);

    // workflow controls
    const workflow = el('div', { class: 'order-workflow', style: 'margin-top:16px;' });
    workflow.appendChild(el('h3', {}, 'Workflow'));

    const statusSelect = el('select', { class: 'form-input', id: 'admin-status-select' });
    const ORDER_WORKFLOW = ['PENDING','PAID','READY_FOR_SHIPPING','SHIPPED','DELIVERED','CANCELLED','RETURNED'];
    ORDER_WORKFLOW.forEach(s => {
      const opt = el('option', { value: s }, s);
      if (s === o.status) opt.selected = true;
      statusSelect.appendChild(opt);
    });
    workflow.appendChild(statusSelect);

    const updateStatusBtn = el('button', { class: 'btn btn-primary', style: 'margin-left:8px;' }, 'Update Status');
    updateStatusBtn.addEventListener('click', async () => {
      const newStatus = statusSelect.value;
      await updateOrderStatus(o.public_order_id, newStatus);
      // refresh
      await loadOrderDetail(o.public_order_id, container);
      await refreshListIfPresent();
    });
    workflow.appendChild(updateStatusBtn);

    container.appendChild(workflow);

    // shipment controls
    const shipWrap = el('div', { class: 'order-shipment', style: 'margin-top:18px;' });
    shipWrap.appendChild(el('h3', {}, 'Shipment'));

    const providerInput = el('input', { class: 'form-input', placeholder: 'Carrier (e.g. UPS)', id: 'admin-shipping-provider' });
    providerInput.value = o.shipping_provider || '';
    const trackingInput = el('input', { class: 'form-input', placeholder: 'Tracking #', id: 'admin-tracking-number' });
    trackingInput.value = o.tracking_number || '';
    const markShippedChk = el('input', { type: 'checkbox', id: 'admin-mark-shipped' });
    const markShippedLabel = el('label', { for: 'admin-mark-shipped', style: 'margin-left:6px;' }, 'Mark as shipped');

    const saveShipmentBtn = el('button', { class: 'btn', style: 'display:block;margin-top:8px;' }, 'Save Shipment');
    saveShipmentBtn.addEventListener('click', async () => {
      const payload = {
        shipping_provider: providerInput.value || null,
        tracking_number: trackingInput.value || null,
        mark_as_shipped: !!markShippedChk.checked
      };
      await updateOrderShipment(o.public_order_id, payload);
      // refresh
      await loadOrderDetail(o.public_order_id, container);
      await refreshListIfPresent();
    });

    const shipmentRow = el('div', {}, providerInput, trackingInput, el('div', { style: 'margin-top:8px;' }, markShippedChk, markShippedLabel), saveShipmentBtn);
    shipWrap.appendChild(shipmentRow);
    container.appendChild(shipWrap);

    // small details (provider/tracking)
    container.appendChild(el('p', {}, `Current shipment: ${o.shipping_provider || '—'} ${o.tracking_number ? ' • ' + o.tracking_number : ''}`));
    if (o.shipped_at) container.appendChild(el('p', {}, `Shipped at: ${new Date(o.shipped_at).toLocaleString()}`));
  }

  // -------------------------------
  // API calls: update status & shipment
  // -------------------------------
  async function updateOrderStatus(publicOrderId, newStatus) {
    try {
      const res = await fetch(`/api/admin/orders/${encodeURIComponent(publicOrderId)}/status`, {
        method: 'PUT',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to update status');
      }
      showToast(`Order ${publicOrderId} status updated to ${newStatus}`, 'success');
      return data;
    } catch (err) {
      console.error('updateOrderStatus error', err);
      showToast('Failed to update status: ' + err.message, 'error');
      throw err;
    }
  }

  async function updateOrderShipment(publicOrderId, payload) {
    try {
      const res = await fetch(`/api/admin/orders/${encodeURIComponent(publicOrderId)}/shipment`, {
        method: 'PUT',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to update shipment');
      }
      showToast(`Shipment info saved for ${publicOrderId}`, 'success');
      return data;
    } catch (err) {
      console.error('updateOrderShipment error', err);
      showToast('Failed to save shipment: ' + err.message, 'error');
      throw err;
    }
  }

  // If the list view exists on the page, refresh it after changes
  async function refreshListIfPresent() {
    const listNode = document.querySelector('#orders-list');
    if (listNode) await loadOrdersList('#orders-list');
  }

  // -------------------------------
  // Auto-detect page and init
  // -------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    // If orders list element present, render list
    if (document.querySelector('#orders-list')) {
      loadOrdersList('#orders-list');

      // wire up filter controls if present
      const filterStatus = document.querySelector('#filter-status');
      const searchOrder = document.querySelector('#search-order');
      if (filterStatus) filterStatus.addEventListener('change', () => loadOrdersList('#orders-list'));
      if (searchOrder) searchOrder.addEventListener('keydown', (e) => { if (e.key === 'Enter') loadOrdersList('#orders-list'); });
    }

    // If order detail container present and URL contains a public_order_id, load it
    const detailNode = document.querySelector('#order-detail');
    if (detailNode) {
      // Try to extract public_order_id from the URL: /admin/orders/<public_order_id>
      const match = window.location.pathname.match(/\/admin\/orders\/([^\/?#]+)/);
      if (match && match[1]) {
        const publicOrderId = decodeURIComponent(match[1]);
        loadOrderDetail(publicOrderId, '#order-detail');
      } else {
        // If template included order_id in a data attribute, use that (e.g., <div id="order-detail" data-public-order-id="ORD-...">)
        const node = document.getElementById('order-detail');
        const publicOrderId = node ? node.dataset.publicOrderId : null;
        if (publicOrderId) loadOrderDetail(publicOrderId, '#order-detail');
      }
    }
  });

  // expose for debugging
  window.adminOrders = {
    loadOrdersList,
    loadOrderDetail,
    updateOrderStatus,
    updateOrderShipment
  };

})();
