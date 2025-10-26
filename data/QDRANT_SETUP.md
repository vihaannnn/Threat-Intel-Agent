# Local Qdrant Vector Database Setup 

## Prerequisites
- Docker installed and running
- OpenAI API key configured in `utils/config.py`

## Setup Steps

### Step 1: Run Data Collection
First get the OSV vulnerability data locally:
```bash
cd data
python osv_collector.py
```

This will download and filter recent vulnerabilities from npm, PyPI, Maven, Go, and Debian ecosystems.

### Step 2: Start Qdrant Server

Pull the Qdrant Docker image:
```bash
docker pull qdrant/qdrant
```

Start Qdrant:

**For Windows:**
```bash
docker run -p 6333:6333 -p 6334:6334 -v "C:\qdrant_storage:/qdrant/storage" qdrant/qdrant
```

**For Mac/Linux:**
```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
    qdrant/qdrant
```

### Step 3: Verify Qdrant is Running
Open your browser to: http://localhost:6333/dashboard

You should see the Qdrant dashboard.

### Step 4: Embed and Store Data in Qdrant
Run the setup script to generate embeddings and store them in Qdrant:
```bash
cd data
python setup_local_qdrant.py
```

This will:
- Create a collection named `osv_vulnerabilities`
- Generate embeddings using OpenAI's `text-embedding-3-small` model
- Store all vulnerability data with vectors in Qdrant
