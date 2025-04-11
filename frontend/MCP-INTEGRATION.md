# Integración de MCP en el Agente AI

Hemos implementado mejoras en el agente para aprovechar mejor la funcionalidad de los servidores MCP y mejorar la experiencia del usuario.

## Características implementadas

1. **Panel de Servidores MCP**
   - Visualización de servidores MCP disponibles
   - Lista de comandos disponibles por servidor
   - Ejemplos de uso para cada servidor

2. **Visualización del Proceso de Razonamiento**
   - Opción para mostrar/ocultar el proceso de pensamiento del agente
   - Estilo diferenciado para los mensajes de tipo "thinking"
   - Mejora visual para las llamadas a herramientas

## Cómo usarlo

### Para usuarios

1. En la interfaz del Agente, encontrarás un botón "MCP Servers" en la parte superior derecha
2. Al hacer clic en este botón, se mostrará un panel con los servidores disponibles
3. Puedes expandir cada servidor para ver los comandos disponibles y ejemplos
4. Usa esta información para formular tus preguntas de manera más efectiva

### Para desarrolladores

1. **Instalación de dependencias**:
   ```bash
   # Desde el directorio frontend
   chmod +x install-missing-deps.sh
   ./install-missing-deps.sh
   ```

   Si el script muestra errores, puedes reintentar con los siguientes pasos:
   
   ```bash
   # 1. Instalar dependencias básicas
   npm install react-markdown @radix-ui/react-popover @radix-ui/react-collapsible @radix-ui/react-avatar class-variance-authority clsx tailwind-merge
   
   # 2. Crear los directorios necesarios
   mkdir -p src/components/ui
   mkdir -p src/lib
   
   # 3. Copiar components.json a la raíz del proyecto (desde frontend/components.json)
   cp frontend/components.json .
   
   # 4. Verificar que src/lib/utils.ts existe con la función cn()
   
   # 5. Ejecutar de nuevo el script
   ./frontend/install-missing-deps.sh
   ```

2. **Estructura del código**:
   - La lógica de integración de MCP está incorporada en `AgentChatInterface.tsx`
   - La interfaz aprovecha los nuevos endpoints de backend: 
     - `/api/v1/agent/mcp/servers`: Lista los servidores disponibles y sus comandos
     - `/api/v1/agent/conversations/{id}/detailed-messages`: Permite recuperar mensajes de tipo "thinking"

## Arquitectura

```
Frontend
├── components/
│   └── agent/
│       └── AgentChatInterface.tsx   # Componente principal con integración MCP
└── app/
    └── dashboard/
        └── agent/
            └── page.tsx             # Página que usa el componente

Backend
├── api/v1/
│   └── agent.py                     # Endpoints para MCP y detailed-messages
└── services/
    └── agent_tools/
        └── mcp_tool.py              # Herramienta MCP con detección dinámica
```

## Solución de problemas

1. **Problemas con componentes de UI**:
   - Si el script de instalación no logra instalar los componentes correctamente, estos se crearán manualmente en `src/components/ui/`.
   - Verifica que los archivos `popover.tsx`, `collapsible.tsx`, `avatar.tsx` y `badge.tsx` existen en ese directorio.
   - Si faltan, el script debería crearlos automáticamente.

2. **Problemas con shadcn/ui**:
   - El script intenta configurar `shadcn` automáticamente, pero si falla, creará los componentes manualmente.
   - Si ves errores relacionados con `components.json`, verifica que este archivo existe en la raíz del proyecto.

3. **Errores de importación**:
   - Si ves errores en importaciones de componentes como `@/components/ui/...`, asegúrate de que el archivo existe en la ruta correcta.
   - La estructura de `@/` debería mapear a la carpeta `src/` en el proyecto.

## Próximos pasos recomendados

1. Mejorar el formateado de los mensajes de tipo "tool" para facilitar la comprensión
2. Añadir la capacidad de copiar ejemplos de comandos desde el panel de MCP
3. Implementar un sistema de feedback para mejorar las respuestas del agente 