import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select as sqlalchemy_select, text
import numpy as np

from database.models.document import Document, DocumentEmbedding
from modules.pipeline import OpenAIEmbeddingStep

# Load environment variables
load_dotenv()

# Configure the database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def search_similar_documents(query_text: str, top_k: int = 3):
    """Search for similar documents to a query text"""
    async with async_session() as session:
        # Generate embedding for the query text
        embedding_step = OpenAIEmbeddingStep(
            model="text-embedding-3-small"
        )
        
        # Get the embedding for the query text
        data = {"content": query_text}
        context = {}
        result = await embedding_step.process(data, context)
        query_embedding = result.get("embedding", [])
        
        # Convert the embedding to text format for pgvector
        embedding_str = str(query_embedding).replace('[', '{').replace(']', '}')
        
        # Search for similar documents using the pgvector extension
        # Note: This requires that the pgvector extension is installed in PostgreSQL
        query = f"""
        SELECT d.id, d.title, d.content, de.chunk_text, 
               (de.embedding <=> '{embedding_str}'::vector) as distance
        FROM document_embeddings de
        JOIN documents d ON de.document_id = d.id
        ORDER BY distance ASC
        LIMIT {top_k}
        """
        
        result = await session.execute(text(query))
        
        similar_docs = result.fetchall()
        
        print(f"\n--- Results for the query: '{query_text}' ---")
        for i, doc in enumerate(similar_docs):
            print(f"\n{i+1}. Document: {doc.title}")
            print(f"   Distance: {doc.distance:.4f}")
            print(f"   Fragment: {doc.chunk_text[:150]}..." if doc.chunk_text else "   Fragment: Not available")
        
        return similar_docs

async def list_all_documents():
    """List all documents with embeddings"""
    async with async_session() as session:
        # Get all documents that have embeddings
        query = text("""
        SELECT DISTINCT d.id, d.title, COUNT(de.id) as embedding_count
        FROM documents d
        JOIN document_embeddings de ON d.id = de.document_id
        GROUP BY d.id, d.title
        ORDER BY d.title
        """)
        
        result = await session.execute(query)
        documents = result.fetchall()
        
        print("\n--- Documents with embeddings ---")
        for i, doc in enumerate(documents):
            print(f"{i+1}. {doc.title} (ID: {doc.id}) - {doc.embedding_count} embeddings")
        
        return documents

async def main():
    # List all documents with embeddings
    await list_all_documents()
    
    # Perform example searches
    queries = [
        "What is machine learning?",
        "Applications of artificial intelligence",
        "Autonomous cars and artificial vision"
    ]
    
    for query in queries:
        await search_similar_documents(query)

if __name__ == "__main__":
    asyncio.run(main())
