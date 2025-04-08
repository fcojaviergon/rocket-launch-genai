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

### Pipeline Design

- Creation of visual flows with draggable nodes (future UI)
- Modular configuration of steps: input, processing, output
- Possibility of manual or automatic execution when uploading documents
- In the future: pre-configured pipeline templates by document type

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

1. A user uploads a document and processes it with a pipeline
2. A user queries documents through messages with AI
3. A user generates responses with an LLM model from completions
4. A user interacts with a chatbot with history
5. An administrator manages users and permissions
6. A super admin supervises all system activity

## Final Considerations

This specification aims to serve as an implementation guide and progress control. The technical components are designed to decouple responsibilities, facilitate scalability, and allow future customization by clients or integrators. The modular approach allows the system to evolve without affecting its core. 