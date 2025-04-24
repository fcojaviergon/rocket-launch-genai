# Analysis System

## Overview

The Analysis System is a modular architecture designed to process and analyze documents efficiently. It replaces the previous pipeline system with an approach based on scenarios and specialized processors, improving flexibility, maintainability, and performance.

## Main Components

### Data Models

#### AnalysisScenario
- Main container for analysis scenarios
- Groups multiple related pipelines
- Stores scenario configuration and metadata

#### AnalysisPipeline
- Base class for analysis pipelines with polymorphic inheritance
- Implements functionality common to all pipeline types
- Maintains relationships with documents and scenarios

#### RfpAnalysisPipeline
- Specialized pipeline for RFP (Request for Proposal) analysis
- Extracts criteria and evaluation frameworks from RFP documents
- Stores specific results from RFP analysis

#### ProposalAnalysisPipeline
- Specialized pipeline for proposal analysis
- Evaluates proposals against RFP criteria
- Generates scores and executive summaries

#### PipelineDocument
- Associates documents with pipelines
- Defines roles and processing order
- Facilitates parallel processing of multiple documents

### Processors

#### DocumentProcessor
- Extracts text from documents in different formats
- Segments documents into manageable chunks
- Preprocesses text for further analysis

#### EmbeddingProcessor
- Generates embeddings for documents and chunks
- Stores vectors in the database (pgvector)
- Optimizes embedding generation

#### RfpProcessor
- Analyzes RFP documents
- Extracts criteria and requirements
- Generates structured evaluation frameworks

#### ProposalProcessor
- Analyzes proposal documents
- Evaluates proposals against RFP criteria
- Generates scores and recommendations

### Asynchronous Tasks

#### async_rfp_tasks.py
- Implements Celery tasks for RFP processing
- Coordinates the RFP analysis workflow
- Handles errors and reports progress

#### async_proposal_tasks.py
- Implements Celery tasks for proposal processing
- Coordinates the proposal analysis workflow
- Integrates RFP results into proposal analysis

## Workflow

### RFP Analysis

1. An analysis scenario is created
2. An RFP pipeline with associated documents is added
3. Asynchronous document processing begins
4. Documents are processed in parallel:
   - Text extraction
   - Embedding generation
   - Content analysis
5. Results from multiple documents are combined
6. Criteria are extracted and an evaluation framework is generated
7. Completion is notified through the event system

### Proposal Analysis

1. A proposal pipeline is added to an existing scenario
2. It's associated with an RFP pipeline to obtain criteria
3. Proposal documents are processed:
   - Text extraction
   - Embedding generation
   - Analysis against RFP criteria
4. The proposal is evaluated and scores are generated
5. An executive summary is created
6. Completion is notified through the event system

## Advantages of the New System

1. **Modularity**: Processors with single, well-defined responsibilities
2. **Parallelism**: Simultaneous processing of multiple documents
3. **Flexibility**: Easy extension for new types of analysis
4. **Maintainability**: Cleaner and better organized code
5. **Performance**: Optimization of resources and processing times
6. **Traceability**: Better tracking of progress and errors

## Integration with the Event System

The analysis system integrates closely with the Unified Event System:

1. Processors publish progress events
2. Asynchronous tasks report their status
3. Clients receive real-time updates
4. An event log is maintained for auditing

## API and Endpoints

The system exposes RESTful endpoints for:

1. Scenario management
2. Pipeline creation and configuration
3. Progress monitoring
4. Results retrieval
5. Pipeline reprocessing

All endpoints are available at `/api/v1/analysis/`.
