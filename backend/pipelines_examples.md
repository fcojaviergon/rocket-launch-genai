# Example 1: Basic Text Extraction and Embedding Pipeline
pipeline_basic = {
    "name": "Basic Embedding Pipeline",
    "description": "Extracts text from documents and generates embeddings for semantic search.",
    "steps": [
        {
            "processor_type": "text_extraction",
            "config": {} # Default configuration
        },
        {
            "processor_type": "embedding",
            "config": {
                "model": "text-embedding-3-small", # Specify model
                "chunk_size": 512,                 # Smaller chunks for potentially better granularity
                "chunk_overlap": 100
            }
        }
    ],
    # Optional: You might add metadata like version or creator
    "version": "1.0",
    "created_by": "system"
}

# Example 2: Extraction, Summary, and Keywords Pipeline
pipeline_analysis = {
    "name": "Content Analysis Pipeline",
    "description": "Extracts text, summarizes content, and identifies keywords.",
    "steps": [
        {
            "processor_type": "text_extraction",
            "config": {}
        },
        {
            "processor_type": "summarizer",
            "config": {
                "model": "gpt-4o-mini", # Specify a capable model for summarization
                "max_chunk_tokens": 10000 # Adjust based on document size and model context limits
            }
        },
        {
            "processor_type": "keyword_extraction",
            "config": {
                "model": "gpt-3.5-turbo", # Can use a faster model for keyword extraction
                "max_keywords": 15        # Extract more keywords
            }
        }
    ],
    "version": "1.1",
    "created_by": "system"
}

# Example 3: Full Pipeline (Extraction, Summary, Keywords, Sentiment, Embedding)
pipeline_full = {
    "name": "Comprehensive Document Pipeline",
    "description": "Performs text extraction, summarization, keyword extraction, sentiment analysis, and embedding generation.",
    "steps": [
        {
            "processor_type": "text_extraction",
            "config": {}
        },
        {
            "processor_type": "summarizer",
            "config": {"model": "gpt-4o-mini"}
        },
        {
            "processor_type": "keyword_extraction",
            "config": {"max_keywords": 10} # Default keyword count
        },
        {
            "processor_type": "sentiment_analysis",
            "config": {"model": "gpt-3.5-turbo"} # Faster model might suffice
        },
        {
            "processor_type": "embedding",
            "config": {
                "model": "text-embedding-3-large", # Higher quality embedding model
                "chunk_size": 1024,
                "chunk_overlap": 150
            }
        }
    ],
    "version": "2.0",
    "created_by": "system"
}

# Example 4: Extraction and Embedding with specific settings
pipeline_custom_embedding = {
    "name": "Large Chunk Embedding Pipeline",
    "description": "Extracts text and uses larger chunks for embedding, potentially better for overview context.",
    "steps": [
        {
            "processor_type": "text_extraction",
            "config": {}
        },
        {
            "processor_type": "embedding",
            "config": {
                "model": "text-embedding-3-small", # Cost-effective model
                "chunk_size": 2000,               # Larger chunk size
                "chunk_overlap": 200              # Maintain some overlap
            }
        }
    ],
    "version": "1.0",
    "created_by": "system"
}

# Example 5: Analysis Focused (No Embedding)
pipeline_no_embedding = {
    "name": "Text Analysis Only Pipeline",
    "description": "Extracts text, summarizes, finds keywords, and analyzes sentiment without generating embeddings.",
    "steps": [
        {
            "processor_type": "text_extraction",
            "config": {}
        },
        {
            "processor_type": "summarizer",
            "config": {"model": "gpt-4o-mini"}
        },
        {
            "processor_type": "keyword_extraction",
            "config": {"max_keywords": 10}
        },
        {
            "processor_type": "sentiment_analysis",
            "config": {}
        }
        # Note: No embedding step
    ],
    "version": "1.0",
    "created_by": "system"
}

# How to use:
# These dictionaries (likely serialized as JSON) would be stored in a database table
# dedicated to pipeline definitions. When processing a document, you would fetch the
# desired pipeline definition by its name or ID and then instantiate the processors
# dynamically based on the 'steps' list.