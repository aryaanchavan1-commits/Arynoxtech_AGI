"""
Arynoxtech_AGI Data Ingestion Layer
Process PDF, CSV, TXT, and other data formats
"""

import logging
import json
import csv
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class IngestedData:
    """Represents ingested data from any source"""
    id: str
    source: str
    source_type: str  # pdf, csv, txt, web, etc.
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    chunks: List[str] = field(default_factory=list)
    embeddings: Optional[List[List[float]]] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'source': self.source,
            'source_type': self.source_type,
            'content': self.content[:1000],  # Truncate for storage
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'chunk_count': len(self.chunks)
        }


class DataProcessor:
    """Base class for data processors"""
    
    def __init__(self, name: str):
        self.name = name
        self.supported_extensions: List[str] = []
    
    def can_process(self, file_path: Path) -> bool:
        """Check if this processor can handle the file"""
        return file_path.suffix.lower() in self.supported_extensions
    
    async def process(self, file_path: Path) -> IngestedData:
        """Process a file and return ingested data"""
        raise NotImplementedError


class PDFProcessor(DataProcessor):
    """Process PDF files"""
    
    def __init__(self):
        super().__init__("PDF Processor")
        self.supported_extensions = ['.pdf']
    
    async def process(self, file_path: Path) -> IngestedData:
        """Extract text from PDF"""
        content = ""
        metadata = {
            'pages': 0,
            'title': '',
            'author': '',
            'file_size': file_path.stat().st_size
        }
        
        # Try PyPDF2 first (more reliable)
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata['pages'] = len(pdf_reader.pages)
                
                if pdf_reader.metadata:
                    metadata['title'] = pdf_reader.metadata.get('/Title', '')
                    metadata['author'] = pdf_reader.metadata.get('/Author', '')
                
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        content += page_text + "\n\n"
            
            # If PyPDF2 worked, return the result
            if content.strip():
                chunks = self._create_chunks(content)
                data_id = hashlib.md5(f"{file_path}_{datetime.now()}".encode()).hexdigest()[:16]
                
                return IngestedData(
                    id=data_id,
                    source=str(file_path),
                    source_type='pdf',
                    content=content.strip(),
                    metadata=metadata,
                    chunks=chunks
                )
        except ImportError:
            logger.warning("PyPDF2 not installed, trying pdfplumber...")
        except Exception as e:
            logger.warning(f"PyPDF2 failed: {e}")
        
        # Try pdfplumber as fallback
        try:
            import pdfplumber
            
            with pdfplumber.open(file_path) as pdf:
                metadata['pages'] = len(pdf.pages)
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        content += page_text + "\n\n"
            
            if content.strip():
                chunks = self._create_chunks(content)
                data_id = hashlib.md5(f"{file_path}_{datetime.now()}".encode()).hexdigest()[:16]
                
                return IngestedData(
                    id=data_id,
                    source=str(file_path),
                    source_type='pdf',
                    content=content.strip(),
                    metadata=metadata,
                    chunks=chunks
                )
        except ImportError:
            logger.warning("pdfplumber not installed")
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
        
        # If all else fails, return minimal data
        logger.warning(f"Could not extract text from PDF: {file_path}")
        chunks = self._create_chunks(content if content else f"PDF file: {file_path.name}")
        data_id = hashlib.md5(f"{file_path}_{datetime.now()}".encode()).hexdigest()[:16]
        
        return IngestedData(
            id=data_id,
            source=str(file_path),
            source_type='pdf',
            content=content.strip() if content else f"PDF file: {file_path.name}",
            metadata=metadata,
            chunks=chunks
        )
    
    def _create_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Create overlapping chunks of text"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks


class CSVProcessor(DataProcessor):
    """Process CSV files"""
    
    def __init__(self):
        super().__init__("CSV Processor")
        self.supported_extensions = ['.csv', '.tsv']
    
    async def process(self, file_path: Path) -> IngestedData:
        """Process CSV file"""
        try:
            import pandas as pd
            
            # Detect delimiter
            delimiter = '\t' if file_path.suffix.lower() == '.tsv' else ','
            
            # Read CSV
            df = pd.read_csv(file_path, delimiter=delimiter, encoding='utf-8')
            
            # Convert to text representation
            content = self._dataframe_to_text(df)
            
            # Create chunks (one per row or grouped)
            chunks = self._create_row_chunks(df)
            
            metadata = {
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': list(df.columns),
                'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                'file_size': file_path.stat().st_size
            }
            
            data_id = hashlib.md5(f"{file_path}_{datetime.now()}".encode()).hexdigest()[:16]
            
            return IngestedData(
                id=data_id,
                source=str(file_path),
                source_type='csv',
                content=content,
                metadata=metadata,
                chunks=chunks
            )
            
        except Exception as e:
            logger.error(f"Error processing CSV {file_path}: {e}")
            raise
    
    def _dataframe_to_text(self, df) -> str:
        """Convert DataFrame to readable text"""
        text_parts = []
        
        # Add header
        text_parts.append(f"Dataset with {len(df)} rows and {len(df.columns)} columns.")
        text_parts.append(f"Columns: {', '.join(df.columns)}")
        text_parts.append("")
        
        # Add sample data
        sample_size = min(10, len(df))
        text_parts.append(f"Sample data (first {sample_size} rows):")
        text_parts.append(df.head(sample_size).to_string())
        
        # Add statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            text_parts.append("\nNumeric column statistics:")
            text_parts.append(df[numeric_cols].describe().to_string())
        
        return '\n'.join(text_parts)
    
    def _create_row_chunks(self, df, rows_per_chunk: int = 50) -> List[str]:
        """Create chunks from DataFrame rows"""
        chunks = []
        
        for i in range(0, len(df), rows_per_chunk):
            chunk_df = df.iloc[i:i + rows_per_chunk]
            chunk_text = f"Rows {i+1} to {i+len(chunk_df)}:\n"
            chunk_text += chunk_df.to_string()
            chunks.append(chunk_text)
        
        return chunks


class TXTProcessor(DataProcessor):
    """Process text files"""
    
    def __init__(self):
        super().__init__("TXT Processor")
        self.supported_extensions = ['.txt', '.md', '.log', '.json', '.xml', '.html']
    
    async def process(self, file_path: Path) -> IngestedData:
        """Process text file"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError(f"Could not decode file {file_path} with any encoding")
            
            # Create chunks
            chunks = self._create_chunks(content)
            
            metadata = {
                'file_size': file_path.stat().st_size,
                'line_count': content.count('\n'),
                'word_count': len(content.split()),
                'char_count': len(content)
            }
            
            data_id = hashlib.md5(f"{file_path}_{datetime.now()}".encode()).hexdigest()[:16]
            
            return IngestedData(
                id=data_id,
                source=str(file_path),
                source_type='txt',
                content=content,
                metadata=metadata,
                chunks=chunks
            )
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            raise
    
    def _create_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Create overlapping chunks of text"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks


class JSONProcessor(DataProcessor):
    """Process JSON files"""
    
    def __init__(self):
        super().__init__("JSON Processor")
        self.supported_extensions = ['.json']
    
    async def process(self, file_path: Path) -> IngestedData:
        """Process JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to text representation
            content = self._json_to_text(data)
            
            # Create chunks
            chunks = self._create_chunks(data)
            
            metadata = {
                'file_size': file_path.stat().st_size,
                'type': type(data).__name__,
                'keys': list(data.keys()) if isinstance(data, dict) else None,
                'length': len(data) if isinstance(data, (list, dict)) else None
            }
            
            data_id = hashlib.md5(f"{file_path}_{datetime.now()}".encode()).hexdigest()[:16]
            
            return IngestedData(
                id=data_id,
                source=str(file_path),
                source_type='json',
                content=content,
                metadata=metadata,
                chunks=chunks
            )
            
        except Exception as e:
            logger.error(f"Error processing JSON {file_path}: {e}")
            raise
    
    def _json_to_text(self, data: Any, indent: int = 0) -> str:
        """Convert JSON data to readable text"""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{'  ' * indent}{key}:")
                    lines.append(self._json_to_text(value, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}{key}: {value}")
            return '\n'.join(lines)
        elif isinstance(data, list):
            lines = []
            for i, item in enumerate(data[:10]):  # Limit to first 10 items
                lines.append(f"{'  ' * indent}[{i}]:")
                lines.append(self._json_to_text(item, indent + 1))
            if len(data) > 10:
                lines.append(f"{'  ' * indent}... and {len(data) - 10} more items")
            return '\n'.join(lines)
        else:
            return str(data)
    
    def _create_chunks(self, data: Any, max_items: int = 50) -> List[str]:
        """Create chunks from JSON data"""
        chunks = []
        
        if isinstance(data, dict):
            items = list(data.items())
            for i in range(0, len(items), max_items):
                chunk_dict = dict(items[i:i + max_items])
                chunks.append(json.dumps(chunk_dict, indent=2))
        elif isinstance(data, list):
            for i in range(0, len(data), max_items):
                chunk_list = data[i:i + max_items]
                chunks.append(json.dumps(chunk_list, indent=2))
        else:
            chunks.append(json.dumps(data, indent=2))
        
        return chunks


class DataIngestionManager:
    """
    Central data ingestion manager
    Coordinates all data processors
    """
    
    def __init__(self, data_folder: str = "data"):
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)
        
        # Initialize processors
        self.processors: List[DataProcessor] = [
            PDFProcessor(),
            CSVProcessor(),
            TXTProcessor(),
            JSONProcessor()
        ]
        
        # Store ingested data
        self.ingested_data: Dict[str, IngestedData] = {}
        self.index_file = self.data_folder / "ingestion_index.json"
        
        # Load existing index
        self._load_index()
        
        logger.info(f"Data Ingestion Manager initialized. Watching folder: {self.data_folder}")
    
    def _load_index(self):
        """Load ingestion index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    index_data = json.load(f)
                
                for data_id, data_info in index_data.items():
                    self.ingested_data[data_id] = IngestedData(
                        id=data_info['id'],
                        source=data_info['source'],
                        source_type=data_info['source_type'],
                        content=data_info['content'],
                        metadata=data_info['metadata'],
                        timestamp=datetime.fromisoformat(data_info['timestamp']),
                        chunks=data_info.get('chunks', [])
                    )
                
                logger.info(f"Loaded {len(self.ingested_data)} ingested data records")
            except Exception as e:
                logger.error(f"Error loading ingestion index: {e}")
    
    def _save_index(self):
        """Save ingestion index to disk"""
        index_data = {}
        for data_id, data in self.ingested_data.items():
            index_data[data_id] = data.to_dict()
        
        with open(self.index_file, 'w') as f:
            json.dump(index_data, f, indent=2)
    
    def get_processor(self, file_path: Path) -> Optional[DataProcessor]:
        """Get appropriate processor for a file"""
        for processor in self.processors:
            if processor.can_process(file_path):
                return processor
        return None
    
    async def ingest_file(self, file_path: Union[str, Path]) -> Optional[IngestedData]:
        """Ingest a single file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        processor = self.get_processor(file_path)
        if not processor:
            logger.warning(f"No processor found for file: {file_path}")
            return None
        
        try:
            logger.info(f"Ingesting file: {file_path}")
            data = await processor.process(file_path)
            
            self.ingested_data[data.id] = data
            self._save_index()
            
            logger.info(f"Successfully ingested: {file_path} ({len(data.chunks)} chunks)")
            return data
            
        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {e}")
            return None
    
    async def ingest_folder(self, folder_path: Optional[Union[str, Path]] = None,
                           recursive: bool = True) -> List[IngestedData]:
        """Ingest all files in a folder"""
        if folder_path is None:
            folder_path = self.data_folder
        else:
            folder_path = Path(folder_path)
        
        if not folder_path.exists():
            logger.error(f"Folder not found: {folder_path}")
            return []
        
        ingested = []
        
        # Get all files
        if recursive:
            files = list(folder_path.rglob('*'))
        else:
            files = list(folder_path.iterdir())
        
        # Filter to only files (not directories)
        files = [f for f in files if f.is_file()]
        
        logger.info(f"Found {len(files)} files to process")
        
        for file_path in files:
            # Skip hidden files and index files
            if file_path.name.startswith('.') or file_path.name == 'ingestion_index.json':
                continue
            
            data = await self.ingest_file(file_path)
            if data:
                ingested.append(data)
        
        logger.info(f"Ingested {len(ingested)} files from {folder_path}")
        return ingested
    
    async def ingest_text(self, text: str, source: str = "direct_input",
                         source_type: str = "text") -> IngestedData:
        """Ingest text directly"""
        data_id = hashlib.md5(f"{text[:100]}_{datetime.now()}".encode()).hexdigest()[:16]
        
        # Create chunks
        chunks = []
        words = text.split()
        chunk_size = 1000
        overlap = 200
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        data = IngestedData(
            id=data_id,
            source=source,
            source_type=source_type,
            content=text,
            metadata={
                'word_count': len(words),
                'char_count': len(text)
            },
            chunks=chunks
        )
        
        self.ingested_data[data_id] = data
        self._save_index()
        
        logger.info(f"Ingested text from {source}")
        return data
    
    def search(self, query: str, limit: int = 10) -> List[IngestedData]:
        """Search ingested data by content"""
        results = []
        query_lower = query.lower()
        
        for data in self.ingested_data.values():
            if query_lower in data.content.lower():
                results.append(data)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_all_data(self) -> List[IngestedData]:
        """Get all ingested data"""
        return list(self.ingested_data.values())
    
    def get_status(self) -> Dict[str, Any]:
        """Get ingestion status"""
        return {
            'data_folder': str(self.data_folder),
            'total_files_ingested': len(self.ingested_data),
            'total_chunks': sum(len(d.chunks) for d in self.ingested_data.values()),
            'source_types': list(set(d.source_type for d in self.ingested_data.values())),
            'processors_available': [p.name for p in self.processors]
        }
    
    async def watch_folder(self, interval: int = 60):
        """Watch data folder for new files and ingest them"""
        logger.info(f"Starting folder watch on {self.data_folder} (interval: {interval}s)")
        
        while True:
            try:
                # Get current files
                current_files = set()
                for file_path in self.data_folder.rglob('*'):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        current_files.add(file_path)
                
                # Get already ingested files
                ingested_sources = set(d.source for d in self.ingested_data.values())
                
                # Find new files
                new_files = [f for f in current_files if str(f) not in ingested_sources]
                
                if new_files:
                    logger.info(f"Found {len(new_files)} new files to ingest")
                    for file_path in new_files:
                        await self.ingest_file(file_path)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in folder watch: {e}")
                await asyncio.sleep(interval)
