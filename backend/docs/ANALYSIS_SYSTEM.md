# Sistema de Análisis de Documentos

## Arquitectura

El sistema de análisis de documentos reemplaza el anterior sistema de pipelines con un enfoque más flexible y modular, centrado en escenarios de análisis.

### Componentes Principales

1. **Escenarios de Análisis**: Contenedor de alto nivel para flujos de trabajo de análisis
2. **Pipelines de Análisis**: Ejecuciones específicas para diferentes tipos de análisis (RFP, Propuestas)
3. **Procesadores de Pipeline**: Módulos que implementan la lógica de procesamiento para cada tipo de documento
4. **Tareas de Análisis**: Tareas en segundo plano para procesar documentos

## Estructura del Proyecto

```
backend/
├── modules/
│   ├── analysis/         # Módulo principal de análisis
│   │   └── service.py    # Servicio de gestión de escenarios y pipelines
│   ├── pipelines/        # Procesadores de pipeline
│   │   ├── base.py       # Clase base para procesadores
│   │   ├── registry.py   # Registro de procesadores
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

## Modelos de Datos

### AnalysisScenario
- Contenedor principal para un escenario de análisis
- Puede contener múltiples pipelines de análisis
- Pertenece a un usuario

### AnalysisPipeline (Clase Base)
- Modelo base para todos los tipos de pipeline
- Implementa herencia polimórfica con SQLAlchemy
- Contiene campos y relaciones comunes

### RfpAnalysisPipeline
- Hereda de AnalysisPipeline
- Almacena criterios extraídos y marcos de evaluación
- Tabla específica: `rfp_analysis_pipelines`

### ProposalAnalysisPipeline
- Hereda de AnalysisPipeline
- Almacena resultados de evaluación y análisis técnico
- Tabla específica: `proposal_analysis_pipelines`

### PipelineEmbedding
- Almacena embeddings para búsqueda semántica
- Vinculado a un pipeline específico

## Flujo de Trabajo

1. **Análisis de RFP**:
   - Usuario crea un escenario de análisis
   - Sube un documento RFP
   - El sistema procesa el RFP para extraer criterios de evaluación
   - Se genera un marco de evaluación

2. **Análisis de Propuesta**:
   - Usuario sube documentos de propuesta
   - El sistema analiza cada propuesta contra los criterios del RFP
   - Se generan evaluaciones técnicas, gramaticales y de consistencia
   - Se proporciona un marco comparativo

## Servicios

### AnalysisService
- Gestiona la creación y consulta de escenarios
- Coordina la adición de pipelines de análisis
- Inicia tareas en segundo plano

### Procesadores de Pipeline
- **RfpPipeline**: Extrae criterios y genera marcos de evaluación
- **ProposalPipeline**: Evalúa propuestas contra criterios de RFP

## API Endpoints

- `POST /analysis/scenarios`: Crear nuevo escenario
- `GET /analysis/scenarios`: Listar escenarios
- `GET /analysis/scenarios/{id}`: Obtener escenario específico
- `POST /analysis/scenarios/{id}/rfp`: Añadir análisis de RFP
- `POST /analysis/scenarios/{id}/proposal`: Añadir análisis de propuesta
- `GET /analysis/scenarios/{id}/pipelines`: Listar pipelines de un escenario

## Tareas en Segundo Plano

- `process_rfp_document`: Procesa documentos RFP
- `process_proposal_document`: Procesa documentos de propuesta

## Migración desde el Sistema Anterior

El nuevo sistema reemplaza completamente las tablas `pipeline` y `pipeline_execution`, centrándose en un enfoque más flexible y orientado a escenarios específicos de análisis de documentos. Se han eliminado los módulos y endpoints relacionados con el sistema anterior.
