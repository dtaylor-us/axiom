# Architecture Definition Language — Archon

This file defines the complete Architecture Definition Language (ADL) specification for the Axiom system. Each ADL block encodes a structural constraint derived from the architecture governance rules in `ARCHITECTURE.md`. Blocks are machine-readable pseudo-code designed to be converted into executable fitness functions by an LLM, enabling continuous architectural conformance checking across the API Gateway, Agent Orchestration, and UI services.

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
| ADL-034  | Agent Orchestration | Structured output schema enforcement | Custom fitness function via pytest | Hard        |
| ADL-057  | archon-api    | Workshop session boundary      | Custom fitness function (bash)    | Hard        |
| ADL-058  | archon-agent  | Workshop module isolation      | pytest + bash (adl-037/038.sh)   | Hard        |
| ADL-059  | archon-api    | Password reset token storage security | Custom fitness function via grep | Hard        |
| ADL-062  | archon-agent  | Implication mechanism prohibition | Custom fitness function via grep | Hard        |
| ADL-063  | archon-api    | Send-to-pipeline includes all attributes | ArchUnit Java library | Hard        |
| ADL-064  | archon-api/ui | Idempotency key on pipeline submission | Custom fitness function via grep | Hard        |
| ADL-065  | archon-agent  | Scenario deduplication before pipeline | PyTestArch Python library | Hard        |
| ADL-069  | archon-agent  | LLM provider abstraction       | PyTestArch Python library         | Hard        |
| ADL-070  | archon-agent  | stage_name required on LLM calls | Custom fitness function via grep | Hard        |
| ADL-071  | axiom-api/archon-api | Gateway is sole JWT validation point | ArchUnit Java library | Hard        |
| ADL-072  | Cross-pillar   | Pillars must not import from each other | PyTestArch Python library | Hard        |
| ADL-073  | Platform       | Maximum two services per pillar | Custom bash fitness function | Hard        |

## ADL blocks

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-001: SYSTEM AND SERVICE BOUNDARIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures the three deployed services have no compile-time dependencies on each other.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a GitHub Actions step that verifies no source file in any of the three services imports from another service's root namespace or module path. Exit with code 1 if a cross-service import is found.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
  DEFINE SERVICE Agent Orchestration Service AS app
  DEFINE SERVICE UI Service AS axiom-ui/src

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
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies every class under com.archon.api resides in one of the five domain packages (controller, domain, security, client, config). Use JUnit 5 and ArchUnit 1.x. The test class should be named ApiGatewayDomainStructureArchitectureTest.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
    DEFINE DOMAIN Chat AS com.archon.api.controller
    DEFINE DOMAIN Conversation AS com.archon.api.domain
    DEFINE DOMAIN Security AS com.archon.api.security
    DEFINE DOMAIN Bridge AS com.archon.api.client
    DEFINE DOMAIN Configuration AS com.archon.api.config

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
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies the seven component packages exist within com.archon.api.domain and com.archon.api.service, and that every class within the conversation domain belongs to one of those component packages. Use JUnit 5 and ArchUnit 1.x. The test class should be named ConversationDomainComponentsArchitectureTest.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
    DEFINE DOMAIN Conversation AS com.archon.api.domain
      DEFINE COMPONENT Conversation Model AS com.archon.api.domain.model
      DEFINE COMPONENT Conversation Repository AS com.archon.api.domain.repository
      DEFINE COMPONENT Chat Service AS com.archon.api.service
      DEFINE COMPONENT Conversation Service AS com.archon.api.service
      DEFINE COMPONENT Architecture Output Service AS com.archon.api.service
      DEFINE COMPONENT ADL Service AS com.archon.api.service
      DEFINE COMPONENT Trade Off Service AS com.archon.api.service

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
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no class under com.archon.api depends on com.theokanning.openai, com.azure.ai.openai, or dev.langchain4j packages. Use JUnit 5 and ArchUnit 1.x. The test class should be named LlmCallProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
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
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no class under com.archon.api imports or depends on org.springframework.web.client.RestTemplate. Use JUnit 5 and ArchUnit 1.x. The test class should be named RestTemplateProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
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
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies classes in com.archon.api.client do not depend on com.archon.api.domain or com.archon.api.controller. Use JUnit 5 and ArchUnit 1.x. The test class should be named BridgeDomainIsolationArchitectureTest.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
    DEFINE DOMAIN Chat AS com.archon.api.controller
    DEFINE DOMAIN Conversation AS com.archon.api.domain
    DEFINE DOMAIN Bridge AS com.archon.api.client

ASSERT(Bridge has NO DEPENDENCY ON Conversation)
ASSERT(Bridge has NO DEPENDENCY ON Chat)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-007: API GATEWAY SERVICE — DATABASE ACCESS BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Ensures chat controller and agent bridge client have no dependency on JPA or JDBC libraries.
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies classes in com.archon.api.controller and com.archon.api.client do not depend on jakarta.persistence or org.springframework.jdbc. Use JUnit 5 and ArchUnit 1.x. The test class should be named DatabaseAccessBoundaryArchitectureTest.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
    DEFINE DOMAIN Chat AS com.archon.api.controller
    DEFINE DOMAIN Bridge AS com.archon.api.client
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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

DEFINE SYSTEM Axiom AS com.archon
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
PROMPT Based on this pseudo-code, write a Semgrep rule in YAML that detects hardcoded API keys (strings starting with sk-), hardcoded password assignments, and hardcoded secret assignments in Python files under app/. The rule id should be axiom-secret-prohibition.

DEFINE SYSTEM Axiom AS com.archon
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
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the eslint-plugin-import that enforces all source files under axiom-ui/src reside within one of the six defined domain directories (views, components, hooks, api, store, types). Output as a valid .eslintrc.json fragment.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE UI Service AS axiom-ui/src
    DEFINE DOMAIN Views AS axiom-ui/src/views
    DEFINE DOMAIN Components AS axiom-ui/src/components
    DEFINE DOMAIN Hooks AS axiom-ui/src/hooks
    DEFINE DOMAIN API Client AS axiom-ui/src/api
    DEFINE DOMAIN Store AS axiom-ui/src/store
    DEFINE DOMAIN Types AS axiom-ui/src/types

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
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the eslint-plugin-import that prohibits direct use of the fetch function in files under axiom-ui/src/views and axiom-ui/src/components, requiring all HTTP calls to go through axiom-ui/src/api modules instead. Output as a valid .eslintrc.json fragment.

DEFINE SYSTEM Axiom AS com.archon
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
PROMPT Based on this pseudo-code, write an ESLint configuration rule using the eslint-plugin-import that prohibits files under axiom-ui/src/views from importing directly from axiom-ui/src/store, while allowing axiom-ui/src/hooks to import from axiom-ui/src/store. Views must access state exclusively through hooks. Output as a valid .eslintrc.json fragment.

DEFINE SYSTEM Axiom AS com.archon
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
DESCRIPTION Ensures no domain in the UI service stores tokens in localStorage or sessionStorage.
PROMPT Based on this pseudo-code, write a bash script suitable for use in a GitHub Actions step that scans all TypeScript and TSX files under axiom-ui/src/ for calls to localStorage.setItem or sessionStorage.setItem. Exit with code 1 if any match is found.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE UI Service AS axiom-ui/src
    DEFINE DOMAIN Views AS axiom-ui/src/views
    DEFINE DOMAIN Components AS axiom-ui/src/components
    DEFINE DOMAIN Hooks AS axiom-ui/src/hooks
    DEFINE DOMAIN API Client AS axiom-ui/src/api
    DEFINE DOMAIN Store AS axiom-ui/src/store
    DEFINE DOMAIN Types AS axiom-ui/src/types
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

DEFINE SYSTEM Axiom AS com.archon
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
PROMPT Based on this pseudo-code, write an ArchUnit test in Java that verifies no class under com.archon.api depends on the io.qdrant package. Use JUnit 5 and ArchUnit 1.x. The test class should be named QdrantAccessProhibitionArchitectureTest.

DEFINE SYSTEM Axiom AS com.archon
  DEFINE SERVICE API Gateway Service AS com.archon.api
  DEFINE LIBRARY Qdrant Java Client AS io.qdrant

ASSERT(API Gateway Service has NO DEPENDENCY ON Qdrant Java Client)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-026: CROSS-SERVICE — TACTIC ENTITY DOMAIN ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Ensures the ArchitectureTactic entity lives exclusively in archon-api.
The Python agent must never import or reference the Java entity directly.
PROMPT Based on this pseudo-code, write a bash fitness function that:
1. Verifies no Python file under archon-agent/ contains the string "ArchitectureTactic" as a type reference.
2. Verifies no Python file under archon-agent/ imports from any Java package.
Emit a PASS or FAIL result with file and line details on failure.

DEFINE SYSTEM Axiom
  DEFINE SERVICE API Gateway Service AS archon-api
  DEFINE SERVICE Agent Orchestration Service AS archon-agent
  DEFINE COMPONENT Tactic Entity AS com.archon.api.domain.model.ArchitectureTactic

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
1. Scans all Java files under archon-api/src/ for calls to TacticRepository.save or TacticRepository.saveAll.
2. Flags any caller that is NOT TacticsService.
3. Scans all Java files for calls to tacticsService.saveTactics and flags any caller that is NOT ChatService.
Emit PASS if no violations are found, FAIL with file and line details otherwise.

DEFINE SYSTEM Axiom
  DEFINE SERVICE API Gateway Service AS com.archon.api
  DEFINE COMPONENT ChatService AS com.archon.api.service.ChatService
  DEFINE COMPONENT TacticsService AS com.archon.api.service.TacticsService
  DEFINE COMPONENT TacticRepository AS com.archon.api.domain.repository.TacticRepository

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

DEFINE SYSTEM Axiom
  DEFINE SERVICE Agent Orchestration Service AS archon-agent
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
       (1) helm/axiom/templates/ingress.yaml contains the string 'ssl-redirect'
           as evidence the HTTP to HTTPS redirect annotation is configured.
       (2) helm/axiom/values.yaml contains 'letsencrypt' as evidence a real CA
           issuer is configured rather than a self-signed certificate.
       (3) helm/axiom/templates/ingress.yaml contains a tls: block.
       Exit with code 1 if any check fails.
       Rule id: axiom-https-enforcement.

DEFINE SYSTEM Axiom AS helm/axiom
DEFINE CONST TLS_ANNOTATION    AS "ssl-redirect"
DEFINE CONST ISSUER_REFERENCE  AS "letsencrypt"
DEFINE CONST TLS_BLOCK         AS "tls:"
DEFINE COMPONENT IngressTemplate AS helm/axiom/templates/ingress.yaml
DEFINE COMPONENT IngressValues   AS helm/axiom/values.yaml

ASSERT(IngressTemplate CONTAINS TLS_ANNOTATION)
ASSERT(IngressValues   CONTAINS ISSUER_REFERENCE)
ASSERT(IngressTemplate CONTAINS TLS_BLOCK)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-034: AGENT ORCHESTRATION — STRUCTURED OUTPUT SCHEMA ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures every tool that calls llm_client.complete() with response_format="json"
             also passes output_schema and schema_name sourced from app.llm.schemas.SCHEMAS.
             Inline schema definitions inside tool classes are prohibited.
PROMPT Based on this pseudo-code, write a pytest test that imports every module from app.tools,
       inspects the source code of each tool's run() method, and verifies:
       (1) Every call to self.llm_client.complete() that includes response_format="json" also
           includes output_schema=SCHEMAS.get(...) and schema_name= arguments.
       (2) No tool module defines a dict or class with a "properties" key outside of
           app/llm/schemas.py (i.e. no inline JSON schema definitions).
       Test function name: test_all_tools_pass_output_schema.

DEFINE SYSTEM Axiom
  DEFINE SERVICE Agent Orchestration Service AS app
  DEFINE COMPONENT SchemaRegistry AS app.llm.schemas.SCHEMAS
  DEFINE \$TOOLS AS {app.tools.requirement_parser, app.tools.challenge_engine,
                    app.tools.scenario_modeler, app.tools.characteristic_reasoner,
                    app.tools.conflict_analyzer, app.tools.tactics_advisor,
                    app.tools.architecture_generator, app.tools.buy_vs_build_analyzer,
                    app.tools.diagram_generator, app.tools.trade_off_engine,
                    app.tools.adl_generator, app.tools.weakness_analyzer,
                    app.tools.fmea_analyzer}

FOREACH \$T IN \$TOOLS DO
  ASSERT(\$T DEPENDS ON SchemaRegistry)
  ASSERT(\$T has NO inline schema definitions)
END
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-035: AGENT ORCHESTRATION — SINGLE REPAIR ATTEMPT PER STAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures each tool is allowed exactly one call to attempt_repair() per run()
             invocation. A second repair attempt would mask persistent model failures
             and increase latency without improving output quality.
PROMPT Based on this pseudo-code, write a pytest test that for each tool in app.tools:
       (1) Mocks llm_client.complete() to raise json.JSONDecodeError on the first call
           and return valid JSON on the second call.
       (2) Verifies attempt_repair() is called exactly once.
       (3) Repeats with attempt_repair() also failing — verifies ToolExecutionException
           is raised without a second call to attempt_repair().
       Test function name: test_single_repair_attempt_per_stage.

DEFINE SYSTEM Axiom
  DEFINE SERVICE Agent Orchestration Service AS app
  DEFINE COMPONENT BaseTool AS app.tools.base.BaseTool
  DEFINE CONST MAX_REPAIR_ATTEMPTS AS 1

ASSERT(BaseTool.attempt_repair CALLED AT MOST MAX_REPAIR_ATTEMPTS PER run())
ASSERT(BaseTool.attempt_repair RAISES ToolExecutionException ON LLMCallException)
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADL-036: AGENT ORCHESTRATION — SUPPORTING STAGE RESILIENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via pytest
DESCRIPTION Ensures supporting stage failures record a gap in context.pipeline_gaps and
             allow the pipeline to continue, while core stage failures abort immediately
             with an ERROR event. CORE_STAGES = {requirement_parsing, requirement_challenge,
             characteristic_inference, architecture_generation}.
PROMPT Based on this pseudo-code, write a pytest test that:
       (1) Mocks a supporting stage node to raise ToolExecutionException.
       (2) Runs run_pipeline() and collects all yielded NDJSON chunks.
       (3) Asserts STAGE_COMPLETE with status="completed_with_gaps" is emitted.
       (4) Asserts subsequent stages still emit STAGE_COMPLETE (pipeline continued).
       (5) Asserts COMPLETE payload contains has_gaps=true and a non-empty pipeline_gaps.
       (6) Repeats with a core stage raising ToolExecutionException.
       (7) Asserts ERROR is emitted and no further STAGE_COMPLETE events follow.
       Test function name: test_supporting_stage_resilience.

DEFINE SYSTEM Axiom
  DEFINE SERVICE Agent Orchestration Service AS app
  DEFINE COMPONENT Graph AS app.pipeline.graph
  DEFINE CONST CORE_STAGES AS {requirement_parsing, requirement_challenge,
                                characteristic_inference, architecture_generation}
  DEFINE CONST SUPPORTING_STAGES AS ORDERED_STAGES - CORE_STAGES

ASSERT(SUPPORTING_STAGES failure EMITS "STAGE_COMPLETE" WITH status="completed_with_gaps")
ASSERT(SUPPORTING_STAGES failure ALLOWS pipeline continuation)
ASSERT(CORE_STAGES failure EMITS "ERROR" AND HALTS pipeline)
ASSERT(COMPLETE payload CONTAINS has_gaps AND pipeline_gaps)
```

---

ADL-037: WORKSHOP MODULE ISOLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES pytest test_workshop_isolation.py + fitness/adl-037-workshop-isolation.sh
DESCRIPTION Ensures that app.workshop does not import from app.pipeline or app.tools.
             The Quality Attribute Workshop is a pre-architecture elicitation module.
             It must be independently testable, deployable, and auditable without any
             dependency on the pipeline orchestration or tool registry.
ENFORCEMENT Automated: pytest parametrised AST import scanner (tests/unit/workshop/test_workshop_isolation.py)
             Automated: bash grep scanner (fitness/adl-037-workshop-isolation.sh)

DEFINE SYSTEM Axiom
  DEFINE MODULE Workshop AS app.workshop
  DEFINE MODULE Pipeline AS app.pipeline
  DEFINE MODULE Tools AS app.tools

ASSERT(Workshop MUST NOT IMPORT Pipeline)
ASSERT(Workshop MUST NOT IMPORT Tools)
ASSERT(Workshop MAY IMPORT app.llm.client)
ASSERT(Workshop MAY IMPORT app.llm.schemas)
ASSERT(Workshop MAY IMPORT app.prompts)

---

ADL-038: WORKSHOP GAP-BEFORE-ELICIT ORDERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES fitness/adl-038-gap-before-elicit.sh
DESCRIPTION Ensures that in the LangGraph graph built by QualityAttributeWorkshopAgent,
             the identify_gaps node is always wired BEFORE elicit_scenarios.
             This encodes the "ask before you assert" invariant at the graph-construction
             level: information gaps must be identified before operational scenarios are
             elicited as primary artifacts.
ENFORCEMENT Automated: bash line-number check (fitness/adl-038-gap-before-elicit.sh)

DEFINE SYSTEM Axiom
  DEFINE COMPONENT WorkshopAgent AS app.workshop.agent.QualityAttributeWorkshopAgent
  DEFINE GRAPH WorkshopGraph AS WorkshopAgent._build_graph()
  DEFINE NODE IdentifyGaps AS identify_gaps_node
  DEFINE NODE ElicitScenarios AS elicit_scenarios_node

ASSERT(WorkshopGraph EDGE IdentifyGaps → ElicitScenarios EXISTS)
ASSERT(WorkshopGraph EDGE IdentifyGaps PRECEDES EDGE ElicitScenarios → ANY)

---

ADL-041: SCENARIO-FIRST GRAPH ORDERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES pytest tests/unit/workshop/test_adl_workshop_order.py::test_scenario_before_attributes
DESCRIPTION elicit_scenarios_node MUST appear before infer_attributes_from_scenarios_node
             in app/workshop/agent.py graph edge definitions (QAW scenario-primary flow).
ENFORCEMENT Automated: pytest inspects agent.py source order

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT WorkshopAgent AS app.workshop.agent
DEFINE CONST SCENARIO_NODE AS "elicit_scenarios"
DEFINE CONST ATTRIBUTE_NODE AS "infer_attributes_from_scenarios"

ASSERT(WorkshopAgent CONTAINS SCENARIO_NODE)
ASSERT(WorkshopAgent CONTAINS ATTRIBUTE_NODE)

---

ADL-042: SCENARIO COMPLETENESS ENFORCED BY COMPUTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES pytest tests/unit/workshop/test_adl_scenario_completeness.py::test_empty_scenario_not_complete
DESCRIPTION QAScenario.compute_completeness MUST override LLM-provided completeness labels
             so empty scenarios cannot be marked complete after model initialisation.
ENFORCEMENT Automated: pytest on WorkshopContext model

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT QAScenario AS app.workshop.context.QAScenario

ASSERT(QAScenario CONTAINS compute_completeness)

---

ADL-043: ANSWER-ARTIFACT BINDING NODE IN GRAPH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES pytest tests/unit/workshop/test_resolver_wired_in_graph.py::test_resolver_wired_in_graph
        fitness/adl-043-resolver-order.sh
DESCRIPTION Assert resolve_questions node appears in the workshop graph and is wired between
             reconcile_gaps and elicit_scenarios (answer-to-artifact binding).
ENFORCEMENT Automated: pytest inspects agent.py source; bash checks edge strings.

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT WorkshopAgent AS app.workshop.agent
DEFINE CONST RESOLVE_NODE AS "resolve_questions"

ASSERT(WorkshopAgent CONTAINS RESOLVE_NODE)

---

ADL-044: SCENARIO EXTRACTION USES FULL EVIDENCE HISTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES fitness/adl-044-scenario-full-evidence.sh
DESCRIPTION Assert that elicit_scenarios prompt template receives all_evidence so scenario
             extraction searches the full conversation history, not only the latest turn.
ENFORCEMENT Automated: bash script greps app/prompts/workshop/elicit_scenarios.j2 for all_evidence.

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT ScenarioPrompt AS app/prompts/workshop/elicit_scenarios.j2
DEFINE CONST FULL_EVIDENCE_VAR AS "all_evidence"

ASSERT(ScenarioPrompt CONTAINS FULL_EVIDENCE_VAR)

---

ADL-039: WORKSHOP ATTRIBUTE CAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES pytest tests/unit/workshop/test_consolidation.py::test_max_attributes_constant_is_12
         pytest tests/unit/workshop/test_consolidation.py::test_cap_enforced_at_max_attributes
DESCRIPTION ConsolidationEngine enforces a hard cap of MAX_ATTRIBUTES = 12 on the
             quality attribute list. This prevents context explosion and ensures each
             attribute has enough token budget for grounded scenario generation.
             Attributes trimmed by the cap are chosen by lowest importance first.
ENFORCEMENT Automated: pytest assertion on MAX_ATTRIBUTES constant and cap behaviour

DEFINE CONSTANT MaxAttributes AS consolidator.MAX_ATTRIBUTES

ASSERT(MaxAttributes == 12)
ASSERT(ConsolidationEngine.consolidate RUNS AFTER infer_attributes_from_scenarios WHEN COUNT ≥ MIN)
ASSERT(ConsolidationEngine.consolidate RUNS AFTER generate_from_current_evidence)
ASSERT(len(WorkshopContext.attributes) <= MaxAttributes) AFTER EVERY CONSOLIDATION

---

ADL-040: NON-QA CONCERN SEPARATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES pytest tests/unit/workshop/test_consolidation.py::test_non_qa_separated
         pytest tests/unit/workshop/test_taxonomy.py
DESCRIPTION ConsolidationEngine._separate_non_qa must run on every consolidation pass,
             moving non-QA concerns (regulatory constraints, organisational concerns,
             delivery pressure) from WorkshopContext.attributes to
             WorkshopContext.non_qa_concerns.
             Non-QA concerns are tracked for the record but must not appear in the
             attribute list used for scenario generation or pipeline submission.
ENFORCEMENT Automated: pytest checks that 'gdpr' is not in attributes after consolidation

DEFINE SET NonQaConcepts AS taxonomy.NON_QA_CONCEPTS
DEFINE LIST QaAttributes AS WorkshopContext.attributes
DEFINE LIST NonQaList AS WorkshopContext.non_qa_concerns

ASSERT(NonQaConcepts INTERSECTION QaAttributes.names == EMPTY) AFTER EVERY CONSOLIDATION
ASSERT(ConsolidationEngine._separate_non_qa CALLED WITHIN consolidate())

---

ADL-059: PASSWORD RESET TOKEN STORAGE SECURITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES fitness/adl-059-password-reset-hash-only.sh
DESCRIPTION Assert that PasswordResetService never persists the raw password reset token.
            The service must store only passwordEncoder.encode(rawToken) in
            PasswordResetToken.tokenHash. The raw token may exist only in the reset email link.
ENFORCEMENT Automated: bash script greps PasswordResetService.java for raw-token persistence.

DEFINE SYSTEM Axiom AS com.archon.api
DEFINE COMPONENT PasswordResetService AS com.archon.api.service.PasswordResetService
DEFINE CONST TOKEN_STORAGE AS "bcrypt hash only"

ASSERT(PasswordResetService CONTAINS passwordEncoder.encode)

---

ADL-060: UTILITY TREE GENERATION THRESHOLD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES (no fitness script — enforced by unit test test_utility_tree.py)
DESCRIPTION The utility tree generator must check has_sufficient_for_utility_tree
            before invoking the LLM. The threshold is:
              - at least 5 scenarios with completeness in (complete, partial, needs_measure)
              - across at least 3 distinct exercises_attributes values
            Aspirational scenarios do not count toward either threshold.
            When the threshold is not met the generator returns None without calling the LLM.
            When the LLM call fails the generator returns the existing utility_tree unchanged.
ENFORCEMENT Unit test: TestHasSufficientForUtilityTree.test_true_at_threshold
            Unit test: TestUtilityTreeGenerator.test_generate_returns_none_when_threshold_not_met
            Unit test: TestUtilityTreeGenerator.test_generate_returns_existing_tree_on_llm_failure

DEFINE SYSTEM Axiom AS archon-agent
DEFINE COMPONENT UtilityTreeGenerator AS app.workshop.utility_tree_generator.UtilityTreeGenerator
DEFINE CONST SCENARIO_THRESHOLD AS 5
DEFINE CONST ATTRIBUTE_THRESHOLD AS 3
DEFINE CONST ELIGIBLE_COMPLETENESS AS ("complete", "partial", "needs_measure")

ASSERT(UtilityTreeGenerator.generate CHECKS context.has_sufficient_for_utility_tree BEFORE llm.complete)
ASSERT(UtilityTreeGenerator.generate RETURNS None WHEN has_sufficient_for_utility_tree IS False)
ASSERT(UtilityTreeGenerator.generate RETURNS existing_tree ON llm_failure)

---

ADL-061: ARCHITECTURAL IMPLICATION FORMAT AND TRACEABILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES (no fitness script — enforced by unit test test_implication_synthesis.py)
DESCRIPTION Architectural implications are synthesised from driver scenarios listed in the
            utility tree. Every implication must:
              - trace to a specific source_scenario_id
              - describe affected_quality_attrs rather than components or technologies
              - include tradeoff and measurable_condition fields
              - be capped at MAX_IMPLICATIONS = 20 per synthesis call
            Synthesis is skipped when utility_tree is None.
            On LLM failure the synthesiser returns the existing architecture_implications list.
ENFORCEMENT Unit test: TestSynthesiseReturnsEmptyWhenNoTree.test_synthesise_returns_empty_when_no_tree
            Unit test: TestImplicationMaxGuard.test_max_implications_guard
            Unit test: TestSynthesiseExtractsDriverScenarios.test_synthesise_returns_existing_on_llm_failure

DEFINE SYSTEM Axiom AS archon-agent
DEFINE COMPONENT ImplicationSynthesiser AS app.workshop.implication_synthesiser.ImplicationSynthesiser
DEFINE CONST MAX_IMPLICATIONS AS 20

ASSERT(ImplicationSynthesiser.synthesise RETURNS empty_list WHEN context.utility_tree IS None)
ASSERT(ImplicationSynthesiser.synthesise RETURNS at_most MAX_IMPLICATIONS items)
ASSERT(ImplicationSynthesiser.synthesise RETURNS existing_implications ON llm_failure)
ASSERT(ArchitectureImplication.affected_quality_attrs CONTAINS quality_attribute_names)
ASSERT(ArchitectureImplication.tradeoff IS NOT empty)
ASSERT(ArchitectureImplication.measurable_condition IS NOT empty)

---

ADL-062: IMPLICATION MECHANISM PROHIBITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Assert that the implication synthesis prompt explicitly lists
            mechanism terms as prohibited and that the synthesiser validates
            against them.
PROMPT "Write a bash script that checks:
        (1) app/prompts/workshop/synthesise_implications.j2
        contains 'consensus protocol' in a PROHIBITED or
        WRONG section demonstrating it is prohibited.
        (2) app/workshop/implication_synthesiser.py contains
        PROHIBITED_MECHANISM_TERMS as a module constant.
        Exit 1 if either check fails.
        Rule: axiom-no-mechanism-implications."

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT ImplicationPrompt
  AS app/prompts/workshop/synthesise_implications.j2
DEFINE COMPONENT ImplicationSynthesiser
  AS app.workshop.implication_synthesiser
DEFINE CONST PROHIBITED AS "PROHIBITED_MECHANISM_TERMS"

ASSERT(ImplicationSynthesiser CONTAINS PROHIBITED)
ASSERT(ImplicationPrompt CONTAINS "consensus protocol")

---

ADL-063: SEND-TO-PIPELINE INCLUDES ALL ATTRIBUTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Assert that formatWorkshopOutputAsRequirements accepts all
            quality attributes from the summary and that no filtering step
            removes attributes before formatting.
PROMPT "Write an ArchUnit test in Java that verifies
        WorkshopController.formatWorkshopOutputAsRequirements
        iterates over summary.qualityAttributes() without
        filtering by confidence level before the iteration.
        This ensures all attributes reach the pipeline.
        Test: test_all_attributes_forwarded_to_pipeline."

DEFINE SYSTEM Axiom AS com.archon.api
DEFINE COMPONENT WorkshopController
  AS com.archon.api.workshop.controller.WorkshopController

ASSERT(WorkshopController CONTAINS formatWorkshopOutputAsRequirements)

---

ADL-064: IDEMPOTENCY KEY ON PIPELINE SUBMISSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Assert that the send-to-pipeline API function in the UI includes
            an Idempotency-Key header and that WorkshopController reads it.
PROMPT "Write a bash script that checks:
        (1) the workshop API TypeScript file contains
        'Idempotency-Key' as a request header.
        (2) WorkshopController.java contains
        'Idempotency-Key' as a request header read.
        Exit 1 if either check fails.
        Rule: axiom-workshop-idempotency-key."

DEFINE SYSTEM Axiom AS com.archon.api
DEFINE COMPONENT WorkshopController
  AS com.archon.api.workshop.controller.WorkshopController
DEFINE CONST IDEMPOTENCY_HEADER AS "Idempotency-Key"

ASSERT(WorkshopController CONTAINS IDEMPOTENCY_HEADER)

---

ADL-065: SCENARIO DEDUPLICATION BEFORE PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Assert that deduplicated_scenarios property exists on
            WorkshopContext and that scenario-consuming synthesis uses it
            rather than the raw scenarios list.
PROMPT "Write a pytest test that creates a WorkshopContext
        with two scenarios sharing the same stimulus and
        artifact text and verifies deduplicated_scenarios
        returns only one of them. Test:
        test_deduplicated_scenarios_removes_duplicates."

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT WorkshopContext AS app.workshop.context
DEFINE CONST DEDUP_PROPERTY AS "deduplicated_scenarios"

ASSERT(WorkshopContext CONTAINS DEDUP_PROPERTY)

---

ADL-066: CANONICAL DECISION PROPAGATION TO ARCHITECTURE GENERATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Assert that ArchitectureGeneratorTool.run() passes
            canonical_decisions to the prompt and that the
            canonical_decisions property exists on ArchitectureContext.
PROMPT "Write a pytest test that creates an ArchitectureContext
        with buy_vs_build_analysis containing a BUY decision,
        verifies canonical_decisions returns a non-empty list,
        and verifies each entry has a 'constraint' field.
        Test: test_canonical_decisions_from_buy_decisions."

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT ArchitectureContext AS app.models.context
DEFINE CONST CANONICAL_DECISIONS AS "canonical_decisions"

ASSERT(ArchitectureContext CONTAINS CANONICAL_DECISIONS)

---

ADL-067: INTERACTION PROTOCOL NEVER UNDEFINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Assert that _validate_interactions rejects interactions
            with undefined protocol.
PROMPT "Write a bash script that checks
        app/tools/architecture_generator.py contains
        '_validate_interactions' as a method and that it
        contains the string 'undefined' in a check context
        (not as a value being set). Exit 1 if the method
        is absent. Rule: axiom-interaction-contracts."

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT ArchitectureGenerator
  AS app.tools.architecture_generator
DEFINE CONST VALIDATE_INTERACTIONS AS "_validate_interactions"

ASSERT(ArchitectureGenerator CONTAINS VALIDATE_INTERACTIONS)

---

ADL-068: GOVERNANCE SCORE GROUNDED IN ARTIFACT COUNTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Assert that the governance scoring prompt contains
            artifact-count instructions for each dimension and that
            the output schema includes score_evidence.
PROMPT "Write a bash script that checks
        app/prompts/review_governance_score.j2 contains
        the string 'score_evidence' in the return format
        and the string 'Count' or 'count' in the scoring
        instructions. Exit 1 if either is missing.
        Rule: axiom-governance-score-grounded."

DEFINE SYSTEM Axiom AS app
DEFINE COMPONENT GovernanceScorePrompt
  AS app/prompts/review_governance_score.j2

ASSERT(GovernanceScorePrompt CONTAINS "score_evidence")

---

ADL-069: LLM PROVIDER ABSTRACTION — NO DIRECT API CALLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Assert that no module outside app.llm imports from openai or
            makes direct HTTP calls to the Ollama API.
PROMPT "Write a PyTestArch test verifying that no module in app.tools or
        app.workshop imports from 'openai' or 'httpx' directly. All LLM calls
        must go through app.llm.client. Tests: test_tools_no_openai_import and
        test_workshop_no_direct_llm_calls."

DEFINE SYSTEM Axiom AS app
DEFINE DOMAIN Tools AS app.tools
DEFINE DOMAIN Workshop AS app.workshop
DEFINE COMPONENT LLMClient AS app.llm.client

ASSERT(Tools has NO DEPENDENCY ON openai)
ASSERT(Workshop has NO DEPENDENCY ON httpx)

---

ADL-070: STAGE_NAME REQUIRED ON ALL LLMCLIENT CALLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom fitness function via grep
DESCRIPTION Assert that every call to llm_client.complete() in the codebase
            passes a stage_name argument.
PROMPT "Write a bash script that searches app/tools/ and app/workshop/ for
        calls to llm_client.complete( and verifies each call includes
        'stage_name=' as a keyword argument. Exit 1 with the file and line if
        any call is missing stage_name. Rule:
        axiom-llm-stage-name-required."

DEFINE SYSTEM Axiom AS app
DEFINE CONST STAGE_NAME_PARAM AS "stage_name="

ASSERT(LLMClient CONTAINS STAGE_NAME_PARAM)

---

ADL-071: AXIOM-API IS THE SOLE JWT VALIDATION POINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES ArchUnit Java library
DESCRIPTION Assert that archon-api does not contain JWT validation
            logic when AXIOM_GATEWAY_BYPASS is false. JWT validation
            belongs exclusively in axiom-api. archon-api trusts the
            X-Axiom-User-Id header forwarded by the gateway.
PROMPT "Write an ArchUnit test verifying that when
        axiom.gateway.bypass property is false, no class in
        com.archon.api reads the Authorization header or imports
        io.jsonwebtoken except within classes annotated with
        @ConditionalOnProperty(name='axiom.gateway.bypass',
        havingValue='true'). Test class: GatewayAuthBoundaryTest."

DEFINE SYSTEM Axiom AS com.axiom
DEFINE COMPONENT ArchonApi AS com.archon.api
DEFINE LIBRARY JJWT AS io.jsonwebtoken
DEFINE CONST BypassOnly AS classes annotated with bypass condition

ASSERT(ArchonApi JWT_VALIDATION only IN BypassOnly)

---

ADL-072: PILLARS MUST NOT IMPORT FROM EACH OTHER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES PyTestArch Python library
DESCRIPTION Assert that no pillar agent imports from another pillar's
            module. Cross-pillar communication is HTTP only.
            Shared utilities may live in a common module but
            business logic must not cross pillar boundaries.
PROMPT "Write a PyTestArch test verifying that app.archon has
        no imports from app.specweaver, app.scout, or app.forge.
        Repeat for each pillar. Test file:
        tests/architecture/test_pillar_isolation.py"

DEFINE SYSTEM Axiom AS app
DEFINE PILLAR Archon AS app.archon
DEFINE PILLAR SpecWeaver AS app.specweaver
DEFINE PILLAR Scout AS app.scout
DEFINE PILLAR Forge AS app.forge

ASSERT(Archon has NO DEPENDENCY ON SpecWeaver)
ASSERT(Archon has NO DEPENDENCY ON Scout)
ASSERT(Archon has NO DEPENDENCY ON Forge)
ASSERT(SpecWeaver has NO DEPENDENCY ON Archon)
ASSERT(SpecWeaver has NO DEPENDENCY ON Scout)
ASSERT(SpecWeaver has NO DEPENDENCY ON Forge)

---

ADL-073: MAXIMUM TWO SERVICES PER PILLAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRES Custom bash fitness function
DESCRIPTION Each pillar directory must contain at most two service
            subdirectories: one *-api and one *-agent.
            This enforces the two-service-per-pillar platform rule
            and prevents scope creep through service proliferation.
PROMPT "Write a bash script that checks each pillar directory
        (archon, specweaver, scout, forge) contains at most two
        subdirectories matching the patterns *-api and *-agent.
        Exit 1 if any pillar has more than two service directories.
        Add this script to .github/workflows/ci.yml as a step
        named 'Check pillar service count'. Rule name:
        axiom-two-service-limit."

DEFINE SYSTEM Axiom AS platform root directory
DEFINE CONST MaxServicesPerPillar AS 2
DEFINE PILLAR Archon AS ./archon/
DEFINE PILLAR SpecWeaver AS ./specweaver/
DEFINE PILLAR Scout AS ./scout/
DEFINE PILLAR Forge AS ./forge/

ASSERT(EACH PILLAR CONTAINS AT MOST MaxServicesPerPillar services)

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
| ADL-059  | Hard        | Persisting raw password reset tokens would turn a database leak into account takeover. Only bcrypt hashes may ever be stored. |
| ADL-033  | Hard        | Serving the application over HTTP exposes user sessions, JWT tokens, and architecture data in plaintext. The ssl-redirect annotation and a valid CA issuer (letsencrypt-staging or letsencrypt-prod) are both required. CI must fail if either is removed. Self-signed certificates are not acceptable; they produce the same browser warning as HTTP-only deployment. |
| ADL-034  | Hard        | Every tool that calls llm_client.complete() with JSON output must pass output_schema and schema_name sourced from app.llm.schemas.SCHEMAS. Inline schema definitions are prohibited. A missing schema falls silently back to unstructured JSON, defeating the contract and allowing malformed payloads to propagate through the pipeline. |
| ADL-035  | Hard        | Each tool is allowed exactly one repair attempt per run() invocation. A second repair would mask persistent model failures and increase latency without improving quality. The repair must pass the same output_schema so the provider can still enforce structure. |
| ADL-036  | Hard        | Supporting stage failures must not abort the pipeline. Recording the gap in context.pipeline_gaps and continuing allows users to receive a partial architecture rather than a blank result. CORE_STAGES failures must still hard-abort because their outputs are prerequisites for all downstream stages. |
| ADL-037  | Hard        | The workshop module must not import from app.pipeline or app.tools. Importing from the pipeline would couple an elicitation tool to orchestration logic, making the workshop impossible to test in isolation and introducing a dependency inversion. Any pipeline tool import would drag in LLM schemas, tool registry, and RAG infrastructure that the workshop does not need. |
| ADL-038  | Hard        | The identify_gaps node must always precede the elicit_attributes node in the workshop LangGraph. If attributes were elicited before gaps were identified, the agent would assert quality properties without gathering sufficient evidence — violating the "ask before you assert" principle that is the methodological foundation of the SEI QAW approach. |
| ADL-039  | Hard        | MAX_ATTRIBUTES must equal 12. ConsolidationEngine must enforce this cap after every elicitation and every generation. Exceeding this cap allows context explosion and dilutes the quality of each attribute's scenario grounding. Attributes trimmed by the cap are chosen by lowest importance first. |
| ADL-040  | Hard        | ConsolidationEngine._separate_non_qa must run on every consolidation pass. Non-QA concerns (regulatory, organisational, delivery) must be moved to WorkshopContext.non_qa_concerns and excluded from the attribute count. Mixing non-QA concerns with quality attributes inflates the apparent attribute count and confuses scenario generation. |
| ADL-060  | Hard        | UtilityTreeGenerator.generate() must check has_sufficient_for_utility_tree (≥5 eligible scenarios across ≥3 distinct attributes) before calling the LLM. Aspirational scenarios do not count. Generating a tree without sufficient evidence produces a low-signal tree that misleads the architect. |
| ADL-061  | Hard        | ImplicationSynthesiser must skip synthesis when utility_tree is None, must cap results at MAX_IMPLICATIONS=20, and must describe affected components using component types rather than technology names. Technology-named implications over-specify and constrain technology selection prematurely. |
| ADL-062  | Hard        | Workshop implications must never prescribe mechanisms. The prompt and validator both need an explicit prohibition list so bad requirements are visible and correctable before they enter architecture generation. |
| ADL-063  | Hard        | The pipeline formatter must forward all quality attributes. Filtering attributes at the workshop boundary hides architecturally relevant constraints and causes the reasoning engine to optimise against incomplete requirements. |
| ADL-064  | Hard        | Send-to-pipeline must be idempotent at the UI/API boundary. Missing idempotency keys allow duplicate architecture runs, inconsistent reports, and unnecessary LLM cost. |
| ADL-065  | Hard        | Duplicate scenarios must be collapsed before utility-tree generation and pipeline handoff. Repeated scenarios overweight one concern and distort downstream architectural reasoning. |
| ADL-066  | Hard        | Buy/adopt decisions are architecture decisions. If they are not propagated as canonical constraints, downstream artifacts contradict the sourcing decision and lose traceability. |
| ADL-067  | Hard        | Undefined interaction protocol or purpose fields produce broken diagrams and unusable interoperability analysis. Invalid interactions must be rejected before storage. |
| ADL-068  | Hard        | Governance scoring must be grounded in artifact counts and expose evidence strings. Static scores across different systems are a scoring engine failure. |
| ADL-069  | Hard        | Direct provider imports outside app.llm would bypass the provider switch and scatter LLM credentials across modules. |
| ADL-070  | Hard        | Stage names drive Ollama model-tier selection and latency budgeting; missing names silently route calls to the wrong model. |
| ADL-071  | Hard        | JWT validation must live exclusively in axiom-api when gateway bypass is disabled. Duplicating JWT parsing in archon-api would split authentication policy and make header trust ambiguous. |
| ADL-072  | Hard        | Pillars are independently bounded architecture domains. Direct imports would bypass the HTTP-only platform contract and create hidden coupling between roadmap phases. |
| ADL-073  | Hard        | The platform rule allows one API service and one agent service per pillar. Extra services expand operational scope and violate the intended deployment model. |
