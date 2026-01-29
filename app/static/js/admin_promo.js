// static/js/admin_promo.js

(function () {
  'use strict';

  function el(tag, attrs = {}, ...children) {
    const e = document.createElement(tag);
    for (const k in attrs) {
      if (k === 'class') e.className = attrs[k];
      else if (k === 'html') e.innerHTML = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    children.forEach(c => {
      if (typeof c === 'string') e.appendChild(document.createTextNode(c));
      else if (c instanceof Node) e.appendChild(c);
    });
    return e;
  }

  function $(sel, root = document) { return root.querySelector(sel); }

  document.addEventListener('DOMContentLoaded', () => {
    const promoList = $('#promo-list');
    const userSelect = $('#promo_user_id');
    const saveBtn = $('#save-promo');
    const deleteBtn = $('#delete-promo');
    const newBtn = $('#btn-new-promo');
    const feedback = $('#admin-feedback');

    if (!promoList) return;

    function showFeedback(msg, type = 'info') {
      if (feedback) {
        feedback.style.display = 'block';
        feedback.className = `alert alert-dismissible fade show mb-0 ${type === 'error' ? 'alert-danger' : 'alert-success'}`;
        feedback.textContent = msg;
        feedback.classList.remove('d-none');
        setTimeout(() => {
          feedback.classList.add('d-none');
        }, 5000);
      } else {
        alert(msg);
      }
    }

    async function loadUsers() {
      try {
        const res = await fetch('/api/admin/users');
        if (!res.ok) throw new Error('Failed to load users');
        const users = await res.json();
        userSelect.innerHTML = '<option value="">Global (All Users)</option>';
        users.forEach(u => {
          userSelect.appendChild(el('option', { value: u.id }, `${u.username} (${u.email})`));
        });
      } catch (err) {
        console.error(err);
      }
    }

    async function loadPromos() {
      try {
        const res = await fetch('/api/admin/promotions');
        if (!res.ok) throw new Error('Failed to load promotions');
        const promos = await res.json();
        promoList.innerHTML = '';
        promos.forEach(p => {
          const item = el('div', {
            class: 'list-group-item list-group-item-action cursor-pointer',
            style: 'cursor: pointer;'
          },
            el('div', { class: 'd-flex w-100 justify-content-between' },
              el('h6', { class: 'mb-1' }, p.code),
              el('small', {}, p.is_active ? 'Active' : 'Inactive')
            ),
            el('p', { class: 'mb-1 small' }, p.description || ''),
            el('small', {}, `${p.discount_type}: ${p.discount_value}${p.discount_type === 'PERCENT' ? '%' : '€'}`),
            p.username ? el('div', { class: 'small text-primary' }, `User: ${p.username}`) : null
          );
          item.addEventListener('click', () => loadPromoDetails(p));
          promoList.appendChild(item);
        });
      } catch (err) {
        console.error(err);
      }
    }

    function loadPromoDetails(p) {
      $('#promo_code').value = p.code;
      $('#promo_type').value = p.discount_type;
      $('#promo_value').value = p.discount_value;
      $('#promo_description').value = p.description || '';
      $('#promo_active').checked = p.is_active;
      $('#promo_user_id').value = p.user_id || '';

      if (p.valid_to) {
        // format ISO to datetime-local compatible string
        const d = new Date(p.valid_to);
        const pad = (n) => n.toString().padStart(2, '0');
        const formatted = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        $('#promo_valid_to').value = formatted;
      } else {
        $('#promo_valid_to').value = '';
      }

      saveBtn.dataset.editId = p.id;
      $('#promo-editor-title').textContent = 'Edit Promo Code: ' + p.code;
    }

    saveBtn.addEventListener('click', async () => {
      const payload = {
        code: $('#promo_code').value.trim(),
        discount_type: $('#promo_type').value,
        discount_value: $('#promo_value').value,
        description: $('#promo_description').value.trim(),
        is_active: $('#promo_active').checked,
        valid_to: $('#promo_valid_to').value || null,
        user_id: $('#promo_user_id').value || null
      };

      if (!payload.code || !payload.discount_value) {
        return showFeedback('Code and Value are required', 'error');
      }

      const editId = saveBtn.dataset.editId;
      const method = editId ? 'PUT' : 'POST';
      const url = editId ? `/api/admin/promotions/${editId}` : '/api/admin/promotions';

      try {
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          showFeedback('Promotion saved successfully');
          loadPromos();
          if (!editId) resetForm();
        } else {
          const data = await res.json();
          showFeedback(data.error || 'Failed to save promotion', 'error');
        }
      } catch (err) {
        showFeedback('Network error', 'error');
      }
    });

    deleteBtn.addEventListener('click', async () => {
      const editId = saveBtn.dataset.editId;
      if (!editId) return;
      if (!confirm('Are you sure you want to delete this promo code?')) return;

      try {
        const res = await fetch(`/api/admin/promotions/${editId}`, { method: 'DELETE' });
        if (res.ok) {
          showFeedback('Promotion deleted');
          resetForm();
          loadPromos();
        } else {
          showFeedback('Failed to delete', 'error');
        }
      } catch (err) {
        showFeedback('Network error', 'error');
      }
    });

    newBtn.addEventListener('click', resetForm);

    function resetForm() {
      $('#promo_code').value = '';
      $('#promo_type').value = 'PERCENT';
      $('#promo_value').value = '';
      $('#promo_description').value = '';
      $('#promo_active').checked = true;
      $('#promo_valid_to').value = '';
      $('#promo_user_id').value = '';
      saveBtn.dataset.editId = '';
      $('#promo-editor-title').textContent = 'Create / Edit Promo Code';
    }

    loadUsers();
    loadPromos();
  });
})();
