# python-txt2utf8
A robust Python utility for converting text files to UTF-8 encoding with multithreaded batch processing capabilities and containerized deployment.

## Features
- **Core Functionality**: Convert individual .txt files to UTF-8 encoding with automatic encoding detection
- **Multithreaded Batch Processing**: Convert multiple files simultaneously using ThreadPoolExecutor with configurable worker threads
- **Chunk-based Processing**: Memory-efficient file handling by processing files in chunks
- **Progress Tracking**: Real-time progress bars for both single and batch operations
- **Containerized Deployment**: Docker support for consistent, isolated execution environments
- **Thread Pool Management**: Efficient resource utilization with worker pool concurrency
- **Fallback Encoding**: Support for common encodings when automatic detection fails

## Installation
### Using uv
```bash
git clone https://github.com/MaximPyanin/python-txt2utf8.git
cd python-txt2utf8
uv sync
```

### Using Docker
```bash
git clone https://github.com/MaximPyanin/python-txt2utf8.git
cd python-txt2utf8
make build
```

## Usage

### Command Line Interface

**Options:** `-i/--input` (file/dir), `-o/--output` (target), `--workers N` (threads), `--overwrite`, `--no-recursive`

**Single file conversion:**
```bash
python -m main -i input.txt -o output.txt
```

**Single file via Docker:**
```bash
make run MOUNTS="-v $(pwd):/work" ARGS="-i /work/input/input.txt -o /work/output --overwrite"
```

**Batch conversion:**
```bash
python -m main -i ./input_dir -o ./output_dir --workers 8
```

**Batch processing via Docker:**
```bash
make run MOUNTS="-v $(pwd):/work" ARGS="-i /work/input_dir -o /work/output_dir --workers 8 --overwrite"
```

## Architecture & Enhancement Choices

I selected two enhancements that provide the most value for real-world file processing tasks:

### 1. Batch Conversion with Progress Tracking

**Value Added:**
The batch flow now uses a plain ThreadPoolExecutor with as_completed to process many files concurrently. The progress bar updates as each future finishes, so feedback is immediate. Work is chunked per file, which keeps memory steady even on large inputs

**Risk Mitigation:**
max_workers directly limits concurrency and I/O pressure on the disk. Each file runs in its own task, so one failure does not stop the whole batch. We also keep safe encoding fallbacks to avoid hard stops when detection is uncertain and report exactly which files failed.

**Client Alignment:**
Companies need to convert thousands of files during migrations. The thread pool approach makes this practical for production use.

### 2. Containerization and Automation

**Value Added:**
Docker ensures the app works the same way on different servers. The Makefile gives simple commands for deployment. This eliminates dependency conflicts that waste development time.

**Risk Mitigation:**
Container isolation protects the host system during file operations. Frozen dependencies prevent version conflicts. This reduces debugging time in production.

**Client Alignment:**
Modern deployment uses containers. This fits with existing Kubernetes setups and CI/CD pipelines that companies already use.
