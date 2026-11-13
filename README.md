# Akro's CrossHair

Aplicación de superposición de miras. Permite colocar miras personalizadas en videojuegos e incluye soporte para atajos de teclado, ratón y mandos, además de detección automática de juegos y un editor interactivo a pantalla completa.

---

## Características principales

- **Superposición transparente:** Ventana invisible al puntero del ratón que no interfiere con los clics ni el rendimiento de los juegos.
- **Biblioteca de miras:** Colección de miras con soporte para importar cualquier imagen PNG.
- **Editor a pantalla completa:** Ajuste visual interactivo arrastrando con el ratón o calibrando píxel a píxel.
- **Perfiles predefinidos (*Presets*) y Grupos:** Guarda configuraciones y agrúpalas por categorías.
- **Detección automática de juegos:** Asocia perfiles a ejecutables específicos; la aplicación activará y aplicará el perfil automáticamente cuando detecte el juego en primer plano.
- **Estados dinámicos por perfil:** Configura variantes de una mira (por ejemplo, para modo apuntado o francotirador) activadas al mantener o alternar botones del ratón, teclas o gatillos del mando.
- **Soporte para mandos:** Detección de mandos Xbox y compatibles mediante XInput y SDL (pygame-ce).
- **Bandeja del sistema:** Se minimiza junto al reloj de Windows y permite arranque automático al encender el equipo.

---

## Instalación

Ejecuta `AkrosCrossHair-Setup.exe` y sigue el asistente. 
- La instalación crea un acceso directo en el menú de inicio y permite crear otro en el escritorio. 

### Ejecutar desde el código fuente

```bash
pip install -r requirements.txt
```

Después, inicia la app desde la carpeta raíz del proyecto:

```bash
python main.py
```

Para crear el instalador de Windows, consulta [packaging/README.md](packaging/README.md).

## Licencia

El código original y los recursos propios que sus titulares pueden licenciar
se ofrecen bajo la Licencia PolyForm No Comercial 1.0.0, junto con las
condiciones complementarias de [LICENSE](LICENSE) y [NOTICE](NOTICE). 
Se permite modificar y redistribuir el proyecto para fines no comerciales; no se permite su uso comercial. 
Las versiones modificadas deben identificarse claramente como no oficiales y no pueden presentarse como versiones oficiales de Akro's CrossHair. 
Esta licencia no cubre dependencias ni recursos de terceros, que conservan sus propias licencias.
