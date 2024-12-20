import sys
from pathlib import Path

# Add the project root directory to the Python path
sys.path.append(str('/home/ngoan/cakespace/bio/nlp/nlp_git/'))

import asyncio
import os
from tqdm import tqdm
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import tiktoken
from PyPDF2 import PdfReader
from tqdm.asyncio import tqdm_asyncio
from api.core.config import settings
from api.core.vector_db import get_vector_db, CollectionConfig, VectorDBException

class DocumentChunk(BaseModel):
    content: str
    metadata: Dict[str, Any]

class ProcessingConfig(BaseModel):
    chunk_size: int = 512
    chunk_overlap: int = 50
    supported_extensions: List[str] = Field(default=['.pdf', '.txt', '.md'])
    skip_empty_chunks: bool = True
    embedding_batch_size: int = 32
    embedding_service_url: str = "http://localhost:8002/embed"

class EmbeddingService:
    def __init__(self, service_url: str, batch_size: int = 32):
        self.service_url = service_url
        self.batch_size = batch_size
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self.client.post(
                self.service_url,
                json={"texts": texts, "batch_size": self.batch_size}
            )
            response.raise_for_status()
            return response.json()["embeddings"]
        except Exception as e:
            raise RuntimeError(f"Embedding service error: {str(e)}")

class DocumentProcessor:
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def create_chunks(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        tokens = self.tokenizer.encode(text)
        chunks = []
        i = 0
        
        while i < len(tokens):
            chunk_tokens = tokens[i:i + self.config.chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            if not (self.config.skip_empty_chunks and chunk_text.isspace()):
                chunks.append(DocumentChunk(
                    content=chunk_text,
                    metadata={
                        **metadata,
                        "chunk_index": len(chunks),
                        "token_count": len(chunk_tokens)
                    }
                ))
            
            i += (self.config.chunk_size - self.config.chunk_overlap)
        
        return chunks

    async def process_file(self, file_path: Path) -> List[DocumentChunk]:
        if not file_path.suffix.lower() in self.config.supported_extensions:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        try:
            if file_path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as file:
                    pdf = PdfReader(file)
                    text = '\n'.join(
                        page.extract_text().strip()
                        for page in pdf.pages
                        if page.extract_text().strip()
                    )
            else:
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()

            base_metadata = {
                'title': file_path.stem,
                'file_path': str(file_path),
                'file_type': file_path.suffix.lower(),
                'file_size': os.path.getsize(file_path),
                'created_at': os.path.getctime(file_path),
                'modified_at': os.path.getmtime(file_path),
            }

            return self.create_chunks(text, base_metadata)
            
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            return []

class DocumentIngester:
    def __init__(
        self,
        collection_name: str,
        embedding_dimension: int = 384,  # Dimension for all-MiniLM-L6-v2
        processing_config: Optional[ProcessingConfig] = None
    ):
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        self.vector_db = get_vector_db()
        self.processor = DocumentProcessor(processing_config or ProcessingConfig())
        self.embedding_service = EmbeddingService(
            self.processor.config.embedding_service_url,
            self.processor.config.embedding_batch_size
        )

    async def create_collection(self) -> bool:
        try:
            config = CollectionConfig(
                name=self.collection_name,
                dimension=self.embedding_dimension,
                distance="cosine",
                metadata_schema={
                    "title": "string",
                    "file_path": "string",
                    "file_type": "string",
                    "chunk_index": "integer",
                    "token_count": "integer",
                    "file_size": "integer",
                    "created_at": "float",
                    "modified_at": "float"
                }
            )
            
            return self.vector_db.create_collection(config)
        
        except VectorDBException as e:
            print(f"Failed to create collection: {str(e)}")
            return False

    async def process_documents(self, directory: str) -> List[DocumentChunk]:
            chunks = []
            files = []
            
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = Path(root) / filename
                    if file_path.suffix.lower() in self.processor.config.supported_extensions:
                        files.append(file_path)

            if not files:
                print(f"No supported files found in {directory}")
                return chunks

            print(f"Processing {len(files)} files...")
            chunks = []
            with tqdm(total=len(files), desc="Processing files") as pbar:
                for file_path in files:
                    file_chunks = await self.processor.process_file(file_path)
                    chunks.extend(file_chunks)
                    pbar.update(1)
                    await asyncio.sleep(0.01)  # Small delay to allow progress bar updates

            return chunks

    async def get_embeddings_batched(self, chunks: List[DocumentChunk]) -> List[List[float]]:
        embeddings = []
        batch_size = self.processor.config.embedding_batch_size
        
        print(f"Generating embeddings for {len(chunks)} chunks...")
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        with tqdm(total=total_batches, desc="Generating embeddings") as pbar:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                try:
                    batch_embeddings = await self.embedding_service.get_embeddings(
                        [chunk.content for chunk in batch]
                    )
                    embeddings.extend(batch_embeddings)
                    pbar.update(1)
                    # Add a small delay to allow the progress bar to update
                    await asyncio.sleep(0.01)
                except Exception as e:
                    print(f"Error generating embeddings for batch {i//batch_size}: {str(e)}")
                    embeddings.extend([[0.0] * self.embedding_dimension] * len(batch))
        
        return embeddings

    
    async def ingest(self, directory: str) -> bool:
        try:
            # Ensure collection exists
            if not self.vector_db.collection_exists(self.collection_name):
                print(f"Creating collection {self.collection_name}...")
                if not await self.create_collection():
                    return False

            # Process documents
            chunks = await self.process_documents(directory)
            if not chunks:
                return False

            print(f"Found {len(chunks)} chunks to process")

            # Generate embeddings
            embeddings = await self.get_embeddings_batched(chunks)

            # Prepare documents for vector DB
            documents = []
            for chunk in chunks:
                documents.append({
                    "content": chunk.content,
                    "title": chunk.metadata.get("title", ""),
                    "file_path": chunk.metadata.get("file_path", ""),
                    "file_type": chunk.metadata.get("file_type", ""),
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                    "token_count": chunk.metadata.get("token_count", 0),
                    "file_size": chunk.metadata.get("file_size", 0),
                    "created_at": chunk.metadata.get("created_at", 0.0),
                    "modified_at": chunk.metadata.get("modified_at", 0.0)
                })

            # Add to vector DB
            print(f"Adding {len(documents)} chunks to vector database...")
            self.vector_db.add_documents(
                collection_name=self.collection_name,
                documents=documents,
                embeddings=embeddings
            )
            
            print(f"Successfully ingested {len(documents)} chunks from {directory}")
            return True

        except Exception as e:
            print(f"Error during ingestion: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest documents into vector database')
    parser.add_argument('directory', default='documents', help='Directory containing documents to ingest')
    parser.add_argument('--collection', default='documents_test_2', help='Collection name')
    parser.add_argument('--chunk-size', type=int, default=512, help='Chunk size in tokens')
    parser.add_argument('--chunk-overlap', type=int, default=50, help='Chunk overlap in tokens')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for embeddings')
    parser.add_argument('--embedding-url', default='http://localhost:8002/embed', 
                       help='URL for the embedding service')
    
    args = parser.parse_args()

    config = ProcessingConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        embedding_batch_size=args.batch_size,
        embedding_service_url=args.embedding_url
    )
    
    ingester = DocumentIngester(
        collection_name=args.collection,
        embedding_dimension=384,  # all-MiniLM-L6-v2 dimension
        processing_config=config
    )
    
    success = await ingester.ingest(args.directory)
    
    if not success:
        print("Ingestion failed")
        return 1
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))