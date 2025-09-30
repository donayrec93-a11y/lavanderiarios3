# Lavandería RÍOS - Sistema de Gestión

Sistema web para la gestión de boletas y servicios de lavandería.

## Características

- Registro de boletas con múltiples ítems
- Cálculo automático de precios según tipo de servicio
- Exportación de datos a CSV
- Generación de enlaces para WhatsApp
- Diseño responsive para móviles y tablets
- Soporte para PWA (Progressive Web App)

## Requisitos

- Python 3.8+
- Flask
- SQLite3

## Instalación

## Instalación y despliegue en Render.com (gratis)

1. Clona este repositorio:
	```bash
	git clone https://github.com/tuusuario/tu-repo.git
	cd tu-repo
	```

2. Crea un entorno virtual e instala dependencias:
	```bash
	python -m venv venv
	venv\Scripts\activate  # En Windows
	# source venv/bin/activate  # En Linux/Mac
	pip install -r requirements.txt
	```

3. Prueba localmente:
	```bash
	python app.py
	```

4. Sube tu código a un repositorio en GitHub.

5. Ve a https://render.com, crea una cuenta y selecciona "New Web Service".
	- Conecta tu cuenta de GitHub y elige tu repositorio.
	- Elige Python 3.x como entorno.
	- En "Start command" pon: `gunicorn app:app`
	- Asegúrate de que el archivo `Procfile` existe y contiene:
	  ```
	  web: gunicorn app:app
	  ```
	- Si usas variables de entorno (.env), configúralas en el panel de Render.
	- Render instalará automáticamente las dependencias de requirements.txt.

6. Espera a que Render despliegue tu app. Obtendrás una URL pública.

7. (Opcional) Si quieres usar tu propio dominio, configúralo en Render.

## Notas importantes
- No subas tu base de datos local (`lavanderia.db`) al repositorio si quieres una base limpia en producción.
- Si necesitas datos de ejemplo, crea un script para poblar la base de datos.
- Elimina carpetas como `__pycache__` antes de subir.
- Prueba la app en varios dispositivos móviles antes de lanzar.

---
¡Listo! Tu app estará disponible en la web y optimizada para móviles.