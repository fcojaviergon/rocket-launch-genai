# Cambios en la Arquitectura

## Nuevo Sistema de Análisis

Hemos implementado un nuevo sistema de análisis de documentos que reemplaza el anterior sistema de pipelines. El nuevo sistema está centrado en escenarios de análisis y tiene los siguientes componentes:

### Modelos de Datos

1. **AnalysisScenario**: Contenedor principal para escenarios de análisis
2. **AnalysisPipeline**: Clase base para pipelines de análisis con herencia polimórfica
3. **RfpAnalysisPipeline**: Tabla específica para análisis de RFP
4. **ProposalAnalysisPipeline**: Tabla específica para análisis de propuestas
5. **PipelineEmbedding**: Almacena embeddings para búsqueda semántica

### Estructura de Módulos

```
backend/
├── modules/
│   ├── analysis/         # Módulo principal de análisis
│   │   └── service.py    # Servicio de gestión de escenarios y pipelines
│   ├── pipelines/        # Procesadores de pipeline
│   │   ├── base.py       # Clase base para procesadores
│   │   ├── registry.py   # Registro de procesadores
│   │   ├── document/     # Procesador de documentos
│   │   │   └── processor.py
│   │   ├── rfp/          # Procesador de RFP
│   │   │   └── processor.py
│   │   └── proposal/     # Procesador de propuestas
│   │       └── processor.py
├── database/
│   └── models/
│       └── analysis.py   # Modelos de datos para análisis
└── tasks/
    └── analysis/         # Tareas en segundo plano
        ├── rfp_tasks.py
        └── proposal_tasks.py
```

### Cambios en las Responsabilidades

1. **Procesamiento de Documentos**: Movido de `DocumentService` a `DocumentPipeline` en `modules/pipelines/document/processor.py`
2. **Generación de Embeddings**: Movido de `DocumentService` a `DocumentPipeline`
3. **Análisis de RFP**: Implementado en `RfpPipeline` en `modules/pipelines/rfp/processor.py`
4. **Análisis de Propuestas**: Implementado en `ProposalPipeline` en `modules/pipelines/proposal/processor.py`

### Tareas en Segundo Plano

- `process_document`: Procesa documentos y genera embeddings
- `process_rfp_document`: Procesa documentos RFP
- `process_proposal_document`: Procesa documentos de propuesta

### Endpoints de API

- `POST /analysis/scenarios`: Crear nuevo escenario
- `GET /analysis/scenarios`: Listar escenarios
- `GET /analysis/scenarios/{id}`: Obtener escenario específico
- `POST /analysis/scenarios/{id}/rfp`: Añadir análisis de RFP
- `POST /analysis/scenarios/{id}/proposal`: Añadir análisis de propuesta
- `GET /analysis/scenarios/{id}/pipelines`: Listar pipelines de un escenario

## Componentes Eliminados

Se han eliminado los siguientes componentes que ya no son necesarios:

1. Tabla `pipeline` y `pipeline_execution`
2. Módulo `modules/pipeline`
3. Endpoints `/pipelines`
4. Tareas `document_tasks.py` y `pipeline_tasks.py`
5. Tipos de tarea `PIPELINE_EXECUTION`, `EMBEDDING_GENERATION` y `BATCH_PROCESSING`

## Flujo de Trabajo

1. **Procesamiento de Documentos**:
   - Usuario sube un documento
   - Se crea una tarea de tipo `DOCUMENT_PROCESSING`
   - El sistema procesa el documento y genera embeddings

2. **Análisis de RFP**:
   - Usuario crea un escenario de análisis
   - Sube un documento RFP
   - Se crea una tarea de tipo `RFP_ANALYSIS`
   - El sistema procesa el RFP para extraer criterios de evaluación
   - Se genera un marco de evaluación

3. **Análisis de Propuesta**:
   - Usuario sube documentos de propuesta
   - Se crea una tarea de tipo `PROPOSAL_ANALYSIS`
   - El sistema analiza cada propuesta contra los criterios del RFP
   - Se generan evaluaciones técnicas, gramaticales y de consistencia
