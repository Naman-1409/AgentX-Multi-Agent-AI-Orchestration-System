# FastAPI REST Backend for Implement FastAPI Backend REST Routes & Business Logic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3
import os
import uvicorn

app = FastAPI(title='Implement FastAPI Backend REST Routes & Business Logic API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

init_db()

class Item(BaseModel):
    id: str
    title: str
    completed: bool = False
    created_at: Optional[str] = None

class ItemCreate(BaseModel):
    title: str

@app.get('/api/health')
def health():
    return {'status': 'healthy', 'service': 'Implement FastAPI Backend REST Routes & Business Logic'}

@app.get('/api/items', response_model=List[Item])
def get_items():
    conn = get_db()
    rows = conn.execute('SELECT id, title, completed, created_at FROM items ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(id=r['id'], title=r['title'], completed=bool(r['completed']), created_at=r['created_at']) for r in rows]

@app.post('/api/items', response_model=Item)
def create_item(item: Item):
    conn = get_db()
    conn.execute(
        'INSERT OR REPLACE INTO items (id, title, completed, created_at) VALUES (?, ?, ?, ?)',
        (item.id, item.title, 1 if item.completed else 0, item.created_at or '')
    )
    conn.commit()
    conn.close()
    return item

@app.put('/api/items/{item_id}', response_model=Item)
def update_item(item_id: str, item: Item):
    conn = get_db()
    cursor = conn.execute(
        'UPDATE items SET title = ?, completed = ? WHERE id = ?',
        (item.title, 1 if item.completed else 0, item_id)
    )
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail='Item not found')
    return item

@app.delete('/api/items/{item_id}')
def delete_item(item_id: str):
    conn = get_db()
    cursor = conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail='Item not found')
    return {'deleted': True, 'id': item_id}

# Mount static frontend files if present
static_dir = os.path.dirname(__file__)
if os.path.exists(os.path.join(static_dir, 'index.html')):
    app.mount('/', StaticFiles(directory=static_dir, html=True), name='static')

if __name__ == '__main__':
    uvicorn.run('server:app', host='0.0.0.0', port=8000, reload=True)