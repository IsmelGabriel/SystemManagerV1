# 🖥️ SystemManager V1 (Python Prototype)

**SystemManager** es una aplicación de escritorio diseñada para Windows cuyo objetivo principal es centralizar la monitorización de hardware y la gestión avanzada de recursos del sistema operativo. Funciona como una alternativa integral al Administrador de Tareas tradicional, combinando métricas en tiempo real con herramientas de optimización directas.

> **Nota importante:** Esta versión (V1) está desarrollada en **Python 3.12**. Se trata de un prototipo funcional diseñado para validar las mecánicas de monitorización y gestión de la interfaz de usuario. 

---

## 🚀 El futuro del proyecto: Migración a C# (.NET)

Aunque Python ha sido excelente para construir este prototipo de forma ágil, el objetivo final de **SystemManager** es ser migrado íntegramente a **C#**. Las razones técnicas para esta transición son:

1. **Rendimiento Nativo y Consumo de Memoria:** Las aplicaciones de escritorio en C# (como WPF o WinUI) gestionan la memoria de forma mucho más eficiente. En Python, depender de la máquina virtual (y subprocesos) genera un consumo base alto, lo cual es contraproducente para un "Optimizador de Memoria".
2. **Integración profunda con Windows API:** C# permite interactuar nativamente con WMI, el Registro de Windows y las APIs del sistema (sin necesidad de librerías externas o invocar scripts de PowerShell por debajo), haciendo la aplicación más segura, rápida y silenciosa.
3. **Distribución:** Compilar un binario de C# `.exe` es estándar en Windows, reduciendo drásticamente el peso de la aplicación comparado con empaquetadores como `PyInstaller`.

---

## ✨ Características (V1)

- 📊 **Monitor de sistema en tiempo real**: Uso de CPU, RAM, Red y almacenamiento en discos.
- 🪟 **Monitor Flotante**: Un widget translúcido minimalista que se ancla en pantalla para vigilar la RAM y la CPU sin interrumpir el flujo de trabajo.
- ⚙️ **Gestión de procesos**: Un árbol de procesos con soporte para suspender, terminar y cambiar la prioridad del procesador, separando aplicaciones de servicios en segundo plano.
- 🚀 **Gestión de inicio (Startup)**: Control total sobre los programas que arrancan junto al sistema operativo (Registro de Windows y carpetas de inicio).
- 🧹 **Optimizador de Sistema**: Herramientas integradas para liberar memoria de reserva, limpiar archivos temporales, vaciar la papelera de reciclaje usando la API nativa, y gestionar la Memoria Virtual (Pagefile.sys).

---

## 📦 Instalación y Ejecución (Prototipo V1)

### 1. Clonar el repositorio

```bash
git clone https://github.com/IsmelGabriel/SystemManagerV1.git
cd SystemManagerV1
```

### 2. Crear un entorno virtual (Recomendado)

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

**Es fundamental ejecutar la aplicación con permisos de Administrador** para que las lecturas de sistema y las operaciones de optimización funcionen correctamente.

```bash
python main.py
```
