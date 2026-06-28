# Architecture Definition Language — Axiom Platform

This file defines the complete Architecture Definition Language (ADL)
specification for the Axiom platform. Each ADL block encodes a structural
constraint derived from the architecture governance rules in `ARCHITECTURE.md`.
Blocks are machine-readable pseudo-code following the Mark Richards ADL
specification published at
[developertoarchitect.com/downloads/adl-ref.pdf](https://developertoarchitect.com/downloads/adl-ref.pdf).

## Specification reference

Keywords used in this document:
`DEFINE SYSTEM`, `DEFINE DOMAIN`, `DEFINE SUBDOMAIN`, `DEFINE COMPONENT`,
`DEFINE LIBRARY`, `DEFINE SERVICE`, `DEFINE CONST`, `ASSERT`, `FOREACH...END`,
`CLASSES`, `DOMAINS`, `SUBDOMAINS`, `COMPONENTS`, `SERVICES`,
`CONTAINED WITHIN`, `CONTAINS`, `DEPENDS ON`, `DEPENDENCY ON`,
`NO DEPENDENCY ON`, `EXCLUSIVELY`.

No keywords beyond this published set are used anywhere in this document.

Each block carries three metadata fields:

- `REQUIRES` — tooling needed to execute the generated test
- `DESCRIPTION` — plain-language description of the constraint
- `PROMPT` — the LLM instruction used to generate the fitness function

Strip all three metadata lines before sending a block to an LLM.
Use only the `PROMPT` text as the user instruction together with the
stripped pseudo-code.

## How to use these blocks

1. **Strip metadata.** Remove `REQUIRES`, `DESCRIPTION`, and `PROMPT` lines.
2. **Send to LLM.** Pass the stripped pseudo-code with the `PROMPT` as the user instruction.
3. **Install tooling.** The `REQUIRES` line names the exact tooling needed:
   - **ArchUnit Java library** — Java architectural tests using JUnit 5 and ArchUnit 1.x
   - **PyTestArch Python library** — Python architectural tests using pytest and pytestarch
   - **ESLint with import plugin** — TypeScript import boundary rules using eslint-plugin-import
   - **Custom fitness function via Semgrep** — pattern-based security rules in Semgrep YAML format
   - **Custom fitness function via grep** — CI-level bash scripts for GitHub Actions
   - **Custom fitness function via pytest** — behavioural contract tests using pytest
4. **Apply enforcement.** Hard blocks must fail the CI build on violation. Soft blocks emit warnings.

## Platform topology

| Service | Namespace / Module | Port | Stack | Status |
|---------|-------------------|------|-------|--------|
| axiom-ui | axiom-ui/src | 3000 | React 18 + Vite | Active |
| axiom-api | com.axiom.api | 8080 | Spring Boot WebFlux | Active |
| archon-api | com.archon.api | 8081 | Spring Boot | Active |
| archon-agent | app (archon-agent/) | 8001 | FastAPI + LangGraph | Active |
| specweaver-api | com.specweaver.api | 8082 | Spring Boot | Active |
| specweaver-agent | app (specweaver-agent/) | 8085 | FastAPI + LangGraph | Active |
| lens-api | com.lens.api | 8083 | Spring Boot | Active |
| lens-agent | app (lens-agent/) | 8086 | FastAPI + LangGraph | Active |

All external traffic enters through **axiom-api**. Each pillar owns its own
PostgreSQL database. Cross-pillar communication is HTTP only.

## Service index

| Block ID | Service | Description | Tooling | Enforcement |
|----------|---------|-------------|---------|-------------|
| ADL-001 | Cross-service | System and service boundaries | grep | Soft |
| ADL-002 | axiom-api | Gateway domain structure | ArchUnit | Soft |
| ADL-003 | axiom-api | Gateway route isolation | ArchUnit | Soft |
| ADL-004 | axiom-api | LLM call prohibition | ArchUnit | Hard |
| ADL-005 | axiom-api | RestTemplate prohibition | ArchUnit | Hard |
| ADL-006 | axiom-api | Filter domain isolation | ArchUnit | Soft |
| ADL-007 | axiom-api | Database access boundary | ArchUnit | Hard |
| ADL-008 | archon-agent | Domain structure | PyTestArch | Soft |
| ADL-009 | archon-agent | Pipeline domain components | PyTestArch | Soft |
| ADL-010 | archon-agent | Tools domain components | PyTestArch | Soft |
| ADL-011 | archon-agent | Tool dependency rule | PyTestArch | Soft |
| ADL-012 | archon-agent | Pipeline nodes dependency | PyTestArch | Soft |
| ADL-013 | archon-agent | LLM domain isolation | PyTestArch | Hard |
| ADL-014 | archon-agent | Memory domain isolation | PyTestArch | Hard |
| ADL-015 | archon-agent | Prompt template isolation | grep | Soft |
| ADL-016 | archon-agent | ArchitectureContext ownership | PyTestArch | Soft |
| ADL-017 | archon-agent | API domain boundary | PyTestArch | Soft |
| ADL-018 | archon-agent | Stage event contract | grep | Soft |
| ADL-019 | All agents | Secret prohibition | Semgrep | Hard |
| ADL-020 | axiom-ui | Domain structure | ESLint | Soft |
| ADL-021 | axiom-ui | API call boundary | ESLint | Soft |
| ADL-022 | axiom-ui | State management boundary | ESLint | Soft |
| ADL-023 | axiom-ui | Token storage prohibition | grep | Hard |
| ADL-024 | All agents | Database access prohibition | PyTestArch | Hard |
| ADL-025 | axiom-api/archon-api | Qdrant access prohibition | ArchUnit | Hard |
| ADL-026 | Cross-service | Tactic entity domain isolation | grep | Hard |
| ADL-027 | archon-api | Tactic write path enforcement | grep | Hard |
| ADL-028 | archon-agent | Tactic catalog enforcement | Semgrep | Hard |
| ADL-033 | Infra | HTTPS enforcement on ingress | grep | Hard |
| ADL-034 | archon-agent | Structured output schema | pytest | Hard |
| ADL-035 | archon-agent | Single repair attempt | pytest | Hard |
| ADL-036 | archon-agent | Supporting stage resilience | pytest | Hard |
| ADL-057 | archon-api | Workshop session boundary | bash | Hard |
| ADL-058 | archon-agent | Workshop module isolation | pytest + bash | Hard |
| ADL-059 | archon-api | Password reset token security | grep | Hard |
| ADL-060 | archon-agent | Utility tree threshold | pytest | Hard |
| ADL-061 | archon-agent | Implication format | pytest | Hard |
| ADL-062 | archon-agent | Implication mechanism prohibition | grep | Hard |
| ADL-063 | archon-api | Send-to-pipeline attributes | ArchUnit | Hard |
| ADL-064 | archon-api/ui | Idempotency key | grep | Hard |
| ADL-065 | archon-agent | Scenario deduplication | PyTestArch | Hard |
| ADL-069 | archon-agent | LLM provider abstraction | PyTestArch | Hard |
| ADL-070 | archon-agent | stage_name on LLM calls | grep | Hard |
| ADL-071 | axiom-api/archon-api | Gateway JWT validation | ArchUnit | Hard |
| ADL-072 | Cross-pillar | Pillar import isolation | PyTestArch | Hard |
| ADL-073 | Platform | Two services per pillar | bash | Hard |
| ADL-087 | lens-api | Domain structure | ArchUnit | Hard |
| ADL-088 | lens-api | LLM call prohibition | ArchUnit | Hard |
| ADL-089 | lens-api | RestTemplate prohibition | ArchUnit | Hard |
| ADL-090 | lens-agent | Domain structure | PyTestArch | Hard |
| ADL-091 | lens-agent | LLM domain isolation | PyTestArch | Hard |
| ADL-092 | lens-agent | Database access prohibition | PyTestArch | Hard |
| ADL-093 | lens-agent | Gap elicitation never blocks user | pytest | Hard |
| ADL-094 | lens-agent | Risk and recommendation caps | pytest | Hard |
| ADL-074 | specweaver-api | Domain structure | ArchUnit | Soft |
| ADL-075 | specweaver-api | Database access boundary | ArchUnit | Hard |
| ADL-076 | specweaver-api | LLM call prohibition | ArchUnit | Hard |
| ADL-077 | specweaver-api | RestTemplate prohibition | ArchUnit | Hard |
| ADL-078 | specweaver-agent | Domain structure | PyTestArch | Soft |
| ADL-079 | specweaver-agent | LLM domain isolation | PyTestArch | Hard |
| ADL-080 | specweaver-agent | Database access prohibition | PyTestArch | Hard |
| ADL-081 | specweaver-agent | Qdrant cleanup contract | pytest | Hard |
| ADL-082 | specweaver-agent | Extraction guard contract | pytest | Hard |
| ADL-083 | specweaver-agent | Conflict preservation | pytest | Hard |
| ADL-084 | specweaver-api | Upload size limit enforcement | ArchUnit | Hard |
| ADL-085 | axiom-api | Auth route coverage | ArchUnit | Hard |
| ADL-086 | axiom-ui | Gateway routing enforcement | grep | Hard |

---

## ADL blocks

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-001: SYSTEM AND SERVICE BOUNDARIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures deployed platform services have no compile-time dependencies
across service boundaries and that external traffic enters through axiom-api
rather than a pillar service directly.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a
GitHub Actions step that verifies no source file in any deployed service imports
from another service's root namespace or module path. The script must also fail
if documentation or configuration claims archon-api is the external entry point,
because axiom-api is the sole gateway and JWT validation point. Exit with code 1
if a cross-service dependency or incorrect entry-point claim is found.

DEFINE SYSTEM Axiom AS platform root directory
  DEFINE SERVICE Platform Gateway Service AS axiom-api/src
  DEFINE SERVICE Archon API Service AS archon-api/src
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE SERVICE SpecWeaver API Service AS specweaver-api/src
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE SERVICE UI Service AS axiom-ui/src

ASSERT(Platform Gateway Service has NO DEPENDENCY ON Archon API Service)
ASSERT(Platform Gateway Service has NO DEPENDENCY ON Archon Agent Service)
ASSERT(Platform Gateway Service has NO DEPENDENCY ON SpecWeaver API Service)
ASSERT(Platform Gateway Service has NO DEPENDENCY ON SpecWeaver Agent Service)
ASSERT(Platform Gateway Service has NO DEPENDENCY ON UI Service)
ASSERT(Archon API Service has NO DEPENDENCY ON Platform Gateway Service)
ASSERT(Archon API Service has NO DEPENDENCY ON Archon Agent Service)
ASSERT(Archon API Service has NO DEPENDENCY ON SpecWeaver API Service)
ASSERT(Archon API Service has NO DEPENDENCY ON SpecWeaver Agent Service)
ASSERT(Archon API Service has NO DEPENDENCY ON UI Service)
ASSERT(Archon Agent Service has NO DEPENDENCY ON Platform Gateway Service)
ASSERT(Archon Agent Service has NO DEPENDENCY ON Archon API Service)
ASSERT(Archon Agent Service has NO DEPENDENCY ON SpecWeaver API Service)
ASSERT(Archon Agent Service has NO DEPENDENCY ON SpecWeaver Agent Service)
ASSERT(Archon Agent Service has NO DEPENDENCY ON UI Service)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON Platform Gateway Service)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON Archon API Service)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON Archon Agent Service)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON SpecWeaver Agent Service)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON UI Service)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Platform Gateway Service)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Archon API Service)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Archon Agent Service)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON SpecWeaver API Service)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON UI Service)
ASSERT(UI Service has NO DEPENDENCY ON Platform Gateway Service)
ASSERT(UI Service has NO DEPENDENCY ON Archon API Service)
ASSERT(UI Service has NO DEPENDENCY ON Archon Agent Service)
ASSERT(UI Service has NO DEPENDENCY ON SpecWeaver API Service)
ASSERT(UI Service has NO DEPENDENCY ON SpecWeaver Agent Service)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-002: PLATFORM GATEWAY SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Enforces that all classes in axiom-api belong to one of the five
defined domains.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
every class under com.axiom.api resides in one of the five domain packages
(filter, health, config, security, dto). Use JUnit 5 and ArchUnit 1.x. The test
class should be named AxiomApiDomainStructureArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
    DEFINE DOMAIN Filter AS com.axiom.api.filter
    DEFINE DOMAIN Health AS com.axiom.api.health
    DEFINE DOMAIN Security AS com.axiom.api.security
    DEFINE DOMAIN DTO AS com.axiom.api.dto
    DEFINE DOMAIN Configuration AS com.axiom.api.config

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN {Filter, Health, Security, DTO, Configuration})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-003: PLATFORM GATEWAY SERVICE — ROUTE ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures axiom-api filter domain has no dependency on pillar-specific
business logic. The gateway is a routing and auth layer only.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
classes in com.axiom.api.filter do not depend on com.archon or com.specweaver
packages. Use JUnit 5 and ArchUnit 1.x. The test class should be named
GatewayRouteIsolationArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
    DEFINE DOMAIN Filter AS com.axiom.api.filter
  DEFINE SERVICE Archon API Service AS com.archon.api
  DEFINE SERVICE SpecWeaver API Service AS com.specweaver.api

ASSERT(Filter has NO DEPENDENCY ON Archon API Service)
ASSERT(Filter has NO DEPENDENCY ON SpecWeaver API Service)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-004: PLATFORM GATEWAY SERVICE — LLM CALL PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures axiom-api has no dependency on any LLM client library.
LLM calls belong exclusively in agent services.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
no class under com.axiom.api depends on com.theokanning.openai,
com.azure.ai.openai, or dev.langchain4j packages. Use JUnit 5 and ArchUnit 1.x.
The test class should be named AxiomApiLlmCallProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
  DEFINE LIBRARY OpenAI Library AS com.theokanning.openai
  DEFINE LIBRARY Azure OpenAI Library AS com.azure.ai.openai
  DEFINE LIBRARY LangChain Library AS dev.langchain4j

ASSERT(Platform Gateway Service has NO DEPENDENCY ON OpenAI Library)
ASSERT(Platform Gateway Service has NO DEPENDENCY ON Azure OpenAI Library)
ASSERT(Platform Gateway Service has NO DEPENDENCY ON LangChain Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-005: PLATFORM GATEWAY SERVICE — RESTTEMPLATE PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures no class in axiom-api depends on RestTemplate.
axiom-api uses Spring Cloud Gateway (WebFlux) and all HTTP calls must be reactive.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
no class under com.axiom.api imports or depends on
org.springframework.web.client.RestTemplate. Use JUnit 5 and ArchUnit 1.x.
The test class should be named AxiomApiRestTemplateProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
  DEFINE LIBRARY Rest Template AS org.springframework.web.client.RestTemplate

FOREACH $X IN CLASSES DO
  ASSERT($X has NO DEPENDENCY ON Rest Template)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-006: PLATFORM GATEWAY SERVICE — FILTER DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures the filter domain has no dependency on the health or DTO domains.
Filters are infrastructure concerns and must not import application-layer objects.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
classes in com.axiom.api.filter do not depend on com.axiom.api.health or
com.axiom.api.dto. Use JUnit 5 and ArchUnit 1.x. The test class should be named
FilterDomainIsolationArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
    DEFINE DOMAIN Filter AS com.axiom.api.filter
    DEFINE DOMAIN Health AS com.axiom.api.health
    DEFINE DOMAIN DTO AS com.axiom.api.dto

ASSERT(Filter has NO DEPENDENCY ON Health)
ASSERT(Filter has NO DEPENDENCY ON DTO)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-007: PLATFORM GATEWAY SERVICE — DATABASE ACCESS BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures filter and health domains in axiom-api have no dependency on
JPA or JDBC. The gateway owns no domain data — it routes and authenticates only.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
classes in com.axiom.api.filter and com.axiom.api.health do not depend on
jakarta.persistence or org.springframework.jdbc. Use JUnit 5 and ArchUnit 1.x.
The test class should be named AxiomApiDatabaseAccessBoundaryArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
    DEFINE DOMAIN Filter AS com.axiom.api.filter
    DEFINE DOMAIN Health AS com.axiom.api.health
  DEFINE LIBRARY JPA Library AS jakarta.persistence
  DEFINE LIBRARY JDBC Library AS org.springframework.jdbc

ASSERT(Filter has NO DEPENDENCY ON JPA Library)
ASSERT(Filter has NO DEPENDENCY ON JDBC Library)
ASSERT(Health has NO DEPENDENCY ON JPA Library)
ASSERT(Health has NO DEPENDENCY ON JDBC Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-008: ARCHON AGENT SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that all modules in archon-agent belong to one of the seven
defined domains.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
every module under app resides in one of the seven domain packages (pipeline,
tools, llm, memory, models, prompts, api). Use pytest and pyTestArch. The test
function should be named test_archon_agent_domain_structure.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN LLM AS app.llm
    DEFINE DOMAIN Memory AS app.memory
    DEFINE DOMAIN Models AS app.models
    DEFINE DOMAIN Prompts AS app.prompts
    DEFINE DOMAIN API AS app.api

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN {Pipeline, Tools, LLM, Memory, Models, Prompts, API})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-009: ARCHON AGENT SERVICE — PIPELINE DOMAIN COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that graph and nodes components are contained within the
pipeline domain.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
app.pipeline.graph and app.pipeline.nodes modules reside within the app.pipeline
package. Use pytest and pyTestArch. The test function should be named
test_pipeline_domain_components.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
      DEFINE COMPONENT Graph AS app.pipeline.graph
      DEFINE COMPONENT Nodes AS app.pipeline.nodes

ASSERT(Graph CONTAINED WITHIN Pipeline)
ASSERT(Nodes CONTAINED WITHIN Pipeline)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-010: ARCHON AGENT SERVICE — TOOLS DOMAIN COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that all tool components are contained within the tools domain.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
all tool modules reside within the app.tools package. Use pytest and pyTestArch.
The test function should be named test_tools_domain_components.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Tools AS app.tools
      DEFINE COMPONENT Base Tool AS app.tools.base
      DEFINE COMPONENT Tool Registry AS app.tools.registry
      DEFINE COMPONENT Requirement Parser AS app.tools.requirement_parser
      DEFINE COMPONENT Challenge Engine AS app.tools.challenge_engine
      DEFINE COMPONENT Scenario Modeler AS app.tools.scenario_modeler
      DEFINE COMPONENT Characteristic Reasoner AS app.tools.characteristic_reasoner
      DEFINE COMPONENT Conflict Analyzer AS app.tools.conflict_analyzer
      DEFINE COMPONENT Architecture Generator AS app.tools.architecture_generator
      DEFINE COMPONENT Diagram Generator AS app.tools.diagram_generator
      DEFINE COMPONENT Trade Off Engine AS app.tools.trade_off_engine
      DEFINE COMPONENT ADL Generator AS app.tools.adl_generator
      DEFINE COMPONENT Weakness Analyzer AS app.tools.weakness_analyzer

FOREACH $X IN COMPONENTS DO
  ASSERT($X CONTAINED WITHIN Tools)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-011: ARCHON AGENT SERVICE — TOOL DEPENDENCY RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures the tools domain has no dependency on the pipeline or api domains.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
no module under app.tools imports from app.pipeline or app.api. Use pytest and
pyTestArch. The test function should be named test_tool_dependency_rule.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN API AS app.api

ASSERT(Tools has NO DEPENDENCY ON Pipeline)
ASSERT(Tools has NO DEPENDENCY ON API)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-012: ARCHON AGENT SERVICE — PIPELINE NODES DEPENDENCY RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures the nodes component depends on tool registry only and not on
the broader tools domain directly.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
app.pipeline.nodes imports only from app.tools.registry and does not import from
any other module under app.tools. Use pytest and pyTestArch. The test function
should be named test_pipeline_nodes_dependency_rule.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
      DEFINE COMPONENT Nodes AS app.pipeline.nodes
    DEFINE DOMAIN Tools AS app.tools
      DEFINE COMPONENT Tool Registry AS app.tools.registry

ASSERT(Nodes DEPENDS ON Tool Registry EXCLUSIVELY)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-013: ARCHON AGENT SERVICE — LLM DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures tools, pipeline, and memory domains have no dependency on
OpenAI or LangChain libraries directly. All LLM calls must go through app.llm.client.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
no module under app.tools, app.pipeline, or app.memory imports from the openai or
langchain_openai packages. Use pytest and pyTestArch. The test function should be
named test_llm_domain_isolation.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Memory AS app.memory
  DEFINE LIBRARY OpenAI Library AS openai
  DEFINE LIBRARY LangChain Library AS langchain_openai

ASSERT(Tools has NO DEPENDENCY ON OpenAI Library)
ASSERT(Tools has NO DEPENDENCY ON LangChain Library)
ASSERT(Pipeline has NO DEPENDENCY ON OpenAI Library)
ASSERT(Pipeline has NO DEPENDENCY ON LangChain Library)
ASSERT(Memory has NO DEPENDENCY ON OpenAI Library)
ASSERT(Memory has NO DEPENDENCY ON LangChain Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-014: ARCHON AGENT SERVICE — MEMORY DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures tools and pipeline domains have no dependency on the Qdrant
client library. Qdrant access belongs exclusively in app.memory.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
no module under app.tools or app.pipeline imports from the qdrant_client package.
Use pytest and pyTestArch. The test function should be named
test_memory_domain_isolation.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Pipeline AS app.pipeline
  DEFINE LIBRARY Qdrant Client AS qdrant_client

ASSERT(Tools has NO DEPENDENCY ON Qdrant Client)
ASSERT(Pipeline has NO DEPENDENCY ON Qdrant Client)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-015: ARCHON AGENT SERVICE — PROMPT TEMPLATE ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures no tool class contains an inline prompt string exceeding 200
characters. All prompts must live in Jinja2 templates under app/prompts/.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a
GitHub Actions step that scans all Python files under app/tools/ for string
literals longer than 200 characters and flags them as inline prompt templates
that should be moved to Jinja2 files in app/prompts/. Exit with code 1 if any
match is found.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Tools AS app.tools
  DEFINE CONST MAX_INLINE_STRING AS 200 CHARS

FOREACH $X IN COMPONENTS DO
  ASSERT($X has NO DEPENDENCY ON MAX_INLINE_STRING)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-016: ARCHON AGENT SERVICE — ARCHITECTURECONTEXT OWNERSHIP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures ArchitectureContext is only contained within the models domain
and that tools, pipeline, and api domains depend on models.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
app.models.context is only within app.models, and that app.tools, app.pipeline,
and app.api each import from app.models. Use pytest and pyTestArch. The test
function should be named test_architecture_context_ownership.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Models AS app.models
      DEFINE COMPONENT Context AS app.models.context
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN API AS app.api

ASSERT(Context CONTAINED WITHIN Models EXCLUSIVELY)
ASSERT(Tools DEPENDS ON Models)
ASSERT(Pipeline DEPENDS ON Models)
ASSERT(API DEPENDS ON Models)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-017: ARCHON AGENT SERVICE — API DOMAIN BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures pipeline, tools, memory, and llm domains have no dependency
on the api domain.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
no module under app.pipeline, app.tools, app.memory, or app.llm imports from
app.api. Use pytest and pyTestArch. The test function should be named
test_api_domain_boundary.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Memory AS app.memory
    DEFINE DOMAIN LLM AS app.llm
    DEFINE DOMAIN API AS app.api

ASSERT(Pipeline has NO DEPENDENCY ON API)
ASSERT(Tools has NO DEPENDENCY ON API)
ASSERT(Memory has NO DEPENDENCY ON API)
ASSERT(LLM has NO DEPENDENCY ON API)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-018: ARCHON AGENT SERVICE — STAGE EVENT CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures every pipeline node emits STAGE_START and STAGE_COMPLETE events.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a
GitHub Actions step that parses app/pipeline/nodes.py and verifies every async
stage function emits both a STAGE_START and STAGE_COMPLETE event. Exit with code
1 if any stage function is missing either event.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
      DEFINE COMPONENT Nodes AS app.pipeline.nodes
  DEFINE CONST STAGE_START AS "STAGE_START"
  DEFINE CONST STAGE_COMPLETE AS "STAGE_COMPLETE"

FOREACH $X IN COMPONENTS DO
  ASSERT($X DEPENDS ON STAGE_START)
  ASSERT($X DEPENDS ON STAGE_COMPLETE)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-019: ALL AGENT SERVICES — SECRET PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via Semgrep
DESCRIPTION Ensures no domain in any agent service contains hardcoded credential strings.
Applies to archon-agent and specweaver-agent.
PROMPT Based on this pseudo-code, write a Semgrep rule in YAML that detects hardcoded
API keys (strings starting with sk-), hardcoded password assignments, and hardcoded
secret assignments in Python files under app/. The rule id should be
axiom-secret-prohibition.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE CONST FORBIDDEN_API_KEY AS "sk-"
  DEFINE CONST FORBIDDEN_PASSWORD AS "password="
  DEFINE CONST FORBIDDEN_SECRET AS "secret="

FOREACH $X IN SERVICES DO
  ASSERT($X has NO DEPENDENCY ON FORBIDDEN_API_KEY)
  ASSERT($X has NO DEPENDENCY ON FORBIDDEN_PASSWORD)
  ASSERT($X has NO DEPENDENCY ON FORBIDDEN_SECRET)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-020: UI SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ESLint with import plugin
DESCRIPTION Enforces that all modules in the UI Service belong to one of the defined
domains.
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the
eslint-plugin-import that enforces all source files under axiom-ui/src reside within
one of the defined domain directories (views, components, hooks, api, store, types,
styles). Output as a valid .eslintrc.json fragment.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE UI Service AS axiom-ui/src
    DEFINE DOMAIN Views AS axiom-ui/src/views
    DEFINE DOMAIN Components AS axiom-ui/src/components
    DEFINE DOMAIN Hooks AS axiom-ui/src/hooks
    DEFINE DOMAIN API Client AS axiom-ui/src/api
    DEFINE DOMAIN Store AS axiom-ui/src/store
    DEFINE DOMAIN Types AS axiom-ui/src/types
    DEFINE DOMAIN Styles AS axiom-ui/src/styles

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN
    {Views, Components, Hooks, API Client, Store, Types, Styles})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-021: UI SERVICE — API CALL BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ESLint with import plugin
DESCRIPTION Ensures views and components domains do not directly depend on the
fetch API. All HTTP calls must go through axiom-ui/src/api modules.
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the
eslint-plugin-import that prohibits direct use of the fetch function in files
under axiom-ui/src/views and axiom-ui/src/components, requiring all HTTP calls
to go through axiom-ui/src/api modules instead. Output as a valid .eslintrc.json
fragment.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE UI Service AS axiom-ui/src
    DEFINE DOMAIN Views AS axiom-ui/src/views
    DEFINE DOMAIN Components AS axiom-ui/src/components
  DEFINE LIBRARY Fetch API AS fetch

ASSERT(Views has NO DEPENDENCY ON Fetch API)
ASSERT(Components has NO DEPENDENCY ON Fetch API)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-022: UI SERVICE — STATE MANAGEMENT BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ESLint with import plugin
DESCRIPTION Ensures views depend on hooks (not store directly) and hooks depend on store.
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the
eslint-plugin-import that prohibits files under axiom-ui/src/views from importing
directly from axiom-ui/src/store, while allowing axiom-ui/src/hooks to import from
axiom-ui/src/store. Views must access state exclusively through hooks. Output as a
valid .eslintrc.json fragment.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE UI Service AS axiom-ui/src
    DEFINE DOMAIN Views AS axiom-ui/src/views
    DEFINE DOMAIN Hooks AS axiom-ui/src/hooks
    DEFINE DOMAIN Store AS axiom-ui/src/store

ASSERT(Views DEPENDS ON Hooks)
ASSERT(Views has NO DEPENDENCY ON Store)
ASSERT(Hooks DEPENDS ON Store)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-023: UI SERVICE — TOKEN STORAGE PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures no domain in the UI service stores tokens in localStorage or
sessionStorage.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a
GitHub Actions step that scans all TypeScript and TSX files under axiom-ui/src/
for calls to localStorage.setItem or sessionStorage.setItem. Exit with code 1 if
any match is found.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE UI Service AS axiom-ui/src
    DEFINE DOMAIN Views AS axiom-ui/src/views
    DEFINE DOMAIN Components AS axiom-ui/src/components
    DEFINE DOMAIN Hooks AS axiom-ui/src/hooks
    DEFINE DOMAIN API Client AS axiom-ui/src/api
    DEFINE DOMAIN Store AS axiom-ui/src/store
  DEFINE CONST FORBIDDEN_LOCAL_STORAGE AS "localStorage.setItem"
  DEFINE CONST FORBIDDEN_SESSION_STORAGE AS "sessionStorage.setItem"

FOREACH $X IN DOMAINS DO
  ASSERT($X has NO DEPENDENCY ON FORBIDDEN_LOCAL_STORAGE)
  ASSERT($X has NO DEPENDENCY ON FORBIDDEN_SESSION_STORAGE)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-024: ALL AGENT SERVICES — DATABASE ACCESS PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures no agent service has a dependency on PostgreSQL client libraries.
All persistence belongs in the corresponding API service.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
no module under app imports from psycopg2, asyncpg, or sqlalchemy in either
archon-agent or specweaver-agent. Use pytest and pyTestArch. The test function
should be named test_agent_database_access_prohibition.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE LIBRARY Psycopg2 AS psycopg2
  DEFINE LIBRARY Asyncpg AS asyncpg
  DEFINE LIBRARY SQLAlchemy AS sqlalchemy

ASSERT(Archon Agent Service has NO DEPENDENCY ON Psycopg2)
ASSERT(Archon Agent Service has NO DEPENDENCY ON Asyncpg)
ASSERT(Archon Agent Service has NO DEPENDENCY ON SQLAlchemy)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Psycopg2)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Asyncpg)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON SQLAlchemy)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-025: CROSS-SERVICE — QDRANT ACCESS PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures API services (axiom-api, archon-api, specweaver-api) have no
dependency on the Qdrant Java client. Qdrant access belongs in agent services only.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no
class under com.axiom.api, com.archon.api, or com.specweaver.api depends on the
io.qdrant package. Use JUnit 5 and ArchUnit 1.x. The test class should be named
QdrantAccessProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
  DEFINE SERVICE Archon API Service AS com.archon.api
  DEFINE SERVICE SpecWeaver API Service AS com.specweaver.api
  DEFINE LIBRARY Qdrant Java Client AS io.qdrant

ASSERT(Platform Gateway Service has NO DEPENDENCY ON Qdrant Java Client)
ASSERT(Archon API Service has NO DEPENDENCY ON Qdrant Java Client)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON Qdrant Java Client)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-026: CROSS-SERVICE — TACTIC ENTITY DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures the ArchitectureTactic entity lives exclusively in archon-api.
The Python agent must never reference the Java entity directly.
PROMPT Based on this pseudo-code, write a bash fitness function that verifies no
Python file under archon-agent/ contains the string "ArchitectureTactic" as a
type reference, and no Python file under archon-agent/ imports from any Java
package. Emit PASS or FAIL with file and line details on failure.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon API Service AS archon-api/src
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT Tactic Entity
    AS com.archon.api.domain.model.ArchitectureTactic

ASSERT(Tactic Entity CONTAINED WITHIN Archon API Service)
ASSERT(Archon Agent Service has NO DEPENDENCY ON Tactic Entity)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-027: ARCHON API SERVICE — TACTIC WRITE PATH ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures tactics are written to the database only from ChatService
via TacticsService.saveTactics(). No other write path is permitted.
PROMPT Based on this pseudo-code, write a bash fitness function that scans all
Java files under archon-api/src/ for calls to TacticRepository.save or
TacticRepository.saveAll and flags any caller that is NOT TacticsService. Also
scans for calls to tacticsService.saveTactics and flags any caller that is NOT
ChatService. Emit PASS if no violations, FAIL with file and line details otherwise.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon API Service AS com.archon.api
  DEFINE COMPONENT ChatService AS com.archon.api.service.ChatService
  DEFINE COMPONENT TacticsService AS com.archon.api.service.TacticsService
  DEFINE COMPONENT TacticRepository
    AS com.archon.api.domain.repository.TacticRepository

ASSERT(TacticRepository EXCLUSIVELY ACCESSED BY TacticsService)
ASSERT(TacticsService.saveTactics EXCLUSIVELY ACCESSED BY ChatService)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-028: ARCHON AGENT SERVICE — TACTIC CATALOG ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via Semgrep
DESCRIPTION Ensures TacticsAdvisorTool only recommends tactics from the Bass,
Clements, and Kazman catalog embedded in tactics_advisor.j2. Tactic names must
not be hardcoded in Python source.
PROMPT Based on this pseudo-code, write a Semgrep YAML rule that detects any
string literal in app/tools/tactics_advisor.py that looks like a tactic name
(heuristic: title-case multi-word string longer than 10 chars not adjacent to a
known variable name) and flags it as a violation. Rule id: axiom-tactic-catalog.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT TacticsAdvisorTool AS app.tools.tactics_advisor
  DEFINE COMPONENT TacticsCatalog AS app.prompts.tactics_advisor

ASSERT(TacticsAdvisorTool DEPENDS ON TacticsCatalog EXCLUSIVELY)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-033: HTTPS ENFORCEMENT ON INGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Asserts that the ingress template enforces TLS and that the ssl-redirect
annotation is present. Also checks a real CA issuer is configured.
PROMPT Based on this pseudo-code, write a bash script for GitHub Actions that checks:
(1) helm/ai-architect/templates/ingress.yaml contains ssl-redirect,
(2) helm/ai-architect/values.yaml contains letsencrypt,
(3) helm/ai-architect/templates/ingress.yaml contains a tls: block.
Exit with code 1 if any check fails. Rule id: axiom-https-enforcement.

DEFINE SYSTEM Axiom AS helm/ai-architect
  DEFINE CONST TLS_ANNOTATION AS "ssl-redirect"
  DEFINE CONST ISSUER_REFERENCE AS "letsencrypt"
  DEFINE CONST TLS_BLOCK AS "tls:"
  DEFINE COMPONENT IngressTemplate
    AS helm/ai-architect/templates/ingress.yaml
  DEFINE COMPONENT IngressValues AS helm/ai-architect/values.yaml

ASSERT(IngressTemplate CONTAINS TLS_ANNOTATION)
ASSERT(IngressValues CONTAINS ISSUER_REFERENCE)
ASSERT(IngressTemplate CONTAINS TLS_BLOCK)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-034: ARCHON AGENT — STRUCTURED OUTPUT SCHEMA ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures every tool that calls llm_client.complete() with JSON output
also passes output_schema and schema_name sourced from app.llm.schemas.SCHEMAS.
Inline schema definitions inside tool classes are prohibited.
PROMPT Based on this pseudo-code, write a pytest test that imports every module from
app.tools, inspects the source code of each tool's run() method, and verifies every
call to self.llm_client.complete() that includes response_format includes
output_schema=SCHEMAS.get(...) and schema_name= arguments. Test function:
test_all_tools_pass_output_schema.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT SchemaRegistry AS app.llm.schemas.SCHEMAS

FOREACH $X IN COMPONENTS DO
  ASSERT($X DEPENDS ON SchemaRegistry)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-035: ARCHON AGENT — SINGLE REPAIR ATTEMPT PER STAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures each tool is allowed exactly one call to attempt_repair()
per run() invocation.
PROMPT Based on this pseudo-code, write a pytest test that mocks llm_client.complete()
to raise json.JSONDecodeError on the first call and return valid JSON on the second.
Verify attempt_repair() is called exactly once. Test function:
test_single_repair_attempt_per_stage.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT BaseTool AS app.tools.base.BaseTool
  DEFINE CONST MAX_REPAIR_ATTEMPTS AS 1

ASSERT(BaseTool.attempt_repair CALLED AT MOST MAX_REPAIR_ATTEMPTS PER run())
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-036: ARCHON AGENT — SUPPORTING STAGE RESILIENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures supporting stage failures record a gap and allow the pipeline
to continue, while core stage failures abort immediately.
CORE_STAGES = {requirement_parsing, requirement_challenge,
characteristic_inference, architecture_generation}.
PROMPT Based on this pseudo-code, write a pytest test that mocks a supporting stage
to raise ToolExecutionException and verifies STAGE_COMPLETE with
status=completed_with_gaps is emitted and subsequent stages still complete. Then
repeat with a core stage and verify ERROR is emitted with no further stages.
Test function: test_supporting_stage_resilience.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT Graph AS app.pipeline.graph
  DEFINE CONST CORE_STAGES AS
    {requirement_parsing, requirement_challenge,
     characteristic_inference, architecture_generation}

ASSERT(SUPPORTING_STAGES failure EMITS "STAGE_COMPLETE"
  WITH status="completed_with_gaps")
ASSERT(CORE_STAGES failure EMITS "ERROR" AND HALTS pipeline)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-057: ARCHON API — WORKSHOP SESSION BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via bash
DESCRIPTION Ensures the workshop domain in archon-api does not import from the
conversation domain. Workshop sessions are independently managed.
PROMPT Based on this pseudo-code, write a bash script that checks no Java file
under archon-api/src/main/java/com/archon/api/workshop imports from
com.archon.api.domain or com.archon.api.service. Exit 1 on violation.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon API Service AS com.archon.api
    DEFINE DOMAIN Workshop AS com.archon.api.workshop
    DEFINE DOMAIN Conversation AS com.archon.api.domain

ASSERT(Workshop has NO DEPENDENCY ON Conversation)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-058: ARCHON AGENT — WORKSHOP MODULE ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest + bash
DESCRIPTION Ensures app.workshop does not import from app.pipeline or app.tools.
The Quality Attribute Workshop is a pre-architecture elicitation module and must
be independently testable without pipeline infrastructure.
PROMPT Based on this pseudo-code, write a PyTestArch test that verifies no module
under app.workshop imports from app.pipeline or app.tools. Test function:
test_workshop_module_isolation.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
    DEFINE DOMAIN Workshop AS app.workshop
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools

ASSERT(Workshop has NO DEPENDENCY ON Pipeline)
ASSERT(Workshop has NO DEPENDENCY ON Tools)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-059: ARCHON API — PASSWORD RESET TOKEN STORAGE SECURITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Asserts that PasswordResetService never persists the raw token.
Only passwordEncoder.encode(rawToken) may be stored in tokenHash.
PROMPT Based on this pseudo-code, write a bash script that verifies
PasswordResetService.java contains passwordEncoder.encode and does not contain
any line that assigns the raw token variable directly to a persistence field.
Exit 1 on violation. Rule: axiom-password-reset-hash-only.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon API Service AS com.archon.api
  DEFINE COMPONENT PasswordResetService
    AS com.archon.api.service.PasswordResetService
  DEFINE CONST TOKEN_STORAGE AS "bcrypt hash only"

ASSERT(PasswordResetService CONTAINS passwordEncoder.encode)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-060: ARCHON AGENT — UTILITY TREE GENERATION THRESHOLD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION The utility tree generator must check has_sufficient_for_utility_tree
before invoking the LLM. Threshold: ≥5 eligible scenarios across ≥3 distinct
attribute values. Aspirational scenarios do not count.
PROMPT Based on this pseudo-code, write a pytest test that creates a WorkshopContext
with fewer than 5 eligible scenarios, calls UtilityTreeGenerator.generate, and
verifies None is returned without calling the LLM. Test function:
test_utility_tree_threshold_not_met.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT UtilityTreeGenerator
    AS app.workshop.utility_tree_generator.UtilityTreeGenerator
  DEFINE CONST SCENARIO_THRESHOLD AS 5
  DEFINE CONST ATTRIBUTE_THRESHOLD AS 3

ASSERT(UtilityTreeGenerator CHECKS has_sufficient_for_utility_tree
  BEFORE llm.complete)
ASSERT(UtilityTreeGenerator RETURNS None
  WHEN has_sufficient_for_utility_tree IS False)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-061: ARCHON AGENT — ARCHITECTURAL IMPLICATION FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Implications must trace to source_scenario_id, describe
affected_quality_attrs, include tradeoff and measurable_condition fields,
and be capped at MAX_IMPLICATIONS = 20.
PROMPT Based on this pseudo-code, write a pytest test that calls
ImplicationSynthesiser.synthesise with more than 20 candidate implications and
verifies only 20 are returned. Test function: test_implication_max_guard.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT ImplicationSynthesiser
    AS app.workshop.implication_synthesiser.ImplicationSynthesiser
  DEFINE CONST MAX_IMPLICATIONS AS 20

ASSERT(ImplicationSynthesiser RETURNS at most MAX_IMPLICATIONS items)
ASSERT(ImplicationSynthesiser RETURNS empty_list
  WHEN context.utility_tree IS None)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-062: ARCHON AGENT — IMPLICATION MECHANISM PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Asserts that the implication synthesis prompt lists mechanism terms
as prohibited and the synthesiser validates against them.
PROMPT Based on this pseudo-code, write a bash script that checks
app/prompts/workshop/synthesise_implications.j2 contains PROHIBITED in a section
and app/workshop/implication_synthesiser.py contains PROHIBITED_MECHANISM_TERMS
as a module constant. Exit 1 if either check fails.
Rule: axiom-no-mechanism-implications.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT ImplicationPrompt
    AS app/prompts/workshop/synthesise_implications.j2
  DEFINE COMPONENT ImplicationSynthesiser
    AS app.workshop.implication_synthesiser
  DEFINE CONST PROHIBITED AS "PROHIBITED_MECHANISM_TERMS"

ASSERT(ImplicationSynthesiser CONTAINS PROHIBITED)
ASSERT(ImplicationPrompt CONTAINS PROHIBITED)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-063: ARCHON API — SEND-TO-PIPELINE INCLUDES ALL ATTRIBUTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Asserts that formatWorkshopOutputAsRequirements iterates over all
quality attributes without filtering before the iteration.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
WorkshopController.formatWorkshopOutputAsRequirements exists and iterates over
summary.qualityAttributes() without a filter call preceding it. Test class:
WorkshopPipelineSubmissionArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon API Service AS com.archon.api
  DEFINE COMPONENT WorkshopController
    AS com.archon.api.workshop.controller.WorkshopController

ASSERT(WorkshopController CONTAINS formatWorkshopOutputAsRequirements)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-064: ARCHON API/UI — IDEMPOTENCY KEY ON PIPELINE SUBMISSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Asserts the send-to-pipeline API function in the UI includes an
Idempotency-Key header and that WorkshopController reads it.
PROMPT Based on this pseudo-code, write a bash script that checks the workshop
API TypeScript file contains Idempotency-Key as a request header and
WorkshopController.java reads it. Exit 1 if either check fails.
Rule: axiom-workshop-idempotency-key.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon API Service AS com.archon.api
  DEFINE COMPONENT WorkshopController
    AS com.archon.api.workshop.controller.WorkshopController
  DEFINE CONST IDEMPOTENCY_HEADER AS "Idempotency-Key"

ASSERT(WorkshopController CONTAINS IDEMPOTENCY_HEADER)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-065: ARCHON AGENT — SCENARIO DEDUPLICATION BEFORE PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Asserts that deduplicated_scenarios property exists on WorkshopContext
and that scenario-consuming synthesis uses it rather than the raw scenarios list.
PROMPT Based on this pseudo-code, write a pytest test that creates a WorkshopContext
with two scenarios sharing the same stimulus and artifact text and verifies
deduplicated_scenarios returns only one. Test function:
test_deduplicated_scenarios_removes_duplicates.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE COMPONENT WorkshopContext AS app.workshop.context
  DEFINE CONST DEDUP_PROPERTY AS "deduplicated_scenarios"

ASSERT(WorkshopContext CONTAINS DEDUP_PROPERTY)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-069: ARCHON AGENT — LLM PROVIDER ABSTRACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Asserts that no module outside app.llm imports from openai or makes
direct HTTP calls to the Ollama API. All LLM calls must go through app.llm.client.
PROMPT Based on this pseudo-code, write a PyTestArch test verifying that no module
in app.tools or app.workshop imports from openai or httpx directly. Test functions:
test_tools_no_direct_openai_import and test_workshop_no_direct_llm_calls.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Workshop AS app.workshop
  DEFINE LIBRARY OpenAI Library AS openai
  DEFINE LIBRARY HTTPX Library AS httpx

ASSERT(Tools has NO DEPENDENCY ON OpenAI Library)
ASSERT(Workshop has NO DEPENDENCY ON HTTPX Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-070: ARCHON AGENT — STAGE_NAME REQUIRED ON ALL LLM CLIENT CALLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Asserts that every call to llm_client.complete() in the codebase
passes a stage_name argument. Stage names drive model-tier selection and latency
budgeting; missing names silently route calls to the wrong model.
PROMPT Based on this pseudo-code, write a bash script that searches app/tools/ and
app/workshop/ for calls to llm_client.complete( and verifies each includes
stage_name= as a keyword argument. Exit 1 with file and line on violation.
Rule: axiom-llm-stage-name-required.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE CONST STAGE_NAME_PARAM AS "stage_name="

ASSERT(LLMClient CONTAINS STAGE_NAME_PARAM)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-071: AXIOM-API IS THE SOLE JWT VALIDATION POINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Asserts that archon-api does not contain JWT validation logic when
AXIOM_GATEWAY_BYPASS is false. JWT validation belongs exclusively in axiom-api.
archon-api trusts the X-Axiom-User-Id header forwarded by the gateway.
PROMPT Based on this pseudo-code, write an ArchUnit test verifying that no class
in com.archon.api reads the Authorization header or imports io.jsonwebtoken except
within classes annotated with @ConditionalOnProperty(name=axiom.gateway.bypass,
havingValue=true). Test class: GatewayAuthBoundaryTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
  DEFINE SERVICE Archon API Service AS com.archon.api
  DEFINE LIBRARY JJWT AS io.jsonwebtoken
  DEFINE CONST BYPASS_CONDITION
    AS "@ConditionalOnProperty(axiom.gateway.bypass=true)"

ASSERT(Archon API Service JWT validation
  CONTAINED WITHIN BYPASS_CONDITION EXCLUSIVELY)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-072: CROSS-PILLAR — PILLARS MUST NOT IMPORT FROM EACH OTHER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Asserts that no pillar agent imports from another pillar's module.
Cross-pillar communication is HTTP only via axiom-api.
PROMPT Based on this pseudo-code, write a PyTestArch test verifying that
archon-agent, specweaver-agent, and lens-agent have no imports from one another.
Test file: tests/architecture/test_pillar_isolation.py.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Archon Agent Service AS archon-agent/app
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE SERVICE Lens Agent Service AS lens-agent/app

ASSERT(Archon Agent Service has NO DEPENDENCY ON SpecWeaver Agent Service)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Archon Agent Service)
ASSERT(Archon Agent Service has NO DEPENDENCY ON Lens Agent Service)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Lens Agent Service)
ASSERT(Lens Agent Service has NO DEPENDENCY ON Archon Agent Service)
ASSERT(Lens Agent Service has NO DEPENDENCY ON SpecWeaver Agent Service)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-073: PLATFORM — MAXIMUM TWO SERVICES PER PILLAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom bash fitness function
DESCRIPTION Each pillar must contain at most two service directories:
one *-api and one *-agent.
PROMPT Based on this pseudo-code, write a bash script that checks each pillar
directory (archon, specweaver, lens) contains at most two subdirectories
matching *-api and *-agent patterns. Exit 1 if any pillar has more than two
service directories. Rule: axiom-two-service-limit.

DEFINE SYSTEM Axiom AS platform root directory
  DEFINE CONST MAX_SERVICES_PER_PILLAR AS 2

FOREACH $X IN {archon, specweaver, lens} DO
  ASSERT($X CONTAINS AT MOST MAX_SERVICES_PER_PILLAR SERVICES)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-074: SPECWEAVER API SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Enforces that all classes in specweaver-api belong to one of the defined
domains.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies every
class under com.specweaver.api resides in one of the five domain packages (controller,
domain, service, storage, config). Use JUnit 5 and ArchUnit 1.x. The test class
should be named SpecWeaverApiDomainStructureArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver API Service AS com.specweaver.api
    DEFINE DOMAIN Controller AS com.specweaver.api.controller
    DEFINE DOMAIN Domain AS com.specweaver.api.domain
    DEFINE DOMAIN Service AS com.specweaver.api.service
    DEFINE DOMAIN Storage AS com.specweaver.api.storage
    DEFINE DOMAIN Configuration AS com.specweaver.api.config

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN
    {Controller, Domain, Service, Storage, Configuration})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-075: SPECWEAVER API SERVICE — DATABASE ACCESS BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures controller domain has no dependency on JPA or JDBC. All
persistence goes through the domain repository layer.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
classes in com.specweaver.api.controller do not depend on jakarta.persistence or
org.springframework.jdbc. Use JUnit 5 and ArchUnit 1.x. The test class should be
named SpecWeaverDatabaseAccessBoundaryArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver API Service AS com.specweaver.api
    DEFINE DOMAIN Controller AS com.specweaver.api.controller
  DEFINE LIBRARY JPA Library AS jakarta.persistence
  DEFINE LIBRARY JDBC Library AS org.springframework.jdbc

ASSERT(Controller has NO DEPENDENCY ON JPA Library)
ASSERT(Controller has NO DEPENDENCY ON JDBC Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-076: SPECWEAVER API SERVICE — LLM CALL PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures specweaver-api has no dependency on any LLM client library.
All LLM calls belong in specweaver-agent.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no
class under com.specweaver.api depends on com.theokanning.openai,
com.azure.ai.openai, or dev.langchain4j. Use JUnit 5 and ArchUnit 1.x. The test
class should be named SpecWeaverLlmCallProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver API Service AS com.specweaver.api
  DEFINE LIBRARY OpenAI Library AS com.theokanning.openai
  DEFINE LIBRARY Azure OpenAI Library AS com.azure.ai.openai
  DEFINE LIBRARY LangChain Library AS dev.langchain4j

ASSERT(SpecWeaver API Service has NO DEPENDENCY ON OpenAI Library)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON Azure OpenAI Library)
ASSERT(SpecWeaver API Service has NO DEPENDENCY ON LangChain Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-077: SPECWEAVER API SERVICE — RESTTEMPLATE PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures no class in specweaver-api depends on RestTemplate.
All HTTP calls must use WebClient.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no
class under com.specweaver.api imports org.springframework.web.client.RestTemplate.
Use JUnit 5 and ArchUnit 1.x. The test class should be named
SpecWeaverRestTemplateProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver API Service AS com.specweaver.api
  DEFINE LIBRARY Rest Template
    AS org.springframework.web.client.RestTemplate

FOREACH $X IN CLASSES DO
  ASSERT($X has NO DEPENDENCY ON Rest Template)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-078: SPECWEAVER AGENT SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that all modules in specweaver-agent belong to one of the
defined domains.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
every module under app resides in one of the six domain packages (pipeline, tools,
llm, models, prompts, api). Use pytest and pyTestArch. The test function should be
named test_specweaver_agent_domain_structure.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN LLM AS app.llm
    DEFINE DOMAIN Models AS app.models
    DEFINE DOMAIN Prompts AS app.prompts
    DEFINE DOMAIN API AS app.api

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN {Pipeline, Tools, LLM, Models, Prompts, API})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-079: SPECWEAVER AGENT SERVICE — LLM DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures tools and pipeline domains in specweaver-agent have no
dependency on OpenAI or LangChain libraries directly.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
no module under app.tools or app.pipeline imports from openai or langchain_openai.
Use pytest and pyTestArch. Test function: test_specweaver_llm_domain_isolation.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Pipeline AS app.pipeline
  DEFINE LIBRARY OpenAI Library AS openai
  DEFINE LIBRARY LangChain Library AS langchain_openai

ASSERT(Tools has NO DEPENDENCY ON OpenAI Library)
ASSERT(Tools has NO DEPENDENCY ON LangChain Library)
ASSERT(Pipeline has NO DEPENDENCY ON OpenAI Library)
ASSERT(Pipeline has NO DEPENDENCY ON LangChain Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-080: SPECWEAVER AGENT SERVICE — DATABASE ACCESS PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures specweaver-agent has no dependency on PostgreSQL client
libraries. All persistence belongs in specweaver-api.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies
no module under app imports from psycopg2, asyncpg, or sqlalchemy. Use pytest and
pyTestArch. Test function: test_specweaver_agent_database_access_prohibition.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE LIBRARY Psycopg2 AS psycopg2
  DEFINE LIBRARY Asyncpg AS asyncpg
  DEFINE LIBRARY SQLAlchemy AS sqlalchemy

ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Psycopg2)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON Asyncpg)
ASSERT(SpecWeaver Agent Service has NO DEPENDENCY ON SQLAlchemy)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-081: SPECWEAVER AGENT — QDRANT CLEANUP CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures ConsolidationTool always deletes its temporary Qdrant collection
in a finally block. Orphaned specweaver_session_{id} collections accumulate
unboundedly across sessions.
PROMPT Based on this pseudo-code, write a pytest test that mocks QdrantClient and
verifies ConsolidationTool._delete_collection is called in a finally block even
when consolidation raises an exception. Verify the collection name follows the
pattern specweaver_session_{session_id}. Test function:
test_qdrant_collection_deleted_in_finally.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE COMPONENT ConsolidationTool AS app.tools.consolidation_tool
  DEFINE CONST COLLECTION_PATTERN AS "specweaver_session_{session_id}"

ASSERT(ConsolidationTool._delete_collection
  CALLED IN finally BLOCK OF ConsolidationTool.run)
ASSERT(ConsolidationTool CONTAINS COLLECTION_PATTERN)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-082: SPECWEAVER AGENT — EXTRACTION GUARD CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures the extraction_guard stage raises ValueError when all documents
produce zero requirements. A successful empty package silently corrupts the Archon
input — explicit abort is the correct failure mode.
PROMPT Based on this pseudo-code, write a pytest test that creates a
SpecWeaverContext with one document and empty extraction_results, calls
check_extraction_results, and verifies ValueError is raised. Verify the pipeline
continues when at least one document produced requirements. Test function:
test_extraction_guard_aborts_on_zero_requirements.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE COMPONENT ExtractionGuard
    AS app.pipeline.graph.check_extraction_results
  DEFINE CONST EMPTY_PACKAGE AS total_requirements = 0

ASSERT(ExtractionGuard RAISES ValueError
  WHEN EMPTY_PACKAGE AND documents IS NOT EMPTY)
ASSERT(ExtractionGuard CONTINUES pipeline
  WHEN at least one document produced requirements)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-083: SPECWEAVER AGENT — CONFLICT PRESERVATION CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures the conflict detection agent never resolves conflicts. Both
sides of a contradiction must remain in the requirements list with LOW confidence.
PROMPT Based on this pseudo-code, write a pytest test that submits a classified
requirement set with two mutually exclusive technology requirements and verifies the
output contains both requirements with confidence=LOW and a non-empty conflicts
array. Test function: test_conflicts_preserved_not_resolved.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver Agent Service AS specweaver-agent/app
  DEFINE COMPONENT ConflictDetectionTool
    AS app.tools.conflict_detection_tool
  DEFINE CONST LOW_CONFIDENCE AS confidence = "low"

ASSERT(ConflictDetectionTool PRESERVES both sides OF CONFLICTING requirements)
ASSERT(ConflictDetectionTool SETS LOW_CONFIDENCE ON conflicting requirements)
ASSERT(ConflictDetectionTool conflicts array IS NOT EMPTY
  WHEN contradictions detected)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-084: SPECWEAVER API — UPLOAD SIZE LIMIT ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures DocumentController validates file and text size before
processing. Unbounded uploads risk OOM on the specweaver-api pod.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
DocumentController contains MAX_FILE_SIZE_BYTES and MAX_TEXT_LENGTH constants.
Use JUnit 5 and ArchUnit 1.x. Test class: SpecWeaverUploadLimitArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE SpecWeaver API Service AS com.specweaver.api
  DEFINE COMPONENT DocumentController
    AS com.specweaver.api.controller.DocumentController
  DEFINE CONST MAX_FILE_SIZE_BYTES AS 20971520
  DEFINE CONST MAX_TEXT_LENGTH AS 500000

ASSERT(DocumentController CONTAINS MAX_FILE_SIZE_BYTES)
ASSERT(DocumentController CONTAINS MAX_TEXT_LENGTH)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-085: AXIOM-API — AUTH ROUTE COVERAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures axiom-api SecurityConfig permits /api/v1/auth/** without JWT
validation so users can obtain tokens through the gateway.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies
SecurityConfig contains a pathMatchers call for /api/v1/auth/** with permitAll().
Use JUnit 5 and ArchUnit 1.x. Test class: AxiomApiAuthRouteArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Platform Gateway Service AS com.axiom.api
  DEFINE COMPONENT SecurityConfig AS com.axiom.api.config.SecurityConfig
  DEFINE CONST AUTH_PATH AS "/api/v1/auth/**"
  DEFINE CONST PERMIT_ALL AS "permitAll"

ASSERT(SecurityConfig CONTAINS AUTH_PATH)
ASSERT(SecurityConfig CONTAINS PERMIT_ALL)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-086: AXIOM-UI — GATEWAY ROUTING ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures the axiom-ui nginx config routes all API calls through
axiom-api and does not bypass the gateway. SSE timeout must be >= 600s.
PROMPT Based on this pseudo-code, write a bash script that verifies:
(1) axiom-ui/nginx.conf contains proxy_pass http://axiom-api:8080,
(2) axiom-ui/nginx.conf does not contain proxy_pass http://archon-api or
    proxy_pass http://specweaver-api,
(3) axiom-ui/nginx.conf contains proxy_read_timeout with a value >= 600s.
Exit 1 with details if any check fails. Rule id: axiom-ui-gateway-routing.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE UI Service AS axiom-ui
  DEFINE COMPONENT NginxConfig AS axiom-ui/nginx.conf
  DEFINE CONST GATEWAY_UPSTREAM AS "proxy_pass http://axiom-api:8080"
  DEFINE CONST MIN_SSE_TIMEOUT AS 600

ASSERT(NginxConfig CONTAINS GATEWAY_UPSTREAM)
ASSERT(NginxConfig has NO DEPENDENCY ON "proxy_pass http://archon-api")
ASSERT(NginxConfig has NO DEPENDENCY ON "proxy_pass http://specweaver-api")
ASSERT(NginxConfig CONTAINS "proxy_read_timeout")
```

---

## Enforcement levels

| Block ID | Enforcement | Rationale |
|----------|-------------|-----------|
| ADL-001 | Soft | Cross-service isolation is guaranteed by separate language runtimes; this block documents intent and catches accidental cross-references |
| ADL-002 | Soft | Domain organisation improves navigability; violations are structural debt |
| ADL-003 | Soft | Route isolation reduces coupling but violations are refactorable |
| ADL-004 | Hard | LLM calls from the gateway bypass the agent pipeline, causing duplicate billing and scattered API key usage |
| ADL-005 | Hard | RestTemplate is blocking and incompatible with WebFlux; it will cause thread starvation under SSE load |
| ADL-006 | Soft | Filter isolation reduces coupling but violations are refactorable |
| ADL-007 | Hard | Direct database access from filters bypasses transaction management and risks data corruption |
| ADL-008 | Soft | Domain organisation in archon-agent improves navigability |
| ADL-009 | Soft | Pipeline component containment improves discoverability |
| ADL-010 | Soft | Tool component containment improves discoverability |
| ADL-011 | Soft | Tool independence from pipeline prevents circular dependencies |
| ADL-012 | Soft | Nodes depending only on the registry prevents tight coupling to individual tools |
| ADL-013 | Hard | LLM library imports outside the LLM domain scatter API key usage and make provider switching impossible |
| ADL-014 | Hard | Qdrant client usage outside the memory domain fragments vector store access |
| ADL-015 | Soft | Inline prompt strings reduce template reusability but don't cause runtime failures |
| ADL-016 | Soft | Context ownership ensures single source of truth for pipeline state |
| ADL-017 | Soft | API boundary prevents reverse dependencies |
| ADL-018 | Soft | Stage events are essential for UI progress display; missing events degrade UX not security |
| ADL-019 | Hard | Hardcoded secrets are a critical security vulnerability that could leak through version control |
| ADL-020 | Soft | UI domain structure improves navigability |
| ADL-021 | Soft | API call boundary centralises error handling and retry logic |
| ADL-022 | Soft | State management layering improves testability |
| ADL-023 | Hard | Storing tokens in localStorage or sessionStorage exposes them to XSS attacks |
| ADL-024 | Hard | Agent services must not own relational data; a violation splits persistence ownership |
| ADL-025 | Hard | API services must not access Qdrant directly; a violation splits vector data ownership |
| ADL-026 | Hard | The ArchitectureTactic entity is owned exclusively by archon-api; a violation couples Python code to the Java persistence model |
| ADL-027 | Hard | A second tactic write path creates duplicate records and race conditions |
| ADL-028 | Hard | Tactic names hardcoded in Python bypass the BCK catalog constraint and make the tool unauditable |
| ADL-033 | Hard | Serving over HTTP exposes JWT tokens and architecture data in plaintext |
| ADL-034 | Hard | A missing schema silently falls back to unstructured JSON, allowing malformed payloads to propagate through the pipeline |
| ADL-035 | Hard | A second repair attempt masks persistent model failures and increases latency without improving quality |
| ADL-036 | Hard | Supporting stage failures must not abort the pipeline; core stage failures must |
| ADL-057 | Hard | Workshop and conversation domains must be independently manageable |
| ADL-058 | Hard | The workshop module must be testable in isolation without pipeline infrastructure |
| ADL-059 | Hard | Persisting raw password reset tokens turns a database leak into account takeover |
| ADL-060 | Hard | Generating a utility tree without sufficient evidence produces a low-signal result that misleads the architect |
| ADL-061 | Hard | Implications must be capped, traceable, and skip synthesis when no tree exists |
| ADL-062 | Hard | Mechanism-named implications over-specify technology choices prematurely |
| ADL-063 | Hard | Filtering attributes before pipeline handoff hides architecturally relevant constraints |
| ADL-064 | Hard | Missing idempotency keys allow duplicate architecture runs and unnecessary LLM cost |
| ADL-065 | Hard | Duplicate scenarios overweight one concern and distort downstream architectural reasoning |
| ADL-069 | Hard | Direct provider imports bypass the provider switch and scatter LLM credentials |
| ADL-070 | Hard | Missing stage names silently route LLM calls to the wrong model tier |
| ADL-071 | Hard | JWT validation must live exclusively in axiom-api; duplicating it in archon-api makes authentication policy ambiguous |
| ADL-072 | Hard | Pillar imports bypass the HTTP-only platform contract and create hidden coupling between roadmap phases |
| ADL-073 | Hard | Extra services expand operational scope and violate the deployment model |
| ADL-074 | Soft | Domain organisation in specweaver-api improves navigability |
| ADL-075 | Hard | Direct JPA access in controllers bypasses the repository layer's transaction management |
| ADL-076 | Hard | LLM calls in specweaver-api bypass the agent pipeline and make provider switching impossible |
| ADL-077 | Hard | RestTemplate is blocking and incompatible with reactive WebFlux |
| ADL-078 | Soft | Domain organisation in specweaver-agent improves navigability |
| ADL-079 | Hard | Direct LLM imports in specweaver-agent scatter credentials and prevent provider switching |
| ADL-080 | Hard | specweaver-agent must not own relational data; a violation splits persistence ownership |
| ADL-081 | Hard | Orphaned Qdrant collections accumulate unboundedly; the cleanup contract is availability-critical |
| ADL-082 | Hard | A successful empty package silently corrupts the Archon input; explicit abort is the correct failure mode |
| ADL-083 | Hard | Resolving conflicts hides ambiguity the architect must address |
| ADL-084 | Hard | Unbounded uploads risk OOM on the specweaver-api pod |
| ADL-085 | Hard | Auth endpoints inaccessible through the gateway break the login flow for all users |
| ADL-086 | Hard | Direct pillar routing in nginx bypasses JWT validation; SSE timeout below 600s breaks the Archon pipeline progress stream |

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-087: LENS API SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Enforces that all classes in lens-api belong to one of the defined
domains.
PROMPT Write an ArchUnit test verifying every class under com.lens.api resides
in one of (controller, domain, service, client, config, security). Test class:
LensApiDomainStructureArchitectureTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens API Service AS com.lens.api
    DEFINE DOMAIN Controller AS com.lens.api.controller
    DEFINE DOMAIN Domain AS com.lens.api.domain
    DEFINE DOMAIN Service AS com.lens.api.service
    DEFINE DOMAIN Client AS com.lens.api.client
    DEFINE DOMAIN Security AS com.lens.api.security
    DEFINE DOMAIN Configuration AS com.lens.api.config

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN
    {Controller, Domain, Service, Client, Security, Configuration})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-088: LENS API SERVICE — LLM CALL PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures lens-api has no dependency on any LLM client library. All
LLM calls belong in lens-agent.
PROMPT Write an ArchUnit test verifying no class under com.lens.api depends on
com.theokanning.openai, com.azure.ai.openai, or dev.langchain4j. Test class:
LensApiLlmCallProhibitionTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens API Service AS com.lens.api
  DEFINE LIBRARY OpenAI Library AS com.theokanning.openai
  DEFINE LIBRARY Azure OpenAI Library AS com.azure.ai.openai
  DEFINE LIBRARY LangChain Library AS dev.langchain4j

ASSERT(Lens API Service has NO DEPENDENCY ON OpenAI Library)
ASSERT(Lens API Service has NO DEPENDENCY ON Azure OpenAI Library)
ASSERT(Lens API Service has NO DEPENDENCY ON LangChain Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-089: LENS API SERVICE — RESTTEMPLATE PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures no class in lens-api depends on RestTemplate.
PROMPT Write an ArchUnit test verifying no class under com.lens.api imports
RestTemplate. Test class: LensApiRestTemplateProhibitionTest.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens API Service AS com.lens.api
  DEFINE LIBRARY Rest Template AS org.springframework.web.client.RestTemplate

FOREACH $X IN CLASSES DO
  ASSERT($X has NO DEPENDENCY ON Rest Template)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-090: LENS AGENT SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that all modules in lens-agent belong to one of the
defined domains.
PROMPT Write a PyTestArch test verifying every module under app resides in one
of (pipeline, tools, llm, models, prompts, api). Test function:
test_lens_agent_domain_structure.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens Agent Service AS lens-agent/app
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN LLM AS app.llm
    DEFINE DOMAIN Models AS app.models
    DEFINE DOMAIN Prompts AS app.prompts
    DEFINE DOMAIN API AS app.api

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN
    {Pipeline, Tools, LLM, Models, Prompts, API})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-091: LENS AGENT SERVICE — LLM DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures tools and pipeline domains in lens-agent have no direct
dependency on openai or langchain libraries.
PROMPT Write a PyTestArch test verifying no module under app.tools or
app.pipeline imports from openai or langchain_openai. Test function:
test_lens_llm_domain_isolation.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens Agent Service AS lens-agent/app
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Pipeline AS app.pipeline
  DEFINE LIBRARY OpenAI Library AS openai
  DEFINE LIBRARY LangChain Library AS langchain_openai

ASSERT(Tools has NO DEPENDENCY ON OpenAI Library)
ASSERT(Tools has NO DEPENDENCY ON LangChain Library)
ASSERT(Pipeline has NO DEPENDENCY ON OpenAI Library)
ASSERT(Pipeline has NO DEPENDENCY ON LangChain Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-092: LENS AGENT SERVICE — DATABASE ACCESS PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures lens-agent has no dependency on PostgreSQL client
libraries. All persistence belongs in lens-api.
PROMPT Write a PyTestArch test verifying no module under app imports from
psycopg2, asyncpg, or sqlalchemy. Test function:
test_lens_agent_database_access_prohibition.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens Agent Service AS lens-agent/app
  DEFINE LIBRARY Psycopg2 AS psycopg2
  DEFINE LIBRARY Asyncpg AS asyncpg
  DEFINE LIBRARY SQLAlchemy AS sqlalchemy

ASSERT(Lens Agent Service has NO DEPENDENCY ON Psycopg2)
ASSERT(Lens Agent Service has NO DEPENDENCY ON Asyncpg)
ASSERT(Lens Agent Service has NO DEPENDENCY ON SQLAlchemy)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-093: LENS AGENT — GAP ELICITATION NEVER BLOCKS USER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Gap elicitation must not exceed MAX_ROUNDS = 5. After round 5 the
system always sets canProceed = True and the user may proceed at any time.
Unresolved gaps become INSUFFICIENT_INFORMATION findings in the report — they
are never used to block the user.
PROMPT Write a pytest test that calls assess_gap_resolution with round=5,
max_rounds=5, and unanswered questions and verifies can_proceed=True is
returned. Also verify that when the user calls force_proceed in lens-api the
session transitions to READY_FOR_REVIEW regardless of gap state. Test function:
test_gap_elicitation_never_blocks_user.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens Agent Service AS lens-agent/app
  DEFINE COMPONENT GapAssessor AS app.tools.gap_assessor
  DEFINE CONST MAX_ROUNDS AS 5

ASSERT(GapAssessor RETURNS can_proceed = True
  WHEN round >= MAX_ROUNDS)
ASSERT(GapAssessor RETURNS can_proceed = True
  WHEN user_forced_proceed IS True)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-094: LENS AGENT — RISK AND RECOMMENDATION CAPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Risk register must not exceed MAX_RISKS = 20. Recommendation list
must not exceed MAX_RECOMMENDATIONS = 15. These caps ensure focused,
actionable output.
PROMPT Write a pytest test that mocks the risk identifier to return 25 risks and
verifies the report_assembly stage caps the list at 20. Repeat for
recommendations capped at 15. Test function:
test_risk_and_recommendation_caps.

DEFINE SYSTEM Axiom AS com.axiom
  DEFINE SERVICE Lens Agent Service AS lens-agent/app
  DEFINE COMPONENT RiskIdentifier AS app.tools.risk_identifier
  DEFINE COMPONENT RecommendationGenerator AS app.tools.recommendation_generator
  DEFINE CONST MAX_RISKS AS 20
  DEFINE CONST MAX_RECOMMENDATIONS AS 15

ASSERT(RiskIdentifier RETURNS AT MOST MAX_RISKS items)
ASSERT(RecommendationGenerator RETURNS AT MOST MAX_RECOMMENDATIONS items)
```
