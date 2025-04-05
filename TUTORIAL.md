# Rocket Launch GenAI Platform - User Tutorial

This tutorial guides you through the basic usage of the Rocket Launch GenAI Platform.

## Prerequisites

- The Rocket Launch GenAI Platform is installed and running (See `INSTALLATION_GUIDE.md`).
- You have access to the frontend URL (e.g., `http://localhost:3000`).
- You have user credentials (email and password).

## 1. Logging In

1.  Open your web browser and navigate to the platform's frontend URL.
2.  You should see a login page.
3.  Enter your registered email address and password.
4.  Click the "Login" or "Sign In" button.
5.  Upon successful login, you will be redirected to the main dashboard.

## 2. Exploring the Dashboard

The dashboard is your main entry point. It typically contains:

-   **Navigation Menu:** Usually on the left side or top, providing access to different sections like Documents, Messages, Completions, Chat, Pipelines, Settings, etc.
-   **Overview/Analytics:** Might display quick stats or recent activity (depending on implementation).

## 3. Managing Documents

This section allows you to upload and manage the files the AI will work with.

1.  **Navigate:** Click on "Documents" in the navigation menu.
2.  **Upload:**
    -   Find the "Upload Document" button or drag-and-drop area.
    -   Select one or more documents (PDF, DOCX, TXT - supported types may vary) from your computer.
    -   The upload process will begin. You might see progress indicators.
3.  **View Documents:**
    -   The main area will list your uploaded documents, showing names, dates, and processing status.
    -   Clicking on a document might show its details, extracted text, or metadata.
4.  **Processing (Automatic/Manual):**
    -   Documents might be automatically processed upon upload (text extraction, embedding generation) based on system configuration or associated pipelines.
    -   If manual processing is required, there might be an option like "Process" or "Run Pipeline" next to each document or in its detail view.

## 4. Querying Documents (Messages / Semantic Search)

This feature lets you ask questions or search for information within your processed documents.

1.  **Navigate:** Click on "Messages" (or similar, like "Query Documents", "Semantic Search") in the navigation menu.
2.  **Select Documents (Optional):** You might be able to select specific documents or collections to query against, or it might search across all your accessible processed documents.
3.  **Enter Query:** Type your question or search keywords into the input field (e.g., "What were the key findings in the Q3 report?").
4.  **Submit:** Press Enter or click the "Send" / "Search" button.
5.  **View Results:** The system will use semantic search (vector similarity) to find relevant sections in your documents and potentially generate a synthesized answer using an AI model (RAG - Retrieval Augmented Generation). The results, including source document snippets, will be displayed.

## 5. Using AI Completions

This section provides direct access to a language model for generating text, answering questions, or performing other language tasks without necessarily referencing your uploaded documents.

1.  **Navigate:** Click on "Completions" (or similar) in the navigation menu.
2.  **Select Model (Optional):** If multiple AI models are configured, you might be able to choose one.
3.  **Enter Prompt:** Type your instruction or question into the prompt input area (e.g., "Write a brief summary of the benefits of AI in customer service.").
4.  **Configure Parameters (Optional):** You might see options to adjust parameters like `max tokens` (response length) or `temperature` (creativity vs. determinism).
5.  **Submit:** Click the "Generate" or "Send" button.
6.  **View Response:** The AI model's generated response will appear.

## 6. Interacting with the Chatbot

This provides a conversational interface with an AI, potentially remembering the context of your conversation.

1.  **Navigate:** Click on "Chat" in the navigation menu.
2.  **Start/Select Chat:** You might see a list of previous chats or an option to start a new one.
3.  **Enter Message:** Type your message or question into the input field at the bottom.
4.  **Send:** Press Enter or click the send button.
5.  **View Response:** The chatbot's reply will appear in the chat history.
6.  **Continue Conversation:** You can continue sending messages, and the chatbot should maintain context within the current session.

## 7. (Future/Optional) Managing Pipelines

Pipelines define sequences of steps for processing documents (e.g., extract text -> chunk -> generate embeddings).

1.  **Navigate:** Click on "Pipelines".
2.  **View Pipelines:** See a list of available pipelines.
3.  **Create/Edit (If UI available):** A visual editor might allow you to drag and drop steps (Input, Text Extraction, Embedding, AI Analysis, Output) and connect them to define a workflow.
4.  **Configure Steps:** Each step might have specific parameters to configure (e.g., chunk size, embedding model).
5.  **Associate with Documents:** You might link pipelines to specific document types or trigger them manually.

## 8. Settings

1.  **Navigate:** Click on "Settings" or your user profile icon.
2.  **Manage Profile:** Update your name, email (if allowed), or password.
3.  **API Keys (If applicable):** Manage personal API keys for accessing the platform programmatically.
4.  **Preferences:** Adjust application preferences if available.

## 9. Logging Out

1.  Find the "Logout" or "Sign Out" button, often located in the user profile menu or main navigation.
2.  Click it to securely end your session.

This covers the fundamental usage. Explore the different sections to discover all the features available in your specific deployment of the Rocket Launch GenAI Platform. 