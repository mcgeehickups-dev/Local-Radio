# Radio Local — Instrucciones

Esta app reproduce un stream de audio desde una URL de tu red local
(por ejemplo, la de un emisor Icecast/Shoutcast en tu WiFi).

## Pasos para compilar la APK sin gastar tu internet

1. **Crea una cuenta en GitHub** (github.com) si no tienes una. Esto pesa poco,
   solo es un formulario.

2. **Crea un repositorio nuevo** (botón "New repository"), por ejemplo
   llamado `radio-local`. Puede ser público o privado.

3. **Sube estos 4 archivos/carpetas** al repositorio, manteniendo la
   misma estructura de carpetas:
   - `main.py`
   - `buildozer.spec`
   - `.github/workflows/build.yml`
   - `LEEME.md` (opcional)

   Puedes hacerlo desde la web de GitHub con "Add file" → "Upload files"
   (arrastra los archivos), sin necesidad de usar la terminal ni git.
   Ojo: al subir por la web, asegúrate de que `build.yml` quede dentro
   de las carpetas `.github/workflows/` — si GitHub no te deja crear
   esas carpetas al arrastrar, crea primero un archivo llamado
   `.github/workflows/build.yml` directamente desde "Create new file"
   y pega el contenido ahí.

4. Ve a la pestaña **"Actions"** de tu repositorio. Debería empezar a
   compilar automáticamente (tarda entre 10 y 20 minutos la primera vez,
   pero corre en los servidores de GitHub, no en tu conexión).

5. Cuando termine (círculo verde ✓), entra en esa ejecución y baja hasta
   **"Artifacts"**. Ahí vas a poder descargar `radio-local-apk` — un
   archivo comprimido que trae tu `.apk` dentro. Esta descarga sí pasa
   por tu internet, pero es solo unos pocos MB.

6. Descomprime, copia el `.apk` a tu teléfono e instálalo (activa
   "instalar de fuentes desconocidas" si Android te lo pide).

## Cómo usar la app

Al abrirla, escribe la URL de tu emisora local en el campo de texto
(por ejemplo `http://192.168.1.100:8000/stream`) y toca "Escuchar".
Debes estar conectado a la misma red WiFi/hotspot que el emisor.

## Si algo falla

Si la pestaña "Actions" muestra una ❌ roja, entra a ver el detalle del
error — casi siempre es un problema de indentación en `buildozer.spec`
o de estructura de carpetas. Copia el mensaje de error y te ayudo a
interpretarlo.
