# Workflows & Data Flow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACES                                │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │   API    │    │   CLI    │    │   Web    │                  │
│  │ FastAPI  │    │  Typer   │    │  React   │                  │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘                  │
└───────┼───────────────┼───────────────┼────────────────────────┘
        │               │               │
        └───────────────┴───────────────┘
                        │
┌───────────────────────┼────────────────────────────────────────┐
│                    DOMAINS                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Extraction  │  │   Search    │  │  Diagnosis  │            │
│  │             │  │             │  │             │            │
│  │ PDF→JSON    │  │ Hybrid RAG  │  │ Expert Agents│           │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         │                │                │                    │
│  ┌──────┴────────────────┴────────────────┴──────┐            │
│  │              Orchestration                     │            │
│  │  Router → Cache → Pipeline                     │            │
│  └──────────────────┬────────────────────────────┘            │
│                     │                                          │
│  ┌──────────────────┴────────────────────────────┐            │
│  │              Knowledge                         │            │
│  │  GraphStore → Reasoner                         │            │
│  └────────────────────────────────────────────────┘            │
└───────────────────────┬────────────────────────────────────────┘
                        │
┌───────────────────────┼────────────────────────────────────────┐
│                    ADAPTERS                                     │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  │
│  │ Gemini │  │ SQLite │  │ FAISS  │  │ Neo4j  │  │ Ollama │  │
│  │  API   │  │  FTS5  │  │ Vector │  │ Graph  │  │ Local  │  │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflow 1: PDF Extraction

```
User uploads PDF
        │
        ▼
┌───────────────────┐
│  API: POST        │
│  /extraction/     │
│  extract          │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  GeminiExtractor  │
│  .extract()       │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  GeminiClient     │
│  .upload_file()   │  ──► Gemini File API
│  .extract_pdf()   │  ──► Gemini Generate
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Parse JSON       │
│  response into:   │
│  - Components     │
│  - Connections    │
│  - Fault Codes    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Store in:        │
│  - SQLite (text)  │
│  - FAISS (vectors)│
│  - Neo4j (graph)  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Return           │
│  ExtractionResult │
└───────────────────┘
```

---

## Workflow 2: Hybrid Search (RAG)

```
User query: "KONE fault 505"
        │
        ▼
┌───────────────────┐
│  SmartRouter      │
│  .route()         │  ──► Classify query type
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Check Cache      │
│  ResponseCache    │  ──► Cache hit? Return cached
└─────────┬─────────┘
          │ cache miss
          ▼
┌───────────────────────────────────────┐
│         HybridSearchEngine            │
│                                       │
│  ┌─────────────┐   ┌─────────────┐   │
│  │   FAISS     │   │   SQLite    │   │
│  │   Vector    │   │   FTS5      │   │
│  │   Search    │   │   Search    │   │
│  └──────┬──────┘   └──────┬──────┘   │
│         │                 │          │
│         └────────┬────────┘          │
│                  │                   │
│         ┌────────▼────────┐          │
│         │  RRF Fusion     │          │
│         │  (Reciprocal    │          │
│         │   Rank Fusion)  │          │
│         └────────┬────────┘          │
└──────────────────┼───────────────────┘
                   │
                   ▼
┌───────────────────┐
│  If use_rag=true: │
│  GeminiClient     │
│  .generate()      │  ──► Generate answer from context
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Cache response   │
│  Return results   │
└───────────────────┘
```

---

## Workflow 3: Fault Diagnosis

```
Fault code: "F505"
        │
        ▼
┌───────────────────┐
│  SmartRouter      │
│  .route()         │  ──► type = FAULT_DIAGNOSIS
└─────────┬─────────┘
          │
          ▼
┌───────────────────────────────────────┐
│         QueryPipeline                  │
│         .execute_diagnosis()           │
│                                        │
│  ┌─────────────────────────────────┐  │
│  │     GraphReasoner               │  │
│  │     .find_causes()              │  │
│  │                                 │  │
│  │  Traverse CAUSED_BY edges       │  │
│  │  Build causal chain             │  │
│  └───────────────┬─────────────────┘  │
│                  │                     │
│  ┌───────────────▼─────────────────┐  │
│  │     FaultDiagnosisAgent         │  │
│  │     .diagnose()                 │  │
│  │                                 │  │
│  │  LLM prompt with:               │  │
│  │  - Fault code                   │  │
│  │  - Graph context                │  │
│  │  - Symptoms                     │  │
│  └───────────────┬─────────────────┘  │
└──────────────────┼─────────────────────┘
                   │
                   ▼
┌───────────────────┐
│  FaultDiagnosis   │
│  - causes         │
│  - remedies       │
│  - severity       │
│  - confidence     │
└───────────────────┘
```

---

## Workflow 4: Expert Consensus

```
Complex diagnosis request
        │
        ▼
┌───────────────────────────────────────┐
│         ExpertConsensus               │
│         .get_consensus()              │
│                                       │
│  ┌────────────────────────────────┐  │
│  │  Run in parallel:              │  │
│  │                                │  │
│  │  ┌──────────┐  ┌──────────┐   │  │
│  │  │ Expert 1 │  │ Expert 2 │   │  │
│  │  │ (Agent)  │  │ (Agent)  │   │  │
│  │  └────┬─────┘  └────┬─────┘   │  │
│  │       │             │         │  │
│  │       ▼             ▼         │  │
│  │  ┌──────────┐  ┌──────────┐   │  │
│  │  │ Opinion1 │  │ Opinion2 │   │  │
│  │  └────┬─────┘  └────┬─────┘   │  │
│  └───────┼─────────────┼─────────┘  │
│          │             │            │
│          └──────┬──────┘            │
│                 │                   │
│        ┌────────▼────────┐          │
│        │  Synthesize     │          │
│        │  - Merge causes │          │
│        │  - Find consensus│         │
│        │  - Note disagree│          │
│        └────────┬────────┘          │
└─────────────────┼───────────────────┘
                  │
                  ▼
┌───────────────────┐
│  ConsensusResult  │
│  - final_diagnosis│
│  - consensus_level│
│  - disagreements  │
└───────────────────┘
```

---

## Workflow 5: Knowledge Graph Building

```
ExtractionResult
        │
        ▼
┌───────────────────────────────────────┐
│     KnowledgeGraphStore               │
│     .build_from_extraction()          │
│                                       │
│  For each component:                  │
│  ┌────────────────────────────────┐  │
│  │  add_node(KnowledgeNode)       │  │
│  │  - type: COMPONENT             │  │
│  │  - properties: specs           │  │
│  └────────────────────────────────┘  │
│                                       │
│  For each connection:                 │
│  ┌────────────────────────────────┐  │
│  │  add_edge(KnowledgeEdge)       │  │
│  │  - type: CONNECTED_TO          │  │
│  │  - source → target             │  │
│  └────────────────────────────────┘  │
│                                       │
│  For each fault code:                 │
│  ┌────────────────────────────────┐  │
│  │  add_node(FAULT_CODE)          │  │
│  │  add_edge(CAUSED_BY)           │  │
│  │  - fault → component           │  │
│  └────────────────────────────────┘  │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────┐
│  Dual Storage:    │
│  - NetworkX (mem) │
│  - Neo4j (persist)│
└───────────────────┘
```

---

## Data Flow Summary

```
PDF Upload
    │
    ▼
Extraction ──────► Components, Connections, Faults
    │
    ├──► SQLite (text chunks, FTS5)
    ├──► FAISS (embeddings)
    └──► Neo4j (knowledge graph)
            │
            ▼
User Query ──────► Router ──────► Pipeline
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
               Search            Diagnosis       Knowledge
               (RAG)            (Expert)         (Graph)
                    │                │                │
                    └────────────────┼────────────────┘
                                     │
                                     ▼
                              Response + Sources
```
