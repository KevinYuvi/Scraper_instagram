# Scraper de Instagram 

Deber de scraping para instagram

---

## ¿Qué se puede obtener?

### Información del perfil
- Nombre de usuario.
- Cantidad de seguidores y seguidos.
- El número total de publicaciones que tiene la cuenta.

### Detalle de las publicaciones
- Identifica si el contenido es un Post o un Reel.
- Fecha de la publicación.
- Conteo real de likes y comentarios
- Lista de hashtags.
- El texto de la publicación y el enlace directo al contenido.

### Dashboard
- Sumatoria de likes y comentarios totales del lote extraído.

---

## Tecnologías que dan vida al proyecto

### En el servidor (Backend)
- Python y FastAPI para gestionar las peticiones de forma rápida.
- Playwright para navegar y extraer los datos directamente del código de Instagram.

### En la interfaz (Frontend)
- React y Vite para una experiencia de usuario fluida.
- JavaScript y CSS para el diseño del dashboard.

---

## Organización de las carpetas

```text
instagram-project/
│
├── backend/            # Lógica del servidor y extracción de datos
│   ├── api.py          # Rutas de la API
│   └── app/            
│
├── frontend/           # Interfaz de usuario
│   └── src/            # Componentes y estilos de React
│
└── README.md           # Esta guía de uso
```

---

## Pasos para la instalación

### 1. Obtener el código
```bash
git clone https://github.com/KevinYuvi/Scraper_instagram.git
cd Scraper_instagram
```

### 2. Configurar el Backend
Primero entra a la carpeta del backend, prepara el entorno de Python e instala lo necesario:
```bash
cd backend
python -m venv venv

# Para activar el entorno:
# En Windows:
venv\Scripts\activate
# En Linux o Mac:
source venv/bin/activate

# Instalar las librerías:
pip install -r requirements.txt
```

**Configuración necesaria:**
Debes crear un archivo llamado `.env` dentro de la carpeta `backend` con tus credenciales de Instagram para que el sistema pueda navegar correctamente:
```env
INSTAGRAM_USERNAME=tu_usuario
INSTAGRAM_PASSWORD=tu_contraseña
MAX_POSTS=10
HEADLESS_MODE=True
```

**Lanzar el servidor:**
```bash
uvicorn api:app --reload
```

### 3. Configurar el Frontend
Abre una terminal nueva y ejecutar estos comandos para levantar la interfaz:
```bash
cd frontend
npm install
npm run dev
```

Una vez que ambos servicios estén corriendo, ya se puede abrir la aplicación en el navegador (`http://localhost:5173`).
