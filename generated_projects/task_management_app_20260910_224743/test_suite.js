let records = JSON.parse(localStorage.getItem('app_task_management_app_with_tasks_and_completion_toggle') || '[]');
const form = document.getElementById('main-form');
const input = document.getElementById('main-input');
const list = document.getElementById('record-list');
const empty = document.getElementById('empty-state');

function render() {
  list.innerHTML = '';
  if (records.length === 0) {
    empty.style.display = 'block';
  } else {
    empty.style.display = 'none';
    records.forEach((r, idx) => {
      const div = document.createElement('div');
      div.className = 'record-item';
      div.innerHTML = `<span>📌 ${r}</span><button onclick="del(${idx})" style="background:none;border:none;color:#ef4444;cursor:pointer;">&times;</button>`;
      list.appendChild(div);
    });
  }
}

function del(idx) {
  records.splice(idx, 1);
  localStorage.setItem('app_task_management_app_with_tasks_and_completion_toggle', JSON.stringify(records));
  render();
}

form.onsubmit = (e) => {
  e.preventDefault();
  if (input.value.trim()) {
    records.unshift(input.value.trim());
    localStorage.setItem('app_task_management_app_with_tasks_and_completion_toggle', JSON.stringify(records));
    input.value = '';
    render();
  }
};
render();