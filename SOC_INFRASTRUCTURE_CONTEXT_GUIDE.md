# SOC Infrastructure Context Guide

> **Note:** This guide was generated using Cursor AI (Claude) to assist with security infrastructure context examples for the Threat Intelligence Agent chatbot.

## Recommended Inputs for Security Operations Center (SOC)

### 1. OS Versions

**Format:** Operating System name and version

**SOC Examples:**
```
Ubuntu 22.04 LTS
Ubuntu 20.04 LTS
Windows Server 2022
Windows Server 2019
Windows 11 Enterprise
Windows 10 Pro
Red Hat Enterprise Linux 9
CentOS Stream 9
Debian 12
macOS 14 Sonoma
macOS 13 Ventura
```

**For your questions:**
- **Authentication bypass vulnerabilities**: Include all OS versions in your environment to see platform-specific auth bypass CVEs
- **Python RCE vulnerabilities**: Include Linux/Unix versions since Python is commonly deployed there

**Why it matters:** The bot filters Debian/Ubuntu vulnerabilities based on OS versions you specify.

---

### 2. Services/Applications

**Format:** Service name (optionally with version)

**SOC Examples:**
```
nginx 1.24.0
Apache HTTP Server 2.4.57
IIS 10.0
PostgreSQL 15.3
MySQL 8.0.33
Microsoft SQL Server 2022
Active Directory Domain Services
Microsoft Exchange Server 2019
Docker Engine 24.0
Kubernetes 1.28
Elasticsearch 8.11.0
Splunk Enterprise 9.0
Fortinet FortiGate
Palo Alto Networks PAN-OS
Okta Identity Provider
AWS Lambda
Azure Active Directory
```

**For your questions:**
- **Authentication bypass vulnerabilities**: 
  - Include authentication services: `Okta`, `Active Directory`, `Keycloak`, `Auth0`
  - Include web servers: `nginx`, `Apache`, `IIS` (auth bypass can occur at web layer)
  - Include SSO providers: `SAML`, `OAuth2`, `LDAP`
  
- **Python RCE vulnerabilities**: 
  - Include Python web frameworks: `Django`, `Flask`, `FastAPI`
  - Include API services: `REST APIs`, `GraphQL`
  - Include data processing: `Apache Airflow`, `Celery`

**Why it matters:** The bot can correlate service vulnerabilities with your infrastructure to identify actual risks.

---

### 3. Packages/Dependencies

**Format:** `ecosystem:package:version` or just `package:version`

**SOC Examples:**
```
npm:express:4.18.2
npm:lodash:4.17.21
npm:react:18.2.0
PyPI:requests:2.31.0
PyPI:Django:4.2.0
PyPI:Flask:2.3.0
PyPI:pandas:2.0.3
PyPI:numpy:1.24.3
PyPI:urllib3:2.0.4
Maven:spring-boot:2.7.8
Maven:apache-commons:3.12.0
Go:golang.org/x/crypto:v0.17.0
Go:github.com/gin-gonic/gin:v1.9.1
```

**For your questions:**
- **Authentication bypass vulnerabilities**:
  ```
  npm:passport:0.6.0
  npm:jsonwebtoken:9.0.2
  PyPI:Flask-Login:0.6.3
  PyPI:Django-Auth:4.2.0
  Maven:spring-security:5.8.0
  Maven:shiro:1.11.0
  Go:golang.org/x/oauth2:v0.15.0
  ```

- **Python RCE vulnerabilities**:
  ```
  PyPI:pickle:any
  PyPI:yaml:6.0
  PyPI:Jinja2:3.1.2
  PyPI:paramiko:3.3.1
  PyPI:subprocess32:3.5.4
  PyPI:Django:4.0.0
  PyPI:Flask:2.0.0
  ```

**Why it matters:** The bot searches by ecosystem (npm, PyPI, Maven, Go, Debian) and matches package names to find CVEs affecting your versions.

---

### 4. Network Information

**Format:** Free text describing network architecture and exposure

**SOC Examples:**
```
Internet-exposed web servers (DMZ)
Internal network only
VPN-accessible endpoints
Cloud-hosted services (AWS/Azure)
Edge computing nodes
Kubernetes cluster exposed via ingress
Load balancers with public IPs
CDN endpoints (CloudFront, Cloudflare)
API gateways (public-facing)
Database servers (internal network only)
Container orchestration platform (Kubernetes)
Multi-cloud infrastructure (AWS + Azure)
Hybrid cloud (on-prem + AWS)
Zero-trust network architecture
```

**For your questions:**
- **Authentication bypass vulnerabilities**:
  ```
  Internet-exposed authentication endpoints
  Public-facing SSO portals
  External-facing API authentication
  DMZ-hosted identity providers
  ```

- **Python RCE vulnerabilities**:
  ```
  Internet-exposed Python web applications
  Public-facing REST APIs built with Python
  Cloud-hosted Python services (AWS Lambda, Azure Functions)
  Edge devices running Python applications
  ```

**Why it matters:** Network exposure determines exploitability. Internet-exposed services have higher priority for remediation.

---

## Enhanced Questions with Infrastructure Context

### Example 1: Authentication Bypass Vulnerabilities

**Without context:**
> "Show me authentication bypass vulnerabilities across various ecosystems"

**With SOC infrastructure context:**
> "Show me authentication bypass vulnerabilities affecting my infrastructure: Okta, Active Directory, nginx 1.24, and Python Flask applications. Our authentication endpoints are internet-exposed."

**Infrastructure to add:**
- **OS Versions:** Ubuntu 22.04, Windows Server 2022
- **Services:** Okta, Active Directory, nginx 1.24.0, Flask
- **Packages:** PyPI:Flask-Login:0.6.3, npm:passport:0.6.0, Maven:spring-security:5.8.0
- **Network:** Internet-exposed authentication endpoints, public-facing SSO portals

---

### Example 2: Python RCE Vulnerabilities

**Without context:**
> "What Python packages have RCE vulnerabilities?"

**With SOC infrastructure context:**
> "What Python packages have RCE vulnerabilities? We use Django 4.2, Flask 2.3, pandas 2.0, and requests 2.31.0. Our Python services run on Ubuntu 22.04 and are internet-exposed via nginx reverse proxy."

**Infrastructure to add:**
- **OS Versions:** Ubuntu 22.04 LTS
- **Services:** nginx 1.24.0, Django, Flask
- **Packages:** 
  - PyPI:Django:4.2.0
  - PyPI:Flask:2.3.0
  - PyPI:pandas:2.0.3
  - PyPI:requests:2.31.0
  - PyPI:urllib3:2.0.4
  - PyPI:Jinja2:3.1.2
- **Network:** Internet-exposed Python web applications, public-facing REST APIs

---

## SOC Workflow Recommendations

### Initial Setup (One-time)
1. **Add all OS versions** in your environment (servers, workstations, endpoints)
2. **Add critical services** (web servers, databases, authentication, monitoring)
3. **Add commonly used packages** by ecosystem (top 20-30 most used)
4. **Document network zones** (DMZ, internal, cloud, edge)

### Per-Incident Analysis
1. **Update packages** for the specific application/service in question
2. **Add relevant services** that interact with the vulnerable component
3. **Specify network exposure** for the affected system
4. **Refine OS versions** if incident is OS-specific

### Continuous Monitoring
- Update package versions monthly (or after major deployments)
- Add new services as they're deployed
- Update network info when architecture changes
- Remove deprecated services/packages

---

## Example SOC Infrastructure Context

**Complete example for a typical SOC environment:**

```
OS Versions:
Ubuntu 22.04 LTS, Ubuntu 20.04 LTS, Windows Server 2022, Windows Server 2019, Windows 11 Enterprise

Services/Applications:
nginx 1.24.0, Apache HTTP Server 2.4.57, PostgreSQL 15.3, MySQL 8.0.33, Active Directory Domain Services, Okta Identity Provider, Kubernetes 1.28, Docker Engine 24.0, Splunk Enterprise 9.0

Packages/Dependencies:
npm:express:4.18.2, npm:react:18.2.0, PyPI:Django:4.2.0, PyPI:Flask:2.3.0, PyPI:requests:2.31.0, PyPI:pandas:2.0.3, Maven:spring-boot:2.7.8, Maven:spring-security:5.8.0, Go:golang.org/x/crypto:v0.17.0

Network Information:
Internet-exposed web servers (DMZ), Internal network databases, VPN-accessible endpoints, Kubernetes cluster exposed via ingress, Cloud-hosted services (AWS/Azure)
```

---

## Tips for Maximum Effectiveness

1. **Be specific with versions** - The bot matches vulnerabilities to exact version ranges
2. **Include all ecosystems** you use - npm, PyPI, Maven, Go, Debian
3. **Don't forget system packages** - Debian/Ubuntu packages are often critical
4. **Update regularly** - Infrastructure changes should be reflected in context
5. **Focus on internet-exposed** - Prioritize those in network information
6. **Include dependencies** - Not just direct packages, but transitive dependencies too

---

## Questions Enhanced by Context

### Better Question Format:
> "Show me [vulnerability type] affecting [specific infrastructure components]. Our [service/package] version is [X.Y.Z] and it's [network exposure]."

**Examples:**
- "Show me authentication bypass vulnerabilities affecting our Okta SSO, Active Directory on Windows Server 2022, and Flask applications using Flask-Login 0.6.3. Our authentication endpoints are internet-exposed."
- "What remote code execution vulnerabilities affect our Python stack running Django 4.2 and Flask 2.3 on Ubuntu 22.04? These applications are behind nginx 1.24 and are internet-facing."
- "Find denial of service vulnerabilities in our Debian 12 servers, MySQL 8.0.33, and Express.js 4.18.2 applications. Database is internal-only, web servers are in DMZ."


