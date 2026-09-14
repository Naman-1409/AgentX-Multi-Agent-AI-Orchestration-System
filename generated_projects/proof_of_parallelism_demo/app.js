// Client application logic & API connectors
const API_BASE = '/api';
let items = [];
let currentFilter = 'all';

const form = document.getElementById('item-form');
const input = document.getElementById('item-input');
const list = document.getElementById('item-list');
const emptyState = document.getElementById('empty-state');
const countBadge = document.getElementById('count-badge');
const filterBtns = document.querySelectorAll('.filter-btn');

async function loadItems() {
  try {
    const res = await fetch(`${API_BASE}/items`);
    if (res.ok) {
      items = await res.json();
    } else {
      items = JSON.parse(localStorage.getItem('app_build_frontend_ui_components___state_reactive_layer') || '[]');
    }
  } catch(e) {
    items = JSON.parse(localStorage.getItem('app_build_frontend_ui_components___state_reactive_layer') || '[]');
  }
  render();
}

async function addItem(title) {
  const newItem = { id: Date.now().toString(), title: title.trim(), completed: false, created_at: new Date().toISOString() };
  try {
    const res = await fetch(`${API_BASE}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newItem)
    });
    if (res.ok) {
      const saved = await res.json();
      items.unshift(saved);
    } else {
      items.unshift(newItem);
    }
  } catch(e) {
    items.unshift(newItem);
  }
  saveLocal();
  render();
}

async function toggleItem(id) {
  const item = items.find(i => i.id === id);
  if (!item) return;
  item.completed = !item.completed;
  try {
    await fetch(`${API_BASE}/items/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item)
    });
  } catch(e) {}
  saveLocal();
  render();
}

async function deleteItem(id) {
  items = items.filter(i => i.id !== id);
  try {
    await fetch(`${API_BASE}/items/${id}`, { method: 'DELETE' });
  } catch(e) {}
  saveLocal();
  render();
}

function saveLocal() {
  localStorage.setItem('app_build_frontend_ui_components___state_reactive_layer', JSON.stringify(items));
}

function render() {
  const filtered = items.filter(i => {
    if (currentFilter === 'active') return !i.completed;
    if (currentFilter === 'completed') return i.completed;
    return true;
  });

  list.innerHTML = '';
  if (filtered.length === 0) {
    emptyState.style.display = 'block';
  } else {
    emptyState.style.display = 'none';
    filtered.forEach(i => {
      const li = document.createElement('li');
      li.className = `item-card ${i.completed ? 'completed' : ''}`;
      li.innerHTML = `
        <span class="item-title">${i.completed ? '✅' : '⚪'} ${i.title}</span>
        <button class="btn-delete" title="Delete">&times;</button>
      `;
      li.querySelector('.item-title').onclick = () => toggleItem(i.id);
      li.querySelector('.btn-delete').onclick = () => deleteItem(i.id);
      list.appendChild(li);
    });
  }
  countBadge.textContent = `${items.filter(i => !i.completed).length} items active (${items.length} total)`;
}

form.onsubmit = (e) => {
  e.preventDefault();
  if (input.value.trim()) {
    addItem(input.value);
    input.value = '';
  }
};

filterBtns.forEach(btn => {
  btn.onclick = () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    render();
  };
});

loadItems();