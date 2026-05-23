# Architecture Definition Language — Archon

This file defines the complete Architecture Definition Language (ADL) specification for the AI Architect Assistant system. Each ADL block encodes a structural constraint derived from the architecture governance rules in `ARCHITECTURE.md`. Blocks are machine-readable pseudo-code designed to be converted into executable fitness functions by an LLM, enabling continuous architectural conformance checking across the API Gateway, Agent Orchestration, and UI services.

## Specification reference

This ADL follows Mark Richards Architecture Definition Language specification published at [developertoarchitect.com/downloads/adl-ref.pdf](https://developertoarchitect.com/downloads/adl-ref.pdf). The specification defines a minimal keyword set for expressing architectural constraints as testable pseudo-code. Keywords include artifact declarations (`DEFINE SYSTEM`, `DEFINE DOMAIN`, `DEFINE SUBDOMAIN`, `DEFINE COMPONENT`, `DEFINE LIBRARY`, `DEFINE SERVICE`, `DEFINE CONST`), constraint constructs (`ASSERT`, `FOREACH...END`), collection nouns (`CLASSES`, `DOMAINS`, `SUBDOMAINS`, `COMPONENTS`, `SERVICES`), and relationship verbs (`CONTAINED WITHIN`, `CONTAINS`, `DEPENDS ON`, `DEPENDENCY ON`, `NO DEPENDENCY ON`, `EXCLUSIVELY`). Each block also carries three metadata fields — `REQUIRES`, `DESCRIPTION`, and `PROMPT` — that support the code-generation workflow. No keywords beyond this published set are used anywhere in this document.

## How to use these blocks

Each ADL block is self-contained and can be independently converted into an executable fitness function:

1. **Strip metadata.** Remove the three metadata lines (`REQUIRES`, `DESCRIPTION`, `PROMPT`) from the block. The remaining pseudo-code is the pure ADL specification.
2. **Send to LLM.** Pass the stripped pseudo-code to an LLM together with the `PROMPT` text as the user instruction. The `PROMPT` is specific enough to produce compilable output from the pseudo-code alone.
3. **Install tooling.** The `REQUIRES` line names the exact tooling needed to execute the generated test. Install the required library or tool before running the output:
   - **ArchUnit Java library** — Java architectural tests using JUnit 5 and ArchUnit 1.x
   - **PyTestArch Python library** — Python architectural tests using pytest and pytestarch
   - **ESLint with import plugin** — TypeScript import boundary rules using eslint-plugin-import
   - **Custom fitness function via Semgrep** — pattern-based security rules in Semgrep YAML format
   - **Custom fitness function via grep** — CI-level bash scripts for GitHub Actions
4. **Apply enforcement.** Each block is assigned a **Hard** or **Soft** enforcement level (see the enforcement table at the end of this document). Hard blocks must fail the CI build on violation. Soft blocks emit warnings but allow the build to continue.

## Service index

| Block ID | Service             | Description                    | Tooling                             | Enforcement |
|----------|---------------------|--------------------------------|-------------------------------------|-------------|
| ADL-001  | Cross-service       | System and service boundaries  | Custom fitness function via grep    | Soft        |
| ADL-002  | API Gateway         | Domain structure               | ArchUnit Java library               | Soft        |
| ADL-003  | API Gateway         | Conversation domain components | ArchUnit Java library               | Soft        |
| ADL-004  | API Gateway         | LLM call prohibition           | ArchUnit Java library               | Hard        |
| ADL-005  | API Gateway         | RestTemplate prohibition       | ArchUnit Java library               | Hard        |
| ADL-006  | API Gateway         | Bridge domain isolation        | ArchUnit Java library               | Soft        |
| ADL-007  | API Gateway         | Database access boundary       | ArchUnit Java library               | Hard        |
| ADL-008  | Agent Orchestration | Domain structure               | PyTestArch Python library           | Soft        |
| ADL-009  | Agent Orchestration | Pipeline domain components     | PyTestArch Python library           | Soft        |
| ADL-010  | Agent Orchestration | Tools domain components        | PyTestArch Python library           | Soft        |
| ADL-011  | Agent Orchestration | Tool dependency rule           | PyTestArch Python library           | Soft        |
| ADL-012  | Agent Orchestration | Pipeline nodes dependency rule | PyTestArch Python library           | Soft        |
| ADL-013  | Agent Orchestration | LLM domain isolation           | PyTestArch Python library           | Hard        |
| ADL-014  | Agent Orchestration | Memory domain isolation        | PyTestArch Python library           | Hard        |
| ADL-015  | Agent Orchestration | Prompt template isolation      | Custom fitness function via grep    | Soft        |
| ADL-016  | Agent Orchestration | ArchitectureContext ownership  | PyTestArch Python library           | Soft        |
| ADL-017  | Agent Orchestration | API domain boundary            | PyTestArch Python library           | Soft        |
| ADL-018  | Agent Orchestration | Stage event contract           | Custom fitness function via grep    | Soft        |
| ADL-019  | Agent Orchestration | Secret prohibition             | Custom fitness function via Semgrep | Hard        |
| ADL-020  | UI                  | Domain structure               | ESLint with import plugin           | Soft        |
| ADL-021  | UI                  | API call boundary              | ESLint with import plugin           | Soft        |
| ADL-022  | UI                  | State management boundary      | ESLint with import plugin           | Soft        |
| ADL-023  | UI                  | Token storage prohibition      | Custom fitness function via grep    | Hard        |
| ADL-024  | Cross-service       | Database access prohibition    | PyTestArch Python library           | Hard        |
| ADL-025  | Cross-service       | Qdrant access prohibition      | ArchUnit Java library               | Hard        |
| ADL-026  | Cross-service       | Tactic entity domain isolation | Custom fitness function via grep    | Hard        |
| ADL-027  | API Gateway         | Tactic write path enforcement  | Custom fitness function via grep    | Hard        |
| ADL-028  | Agent Orchestration | Tactic catalog enforcement     | Custom fitness function via Semgrep | Hard        |
| ADL-033  | Infra               | HTTPS enforcement on ingress   | Custom fitness function via grep    | Hard        |

## ADL blocks

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-001: SYSTEM AND SERVICE BOUNDARIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures the three deployed services have no compile-time dependencies on each other.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a GitHub Actions step that verifies no source file in any of the three services imports from another service's root namespace or module path. Exit with code 1 if a cross-service import is found.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
  DEFINE SERVICE Agent Orchestration Service AS app
  DEFINE SERVICE UI Service AS ui/src

ASSERT(API Gateway Service has NO DEPENDENCY ON Agent Orchestration Service)
ASSERT(API Gateway Service has NO DEPENDENCY ON UI Service)
ASSERT(Agent Orchestration Service has NO DEPENDENCY ON API Gateway Service)
ASSERT(Agent Orchestration Service has NO DEPENDENCY ON UI Service)
ASSERT(UI Service has NO DEPENDENCY ON API Gateway Service)
ASSERT(UI Service has NO DEPENDENCY ON Agent Orchestration Service)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-002: API GATEWAY SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Enforces that all classes in the API Gateway Service belong to one of the five defined domains.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies every class under com.aiarchitect.api resides in one of the five domain packages (controller, domain, security, client, config). Use JUnit 5 and ArchUnit 1.x. The test class should be named ApiGatewayDomainStructureArchitectureTest.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
    DEFINE DOMAIN Chat AS com.aiarchitect.api.controller
    DEFINE DOMAIN Conversation AS com.aiarchitect.api.domain
    DEFINE DOMAIN Security AS com.aiarchitect.api.security
    DEFINE DOMAIN Bridge AS com.aiarchitect.api.client
    DEFINE DOMAIN Configuration AS com.aiarchitect.api.config

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN {Chat, Conversation, Security, Bridge, Configuration})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-003: API GATEWAY SERVICE — CONVERSATION DOMAIN COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Enforces that the seven conversation domain components are contained within the conversation domain and that all classes reside within a component.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies the seven component packages exist within com.aiarchitect.api.domain and com.aiarchitect.api.service, and that every class within the conversation domain belongs to one of those component packages. Use JUnit 5 and ArchUnit 1.x. The test class should be named ConversationDomainComponentsArchitectureTest.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
    DEFINE DOMAIN Conversation AS com.aiarchitect.api.domain
      DEFINE COMPONENT Conversation Model AS com.aiarchitect.api.domain.model
      DEFINE COMPONENT Conversation Repository AS com.aiarchitect.api.domain.repository
      DEFINE COMPONENT Chat Service AS com.aiarchitect.api.service
      DEFINE COMPONENT Conversation Service AS com.aiarchitect.api.service
      DEFINE COMPONENT Architecture Output Service AS com.aiarchitect.api.service
      DEFINE COMPONENT ADL Service AS com.aiarchitect.api.service
      DEFINE COMPONENT Trade Off Service AS com.aiarchitect.api.service

FOREACH $X IN COMPONENTS DO
  ASSERT($X CONTAINED WITHIN Conversation)
END

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN {Conversation Model, Conversation Repository, Chat Service, Conversation Service, Architecture Output Service, ADL Service, Trade Off Service})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-004: API GATEWAY SERVICE — LLM CALL PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures the API Gateway Service has no dependency on any LLM client library.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no class under com.aiarchitect.api depends on com.theokanning.openai, com.azure.ai.openai, or dev.langchain4j packages. Use JUnit 5 and ArchUnit 1.x. The test class should be named LlmCallProhibitionArchitectureTest.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
  DEFINE LIBRARY OpenAI Library AS com.theokanning.openai
  DEFINE LIBRARY Azure OpenAI Library AS com.azure.ai.openai
  DEFINE LIBRARY LangChain Library AS dev.langchain4j

ASSERT(API Gateway Service has NO DEPENDENCY ON OpenAI Library)
ASSERT(API Gateway Service has NO DEPENDENCY ON Azure OpenAI Library)
ASSERT(API Gateway Service has NO DEPENDENCY ON LangChain Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-005: API GATEWAY SERVICE — RESTTEMPLATE PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures no class in the API Gateway Service depends on RestTemplate.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no class under com.aiarchitect.api imports or depends on org.springframework.web.client.RestTemplate. Use JUnit 5 and ArchUnit 1.x. The test class should be named RestTemplateProhibitionArchitectureTest.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
  DEFINE LIBRARY Rest Template AS org.springframework.web.client.RestTemplate

FOREACH $X IN CLASSES DO
  ASSERT($X has NO DEPENDENCY ON Rest Template)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-006: API GATEWAY SERVICE — BRIDGE DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures the bridge domain has no dependency on the conversation domain or chat domain.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies classes in com.aiarchitect.api.client do not depend on com.aiarchitect.api.domain or com.aiarchitect.api.controller. Use JUnit 5 and ArchUnit 1.x. The test class should be named BridgeDomainIsolationArchitectureTest.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
    DEFINE DOMAIN Chat AS com.aiarchitect.api.controller
    DEFINE DOMAIN Conversation AS com.aiarchitect.api.domain
    DEFINE DOMAIN Bridge AS com.aiarchitect.api.client

ASSERT(Bridge has NO DEPENDENCY ON Conversation)
ASSERT(Bridge has NO DEPENDENCY ON Chat)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-007: API GATEWAY SERVICE — DATABASE ACCESS BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures chat controller and agent bridge client have no dependency on JPA or JDBC libraries.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies classes in com.aiarchitect.api.controller and com.aiarchitect.api.client do not depend on jakarta.persistence or org.springframework.jdbc. Use JUnit 5 and ArchUnit 1.x. The test class should be named DatabaseAccessBoundaryArchitectureTest.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
    DEFINE DOMAIN Chat AS com.aiarchitect.api.controller
    DEFINE DOMAIN Bridge AS com.aiarchitect.api.client
  DEFINE LIBRARY JPA Library AS jakarta.persistence
  DEFINE LIBRARY JDBC Library AS org.springframework.jdbc

ASSERT(Chat has NO DEPENDENCY ON JPA Library)
ASSERT(Chat has NO DEPENDENCY ON JDBC Library)
ASSERT(Bridge has NO DEPENDENCY ON JPA Library)
ASSERT(Bridge has NO DEPENDENCY ON JDBC Library)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-008: AGENT ORCHESTRATION SERVICE — DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that all modules in the Agent Orchestration Service belong to one of the seven defined domains.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies every module under app resides in one of the seven domain packages (pipeline, tools, llm, memory, models, prompts, api). Use pytest and pyTestArch. The test function should be named test_agent_domain_structure.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
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
ADL-009: AGENT ORCHESTRATION SERVICE — PIPELINE DOMAIN COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that graph and nodes components are contained within the pipeline domain.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies app.pipeline.graph and app.pipeline.nodes modules reside within the app.pipeline package. Use pytest and pyTestArch. The test function should be named test_pipeline_domain_components.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
      DEFINE COMPONENT Graph AS app.pipeline.graph
      DEFINE COMPONENT Nodes AS app.pipeline.nodes

ASSERT(Graph CONTAINED WITHIN Pipeline)
ASSERT(Nodes CONTAINED WITHIN Pipeline)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-010: AGENT ORCHESTRATION SERVICE — TOOLS DOMAIN COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Enforces that all twelve tool components are contained within the tools domain.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies all twelve tool modules reside within the app.tools package. Use pytest and pyTestArch. The test function should be named test_tools_domain_components.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
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
ADL-011: AGENT ORCHESTRATION SERVICE — TOOL DEPENDENCY RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures the tools domain has no dependency on the pipeline or api domains.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies no module under app.tools imports from app.pipeline or app.api. Use pytest and pyTestArch. The test function should be named test_tool_dependency_rule.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN API AS app.api

ASSERT(Tools has NO DEPENDENCY ON Pipeline)
ASSERT(Tools has NO DEPENDENCY ON API)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-012: AGENT ORCHESTRATION SERVICE — PIPELINE NODES DEPENDENCY RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures the nodes component depends on tool registry only and not on the broader tools domain directly.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies app.pipeline.nodes imports only from app.tools.registry and does not import from any other module under app.tools. Use pytest and pyTestArch. The test function should be named test_pipeline_nodes_dependency_rule.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
      DEFINE COMPONENT Nodes AS app.pipeline.nodes
    DEFINE DOMAIN Tools AS app.tools
      DEFINE COMPONENT Tool Registry AS app.tools.registry
      DEFINE COMPONENT Base Tool AS app.tools.base
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

ASSERT(Nodes DEPENDS ON Tool Registry EXCLUSIVELY)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-013: AGENT ORCHESTRATION SERVICE — LLM DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures tools, pipeline, and memory domains have no dependency on OpenAI or LangChain libraries.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies no module under app.tools, app.pipeline, or app.memory imports from the openai or langchain_openai packages. Use pytest and pyTestArch. The test function should be named test_llm_domain_isolation.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
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
ADL-014: AGENT ORCHESTRATION SERVICE — MEMORY DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures tools and pipeline domains have no dependency on the Qdrant client library.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies no module under app.tools or app.pipeline imports from the qdrant_client package. Use pytest and pyTestArch. The test function should be named test_memory_domain_isolation.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN Pipeline AS app.pipeline
  DEFINE LIBRARY Qdrant Client AS qdrant_client

ASSERT(Tools has NO DEPENDENCY ON Qdrant Client)
ASSERT(Pipeline has NO DEPENDENCY ON Qdrant Client)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-015: AGENT ORCHESTRATION SERVICE — PROMPT TEMPLATE ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures no tool class contains an inline prompt string exceeding 200 characters.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a GitHub Actions step that scans all Python files under app/tools/ for string literals longer than 200 characters and flags them as inline prompt templates that should be moved to Jinja2 files in app/prompts/. Exit with code 1 if any match is found.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
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
  DEFINE CONST MAX-INLINE-STRING AS 200 CHARS

FOREACH $X IN COMPONENTS DO
  ASSERT($X has NO DEPENDENCY ON MAX-INLINE-STRING)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-016: AGENT ORCHESTRATION SERVICE — ARCHITECTURECONTEXT OWNERSHIP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures ArchitectureContext is only contained within the models domain and that tools, pipeline, and api domains depend on models.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies app.models.context is only within app.models, and that app.tools, app.pipeline, and app.api each import from app.models. Use pytest and pyTestArch. The test function should be named test_architecture_context_ownership.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
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
ADL-017: AGENT ORCHESTRATION SERVICE — API DOMAIN BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures pipeline, tools, memory, and llm domains have no dependency on the api domain.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies no module under app.pipeline, app.tools, app.memory, or app.llm imports from app.api. Use pytest and pyTestArch. The test function should be named test_api_domain_boundary.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
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
ADL-018: AGENT ORCHESTRATION SERVICE — STAGE EVENT CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures every pipeline node emits STAGE_START and STAGE_COMPLETE events.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a GitHub Actions step that parses app/pipeline/nodes.py and verifies every async stage function emits both a STAGE_START and STAGE_COMPLETE event. Exit with code 1 if any stage function is missing either event.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
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
ADL-019: AGENT ORCHESTRATION SERVICE — SECRET PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via Semgrep
DESCRIPTION Ensures no domain in the agent service contains hardcoded credential strings.
PROMPT Based on this pseudo-code, write a Semgrep rule in YAML that detects hardcoded API keys (strings starting with sk-), hardcoded password assignments, and hardcoded secret assignments in Python files under app/. The rule id should be aiarchitect-secret-prohibition.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
    DEFINE DOMAIN Pipeline AS app.pipeline
    DEFINE DOMAIN Tools AS app.tools
    DEFINE DOMAIN LLM AS app.llm
    DEFINE DOMAIN Memory AS app.memory
    DEFINE DOMAIN Models AS app.models
    DEFINE DOMAIN Prompts AS app.prompts
    DEFINE DOMAIN API AS app.api
  DEFINE CONST FORBIDDEN_API_KEY AS "sk-"
  DEFINE CONST FORBIDDEN_PASSWORD AS "password="
  DEFINE CONST FORBIDDEN_SECRET AS "secret="

FOREACH $X IN DOMAINS DO
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
DESCRIPTION Enforces that all modules in the UI Service belong to one of the six defined domains.
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the eslint-plugin-import that enforces all source files under ui/src reside within one of the six defined domain directories (views, components, hooks, api, store, types). Output as a valid .eslintrc.json fragment.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE UI Service AS ui/src
    DEFINE DOMAIN Views AS ui/src/views
    DEFINE DOMAIN Components AS ui/src/components
    DEFINE DOMAIN Hooks AS ui/src/hooks
    DEFINE DOMAIN API Client AS ui/src/api
    DEFINE DOMAIN Store AS ui/src/store
    DEFINE DOMAIN Types AS ui/src/types

FOREACH $X IN CLASSES DO
  ASSERT($X CONTAINED WITHIN {Views, Components, Hooks, API Client, Store, Types})
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-021: UI SERVICE — API CALL BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ESLint with import plugin
DESCRIPTION Ensures views and components domains do not directly depend on the fetch API.
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the eslint-plugin-import that prohibits direct use of the fetch function in files under ui/src/views and ui/src/components, requiring all HTTP calls to go through ui/src/api modules instead. Output as a valid .eslintrc.json fragment.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE UI Service AS ui/src
    DEFINE DOMAIN Views AS ui/src/views
    DEFINE DOMAIN Components AS ui/src/components
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
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the eslint-plugin-import that prohibits files under ui/src/views from importing directly from ui/src/store, while allowing ui/src/hooks to import from ui/src/store. Views must access state exclusively through hooks. Output as a valid .eslintrc.json fragment.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE UI Service AS ui/src
    DEFINE DOMAIN Views AS ui/src/views
    DEFINE DOMAIN Hooks AS ui/src/hooks
    DEFINE DOMAIN Store AS ui/src/store

ASSERT(Views DEPENDS ON Hooks)
ASSERT(Views has NO DEPENDENCY ON Store)
ASSERT(Hooks DEPENDS ON Store)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-023: UI SERVICE — TOKEN STORAGE PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures no domain in the UI service stores tokens in localStorage or sessionStorage.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a GitHub Actions step that scans all TypeScript and TSX files under ui/src/ for calls to localStorage.setItem or sessionStorage.setItem. Exit with code 1 if any match is found.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE UI Service AS ui/src
    DEFINE DOMAIN Views AS ui/src/views
    DEFINE DOMAIN Components AS ui/src/components
    DEFINE DOMAIN Hooks AS ui/src/hooks
    DEFINE DOMAIN API Client AS ui/src/api
    DEFINE DOMAIN Store AS ui/src/store
    DEFINE DOMAIN Types AS ui/src/types
  DEFINE CONST FORBIDDEN_LOCAL_STORAGE AS "localStorage.setItem"
  DEFINE CONST FORBIDDEN_SESSION_STORAGE AS "sessionStorage.setItem"

FOREACH $X IN DOMAINS DO
  ASSERT($X has NO DEPENDENCY ON FORBIDDEN_LOCAL_STORAGE)
  ASSERT($X has NO DEPENDENCY ON FORBIDDEN_SESSION_STORAGE)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-024: CROSS-SERVICE — DATABASE ACCESS PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Ensures the Agent Orchestration Service has no dependency on PostgreSQL client libraries.
PROMPT Based on this pseudo-code, write a PyTestArch test in Python that verifies no module under app imports from psycopg2, asyncpg, or sqlalchemy. Use pytest and pyTestArch. The test function should be named test_agent_database_access_prohibition.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE Agent Orchestration Service AS app
  DEFINE LIBRARY Psycopg2 AS psycopg2
  DEFINE LIBRARY Asyncpg AS asyncpg
  DEFINE LIBRARY SQLAlchemy AS sqlalchemy

ASSERT(Agent Orchestration Service has NO DEPENDENCY ON Psycopg2)
ASSERT(Agent Orchestration Service has NO DEPENDENCY ON Asyncpg)
ASSERT(Agent Orchestration Service has NO DEPENDENCY ON SQLAlchemy)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-025: CROSS-SERVICE — QDRANT ACCESS PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures the API Gateway Service has no dependency on the Qdrant Java client.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no class under com.aiarchitect.api depends on the io.qdrant package. Use JUnit 5 and ArchUnit 1.x. The test class should be named QdrantAccessProhibitionArchitectureTest.

DEFINE SYSTEM AI Architect Assistant AS com.aiarchitect
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
  DEFINE LIBRARY Qdrant Java Client AS io.qdrant

ASSERT(API Gateway Service has NO DEPENDENCY ON Qdrant Java Client)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-026: CROSS-SERVICE — TACTIC ENTITY DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures the ArchitectureTactic entity lives exclusively in ai-architect-api.
The Python agent must never import or reference the Java entity directly.
PROMPT Based on this pseudo-code, write a bash fitness function that:
1. Verifies no Python file under ai-architect-agent/ contains the string "ArchitectureTactic" as a type reference.
2. Verifies no Python file under ai-architect-agent/ imports from any Java package.
Emit a PASS or FAIL result with file and line details on failure.

DEFINE SYSTEM AI Architect Assistant
  DEFINE SERVICE API Gateway Service AS ai-architect-api
  DEFINE SERVICE Agent Orchestration Service AS ai-architect-agent
  DEFINE COMPONENT Tactic Entity AS com.aiarchitect.api.domain.model.ArchitectureTactic

ASSERT(Tactic Entity CONTAINED WITHIN API Gateway Service)
ASSERT(Agent Orchestration Service has NO DEPENDENCY ON Tactic Entity)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-027: API GATEWAY — TACTIC WRITE PATH ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures tactics are written to the database only from ChatService.doOnComplete()
via TacticsService.saveTactics(). No other write path is permitted; controllers
and other services must never call TacticRepository directly.
PROMPT Based on this pseudo-code, write a bash fitness function that:
1. Scans all Java files under ai-architect-api/src/ for calls to TacticRepository.save or TacticRepository.saveAll.
2. Flags any caller that is NOT TacticsService.
3. Scans all Java files for calls to tacticsService.saveTactics and flags any caller that is NOT ChatService.
Emit PASS if no violations are found, FAIL with file and line details otherwise.

DEFINE SYSTEM AI Architect Assistant
  DEFINE SERVICE API Gateway Service AS com.aiarchitect.api
  DEFINE COMPONENT ChatService AS com.aiarchitect.api.service.ChatService
  DEFINE COMPONENT TacticsService AS com.aiarchitect.api.service.TacticsService
  DEFINE COMPONENT TacticRepository AS com.aiarchitect.api.domain.repository.TacticRepository

ASSERT(TacticRepository EXCLUSIVELY ACCESSED BY TacticsService)
ASSERT(TacticsService.saveTactics EXCLUSIVELY CALLED BY ChatService)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-028: AGENT ORCHESTRATION — TACTIC CATALOG ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via Semgrep
DESCRIPTION Ensures TacticsAdvisorTool only recommends tactics from the Bass, Clements, and
Kazman "Software Architecture in Practice" catalog embedded in tactics_advisor.j2.
The LLM prompt must reference the catalog template; ad-hoc tactic names must not
be hardcoded in the Python tool itself.
PROMPT Based on this pseudo-code, write a Semgrep YAML rule that:
1. Detects any string literal in app/tools/tactics_advisor.py that looks like a tactic name
   (heuristic: title-case multi-word string longer than 10 chars not adjacent to a known variable name).
2. Flags it as a violation: tactic names must live in tactics_advisor.j2, not in Python source.
Emit the rule in standard Semgrep YAML format with message, severity: WARNING, and languages: [python].

DEFINE SYSTEM AI Architect Assistant
  DEFINE SERVICE Agent Orchestration Service AS ai-architect-agent
  DEFINE COMPONENT TacticsAdvisorTool AS app.tools.tactics_advisor.TacticsAdvisorTool
  DEFINE COMPONENT TacticsCatalog AS app.prompts.tactics_advisor

ASSERT(TacticsAdvisorTool DEPENDS ON TacticsCatalog EXCLUSIVELY)
ASSERT(TacticsAdvisorTool has NO hardcoded tactic names in Python source)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-033: HTTPS ENFORCEMENT ON INGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Assert that the ingress template enforces TLS and that the ssl-redirect
             annotation is present so HTTP traffic is redirected to HTTPS. Checks both
             the template file and the values file to confirm a real CA issuer is
             configured and not a self-signed certificate.
PROMPT Based on this pseudo-code, write a bash script for GitHub Actions that checks:
       (1) helm/ai-architect/templates/ingress.yaml contains the string 'ssl-redirect'
           as evidence the HTTP to HTTPS redirect annotation is configured.
       (2) helm/ai-architect/values.yaml contains 'letsencrypt' as evidence a real CA
           issuer is configured rather than a self-signed certificate.
       (3) helm/ai-architect/templates/ingress.yaml contains a tls: block.
       Exit with code 1 if any check fails.
       Rule id: aiarchitect-https-enforcement.

DEFINE SYSTEM AIArchitect AS helm/ai-architect
DEFINE CONST TLS_ANNOTATION    AS "ssl-redirect"
DEFINE CONST ISSUER_REFERENCE  AS "letsencrypt"
DEFINE CONST TLS_BLOCK         AS "tls:"
DEFINE COMPONENT IngressTemplate AS helm/ai-architect/templates/ingress.yaml
DEFINE COMPONENT IngressValues   AS helm/ai-architect/values.yaml

ASSERT(IngressTemplate CONTAINS TLS_ANNOTATION)
ASSERT(IngressValues   CONTAINS ISSUER_REFERENCE)
ASSERT(IngressTemplate CONTAINS TLS_BLOCK)
```

## Enforcement levels

| Block ID | Enforcement | Rationale |
|----------|-------------|-----------|
| ADL-001  | Soft        | Cross-service isolation is guaranteed by separate language runtimes; this block documents the architectural intent and catches accidental cross-references. |
| ADL-002  | Soft        | Domain organization improves navigability; violations are structural debt, not runtime risks. |
| ADL-003  | Soft        | Component granularity within the conversation domain improves maintainability but doesn't affect correctness. |
| ADL-004  | Hard        | LLM client calls from the API gateway would bypass the agent's orchestration pipeline, causing duplicate billing, inconsistent behavior, and scattered API key usage. |
| ADL-005  | Hard        | RestTemplate is blocking and will deadlock the SSE streaming threads, causing observable runtime failures. |
| ADL-006  | Soft        | Bridge domain isolation reduces coupling but violations are refactorable without immediate runtime impact. |
| ADL-007  | Hard        | Direct database access from controllers or bridge clients bypasses the repository layer's validation and transaction management, risking data corruption. |
| ADL-008  | Soft        | Domain organization in the agent service improves navigability; violations are structural debt. |
| ADL-009  | Soft        | Pipeline component containment improves discoverability but doesn't affect correctness. |
| ADL-010  | Soft        | Tool component containment improves discoverability but doesn't affect correctness. |
| ADL-011  | Soft        | Tool independence from pipeline prevents circular dependencies but is not a security or runtime risk. |
| ADL-012  | Soft        | Nodes depending only on the registry prevents tight coupling to individual tools but violations are refactorable. |
| ADL-013  | Hard        | LLM library imports outside the LLM domain scatter API key usage and make model switching impossible without a multi-file refactor. |
| ADL-014  | Hard        | Qdrant client usage outside the memory domain fragments vector store access and breaks the single-responsibility of MemoryStore. |
| ADL-015  | Soft        | Inline prompt strings reduce template reusability but don't cause runtime failures; refactoring to Jinja2 templates is non-urgent. |
| ADL-016  | Soft        | Context ownership ensures single source of truth for pipeline state; violations create maintenance burden but not runtime errors. |
| ADL-017  | Soft        | API boundary prevents reverse dependencies that would complicate deployment, but violations are structural debt. |
| ADL-018  | Soft        | Stage events are essential for UI progress display but missing events degrade user experience, not security or data integrity. |
| ADL-019  | Hard        | Hardcoded secrets are a critical security vulnerability that could leak credentials through version control or logs. |
| ADL-020  | Soft        | UI domain structure improves navigability; violations are structural debt, not runtime risks. |
| ADL-021  | Soft        | API call boundary centralizes error handling and retry logic but violations are refactorable without runtime risk. |
| ADL-022  | Soft        | State management layering improves testability and debugging but violations don't cause runtime failures. |
| ADL-023  | Hard        | Storing tokens in localStorage or sessionStorage exposes them to cross-site scripting (XSS) attacks, creating a security vulnerability. |
| ADL-024  | Hard        | The agent service must not access PostgreSQL directly; only the API service owns relational data. A violation would bypass schema management and split data ownership. |
| ADL-025  | Hard        | The API service must not access Qdrant directly; only the agent service owns vector data. A violation would bypass the MemoryStore abstraction and split data ownership. |
| ADL-026  | Hard        | The ArchitectureTactic entity is owned exclusively by the API service; agent code must not reference it directly. A violation would split domain ownership and couple the Python agent to the Java persistence model. |
| ADL-027  | Hard        | Tactics must only be written through TacticsService.saveTactics() called from ChatService.doOnComplete(). A second write path would create duplicate records and race conditions with the pipeline streaming response. |
| ADL-028  | Hard        | Tactic names must live in the Jinja2 catalog template, not hardcoded in Python. Inline names bypass the Bass/Clements/Kazman catalog constraint and make the tool unauditable. |
| ADL-033  | Hard        | Serving the application over HTTP exposes user sessions, JWT tokens, and architecture data in plaintext. The ssl-redirect annotation and a valid CA issuer (letsencrypt-staging or letsencrypt-prod) are both required. CI must fail if either is removed. Self-signed certificates are not acceptable; they produce the same browser warning as HTTP-only deployment. |
