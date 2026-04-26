# Instagram Analytics Scraper

Aplicación web para extraer métricas públicas de perfiles de Instagram y analizar publicaciones recientes mediante un dashboard visual.

---

## ¿Qué hace esta aplicación?

Permite ingresar un usuario de Instagram y obtener:

### Datos del perfil

- Usuario
- Nombre del perfil
- Seguidores
- Seguidos
- Número total de publicaciones


### Datos de publicaciones

- Tipo de publicación (Post / Reel)
- Fecha
- Likes
- Hashtags
- Comentario
- URL directa

### Dashboard

- Publicaciones 
- Likes totales
- Comentarios totales
- Hashtags 

---

## Tecnologías utilizadas

### Backend

- Python
- FastAPI
- Uvicorn
- Playwright

### Frontend

- React
- Vite
- JavaScript
- CSS

---

## Estructura del proyecto

```text
instagram-project/
│
├── backend/
│   ├── api.py
│   ├── requirements.txt
│   └── app/
│       ├── browser.py
│       ├── config.py
│       ├── models.py
│       ├── parser.py
│       ├── scraper.py
│       └── session.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       └── App.css
│
└── README.md
