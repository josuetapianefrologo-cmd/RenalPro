
# TRRC360 by Dr. Tapia — Web App (con contraseña)

## Contraseña (simple)
Por defecto, la contraseña es **TRRC360**.
Para cambiarla:
- Edita `app.py` y cambia `DEFAULT_PASSWORD`, o
- Define un secreto en Streamlit Cloud llamado **APP_PASSWORD** y guarda la nueva contraseña allí (recomendado).

## Despliegue en Streamlit Community Cloud
1. Crea un repo GitHub con: `app.py`, `requirements.txt`, `logo.png`.
2. En https://share.streamlit.io, conecta tu repo y selecciona **app.py**.
3. En *Advanced settings → Secrets*, agrega:
```
APP_PASSWORD = "TU_NUEVA_CONTRASEÑA"
```
4. Lanza la app y comparte la URL.

## Local
```bash
pip install -r requirements.txt
streamlit run app.py
```
