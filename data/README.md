# OSV Vulnerability Data Collection for RAG Chatbot

## What is OSV.dev?

[OSV (Open Source Vulnerabilities)](https://osv.dev/) is a comprehensive, distributed vulnerability database for open source software. It aggregates security advisories from multiple authoritative sources and provides a unified platform to access vulnerability information across different programming language ecosystems and platforms.

### Key Features of OSV Data:
- **Structured vulnerability information**: CVE IDs, descriptions, affected versions
- **Affected package details**: Specific versions and version ranges
- **Remediation guidance**: Links to patches, security advisories, and fixes
- **Cross-ecosystem coverage**: Supports 20+ package ecosystems
- **Bulk data exports**: Complete ecosystem datasets available via Google Cloud Storage

## Why These Ecosystems?

We selected **5 core ecosystems** that represent the most common technology stacks in enterprise environments:

| Ecosystem | Description | Why It Matters |
|-----------|-------------|----------------|
| **npm** | JavaScript/Node.js packages | Powers modern web applications, backend services, and serverless functions |
| **PyPI** | Python packages | Widely used in data science, ML/AI, automation, and web frameworks (Django/Flask) |
| **Maven** | Java packages | Foundation of enterprise applications, Android development, and legacy systems |
| **Go** | Go modules | Modern cloud-native infrastructure, container orchestration (Kubernetes), and microservices |
| **Debian** | Linux distribution packages | Server infrastructure, containers, and cloud instances run on Debian-based systems (Ubuntu, etc.) |

### Coverage Rationale:
- **Web Applications**: npm (frontend/backend JavaScript), PyPI (Python frameworks)
- **Enterprise Systems**: Maven (Java enterprise applications), Debian (server OS)
- **Cloud Infrastructure**: Go (cloud-native tools), Debian (container base images)

This selection ensures our chatbot can answer security questions relevant to **90%+ of modern software organizations**.

## Data Collection Strategy

### Filtering: Recency-Based (Last 3 Years)

We focus on **recently published vulnerabilities** from the last 3 years because:

1. **Relevance**: Organizations care about vulnerabilities affecting currently-maintained software versions
2. **Actionable**: Recent vulnerabilities are more likely to impact production systems
3. **Manageable Size**: 3 years provides comprehensive coverage while keeping the dataset size reasonable for local RAG
4. **Active Threats**: Recent vulnerabilities are what attackers actively exploit


### Target Dataset Size
- **~3,000-5,000 vulnerabilities per ecosystem** (depending on ecosystem activity)
- **Total: ~15,000-25,000 recent vulnerabilities**

## How OSV Bulk Data Exports Are Used

### Data Source

OSV provides **bulk data exports** for each ecosystem via Google Cloud Storage:
```
https://osv-vulnerabilities.storage.googleapis.com/<ECOSYSTEM>/all.zip
```

Each zip file contains:
- Individual JSON files for every vulnerability in that ecosystem
- Complete vulnerability data (no API pagination needed)
- Updated regularly (typically daily)

### Collection Process

1. **Download Ecosystem Data**
   ```python
   # Download complete ecosystem dataset
   GET https://osv-vulnerabilities.storage.googleapis.com/npm/all.zip
   ```
   - Downloads zip file containing all npm vulnerabilities
   - Typical sizes: 10-100MB depending on ecosystem

2. **Extract and Parse**
   ```python
   # Extract zip in-memory
   with zipfile.ZipFile(response.content) as zip_file:
       for json_file in zip_file.namelist():
           vulnerability = json.load(json_file)
   ```
   - Parses each JSON file individually
   - Loads complete vulnerability records

3. **Apply Recency Filter**
   ```python
   # Filter by publication date
   if published_date >= cutoff_date:  # Last 3 years
       # Keep this vulnerability
   ```
   - Parse `published` date from vulnerability record
   - Compare to 3-year cutoff date
   - Exclude withdrawn vulnerabilities

4. **Format for RAG**
   - **Content** (for embedding): Summary, detailed description, affected packages
   - **Metadata** (for filtering): All other fields including ecosystem, dates, package details, severity info (as-is)


## Data Structure for RAG

Each collected vulnerability is formatted as:

```json
{
  "content": "Summary\n\nNon-empty default inheritable capabilities for linux container in Buildah\n\nA bug was found in Buildah where containers were created with non-empty default inheritable Linux capabilities...\n\nDetails:...\n\nAffects: github.com/containers/buildah",
  
  "metadata": {
    "id": "GHSA-c3g4-w6cv-6v7h",
    "aliases": ["CVE-2022-27651"],
    "schema_version": "1.3.0",
    "ecosystem": "Go",
    "published": "2022-04-01T13:56:42Z",
    "modified": "2022-04-01T13:56:42Z",
    "withdrawn": null,
    "severity": [
      {
        "type": "CVSS_V3",
        "score": "8.5"
      }
    ],
    "affected": [
      {
        "package": {
          "name": "github.com/containers/buildah",
          "ecosystem": "Go",
          "purl": "pkg:golang/github.com/containers/buildah"
        },
        "ranges": [
          {
            "type": "SEMVER",
            "events": [
              {"introduced": "0"},
              {"fixed": "1.25.0"}
            ]
          }
        ],
        "versions": ["1.24.0", "1.24.1"],
        "database_specific": {},
        "ecosystem_specific": {}
      }
    ],
    "references": [
      {
        "type": "WEB",
        "url": "https://github.com/containers/buildah/commit/..."
      },
      {
        "type": "PACKAGE",
        "url": "https://github.com/containers/buildah"
      }
    ],
    "credits": [],
    "database_specific": {},
    "related": []
  }
}
```

### Why This Structure?

#### Content Field (For Semantic Search)
- **Summary**: Natural language vulnerability title
- **Details**: In-depth technical description
- **Affected packages**: Package names for context

#### Metadata Fields (For Filtering and Context)
- **`metadata.ecosystem`**: Filter by technology stack ("Show me Python vulnerabilities")
- **`metadata.published`**: Time-based filtering ("vulnerabilities from 2024")
- **`metadata.affected`**: Complete package and version information
  - Package names, ecosystems, PURLs
  - Version ranges with introduced/fixed events
  - Specific vulnerable versions
- **`metadata.severity`**: Original severity data (stored as-is, not standardized)
- **`metadata.references`**: Links to advisories, patches, and documentation
- **`metadata.aliases`**: Alternative IDs (CVE, GHSA, etc.)

## Usage

### Prerequisites

```bash
pip install requests
```

### Running the Collector

```bash
cd data
python osv_collector.py
```

### Output

The script creates an `osv_data/` directory containing:

```
osv_data/
├── npm_vulnerabilities.json          # ~3,000-5,000 npm vulnerabilities
├── PyPI_vulnerabilities.json         # ~3,000-5,000 Python vulnerabilities
├── Maven_vulnerabilities.json        # ~2,000-4,000 Java vulnerabilities
├── Go_vulnerabilities.json           # ~2,000-4,000 Go vulnerabilities
├── Debian_vulnerabilities.json       # ~3,000-5,000 Linux vulnerabilities
└── collection_summary.json           # Statistics and metadata
```