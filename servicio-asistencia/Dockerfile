# Imagen de servicio-asistencia. Se construye desde la raíz del backend (contexto ".")
# porque necesita copiar también el paquete comun/.
FROM python:3.12-slim

# Sin archivos .pyc y con los logs al instante (sin búfer).
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /servicio

# Primero las dependencias y después el código: Docker reutiliza estas capas
# mientras requirements.txt no cambie, y reconstruir tarda segundos.
COPY comun /comun
RUN pip install --no-cache-dir /comun
COPY servicio-asistencia/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servicio-asistencia/app ./app

# No correr como root: si alguien comprometiera el servicio, no tendría
# permisos de administrador dentro del contenedor.
RUN useradd --create-home schooldesk
USER schooldesk

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
