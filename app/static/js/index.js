// index.js - loads product list and injects into #product-grid
window.addEventListener('DOMContentLoaded', async () => {
  const grid = document.getElementById('product-grid');
  try {
    const res = await fetch('/api/products?per_page=100', { credentials: 'same-origin' });
    const data = await res.json();
    const products = data.products || [];
    grid.innerHTML = '';
    if (!products.length) { grid.innerHTML = '<p>No products found.</p>'; return; }
    products.forEach(p => {
      const card = document.createElement('div'); card.className='product-card';
      const imageUrl = (p.images && p.images.length) ? p.images[0].url : 'https://via.placeholder.com/300';
      card.innerHTML = `<a href="/product/${p.product_sku}"><img src="${imageUrl}" alt="${p.name}"><h3>${p.name}</h3><p class=\"price\">$${(p.base_price_cents/100).toFixed(2)}</p></a>`;
      grid.appendChild(card);
    });
  } catch (err) {
    console.error(err);
    grid.innerHTML = '<p>Could not load products.</p>';
  }
});
