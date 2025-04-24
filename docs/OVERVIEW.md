# Overview

**Rocket Launch GenAI Platform** is a modular white-label platform designed to accelerate the development of enterprise applications based on artificial intelligence. Its event-driven, microservices-based architecture allows efficient scaling and extension for different domains and use cases. The platform is designed for developers, data teams, and businesses that need to create intelligent processing solutions, AI queries, and data flow automation.

## Main Functionalities

### Document Management

- Upload and storage of documents (PDF, DOCX, TXT, etc.)
- Text extraction, segmentation by chunks
- Generation of embeddings and storage in `pgvector`
- Document processing through configurable pipelines

### AI Queries and Semantic Search

- Completions view: model selection and response generation
- Chat view: creation of chats with persistent history
- Messages view: query of processed documents through semantic search
- Documents view: visualization of uploaded files and their metadata

### Analysis System

- Scenario-based analysis with multiple pipelines
- Modular processors for document extraction, embedding generation, and analysis
- Specialized processors for RFP and proposal analysis
- Unified event management for real-time notifications and internal communication
- Asynchronous task processing with progress tracking

### Control Panel and Analytics

- Dashboard with usage metrics by user, document, and pipeline
- Visualization of performance, response times, and errors
- Estimation of token consumption and costs
- Export of reports

### Security and Access

- Authentication with JWT and sessions (NextAuth)
- Role and permission system (RBAC)
- Available roles:
  - **Super Admin**: Full access, cannot be deleted by other roles
  - **Admin**: Can manage users, documents, and configurations
  - **User**: Can operate on their documents, execute AI, manage their personal data
- Audit of relevant events and actions

## Priority Use Cases

1. A user creates an analysis scenario and adds documents for processing
2. A user analyzes RFP documents to extract criteria and evaluation frameworks
3. A user analyzes proposal documents against RFP criteria
4. A user queries documents through messages with AI
5. A user generates responses with an LLM model from completions
6. A user interacts with a chatbot with history
7. An administrator manages users and permissions
8. A super admin supervises all system activity

## Final Considerations

This specification aims to serve as an implementation guide and progress control. The technical components are designed to decouple responsibilities, facilitate scalability, and allow future customization by clients or integrators. The modular approach allows the system to evolve without affecting its core. 