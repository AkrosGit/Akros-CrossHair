# Instalador de escritorio para Windows

Para generar el instalador de Windows, instala PyInstaller e Inno Setup 6.
Inno Setup se puede obtener en <https://jrsoftware.org/isinfo.php>. 
Desde la carpeta del proyecto, instala la dependencia de compilacion de Python si hace falta:

```powershell
python -m pip install -r packaging\requirements-build.txt
```

Compila el instalador:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

El instalador se genera en `dist\installer\AkrosCrossHair-Setup.exe`. 
Instala la aplicacion solo para el usuario actual, crea un acceso directo en el menu Inicio y ofrece crear otro en el escritorio. 
Se puede desinstalar desde Configuracion de Windows > Aplicaciones. 
La configuracion y las miras importadas se guardan en `%LOCALAPPDATA%\AkrosCrossHair`, separadas de los archivos del programa.

Para usar otro interprete de Python, asigna su ruta a `$env:PYTHON` antes de ejecutar el script de compilacion.
