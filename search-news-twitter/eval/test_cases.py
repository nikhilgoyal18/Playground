"""
Test cases for search-news-twitter evaluation harness.

Each test case defines:
- id: unique test identifier
- query: user input query
- expected_path: "internal" | "web_fallback" | "explicit_web"
- expected_sources: list of author/source substrings (case-insensitive) that should appear in metas
- min_judge_score: minimum judge score required if internal path is taken
- notes: context about why this test matters
"""

TEST_CASES = [
    # ============ Path 1: Internal Hits (queries about indexed content)
    {
        "id": "internal_db_optimization",
        "query": "database indexing and caching trade-offs",
        "expected_path": "internal",
        "expected_sources": ["ByteByteGo"],
        "min_judge_score": 5,
        "notes": "ByteByteGo 2026-04-02 covers DB optimization strategies, indexes slow writes, caching intro patterns",
    },
    {
        "id": "internal_rag_agents",
        "query": "agentic RAG systems and retrieval evaluation",
        "expected_path": "internal",
        "expected_sources": ["ByteByteGo"],
        "min_judge_score": 5,
        "notes": "ByteByteGo 2026-04-02 covers agentic RAG: multi-step retrieval, evaluation, quality checks",
    },
    {
        "id": "internal_api_security",
        "query": "API authentication and authorization best practices",
        "expected_path": "internal",
        "expected_sources": ["ByteByteGo"],
        "min_judge_score": 5,
        "notes": "ByteByteGo 2026-04-02 covers API security: layered pattern, authorization missing bugs",
    },
    {
        "id": "internal_event_sourcing",
        "query": "event sourcing architecture and audit trails",
        "expected_path": "internal",
        "expected_sources": ["ByteByteGo"],
        "min_judge_score": 5,
        "notes": "ByteByteGo 2026-04-02 covers event sourcing: immutable event log, replay, CQRS",
    },
    # ============ Path 2: Web Fallback (queries about out-of-corpus content)
    {
        "id": "web_fallback_photosynthesis",
        "query": "how photosynthesis works at the molecular level",
        "expected_path": "web_fallback",
        "expected_sources": [],  # No internal sources expected
        "min_judge_score": 0,
        "notes": "Biology topic not in indexed newsletters/tweets; should fallback to web",
    },
    {
        "id": "web_fallback_medieval_history",
        "query": "causes of the fall of the Roman Empire",
        "expected_path": "web_fallback",
        "expected_sources": [],
        "notes": "History topic not in AI/Tech digests; should fallback to web",
    },
    {
        "id": "web_fallback_cooking",
        "query": "how to make a perfect risotto from scratch",
        "expected_path": "web_fallback",
        "expected_sources": [],
        "notes": "Cooking topic not in indexed newsletters/tweets; should fallback to web",
    },
    # ============ Path 3: Explicit Web Detection (queries with time-sensitive keywords)
    {
        "id": "explicit_web_latest_ai_news",
        "query": "latest AI news and announcements today",
        "expected_path": "explicit_web",
        "expected_sources": [],
        "min_judge_score": 0,
        "notes": "Query contains 'latest' and 'today'; should skip internal and go straight to web",
    },
    {
        "id": "explicit_web_breaking_news",
        "query": "breaking technology news right now",
        "expected_path": "explicit_web",
        "expected_sources": [],
        "min_judge_score": 0,
        "notes": "Query contains 'breaking' and 'right now'; should trigger explicit web path",
    },
    # ============ Path 4: Complex Technical Query
    {
        "id": "netflix_technical",
        "query": "how Netflix streams to 100 million devices efficiently",
        "expected_path": "internal",  # Judge scores 8 with full chunk context
        "expected_sources": ["ByteByteGo"],
        "min_judge_score": 5,
        "notes": "Complex technical query; judge evaluates with chunk context preview",
    },
    {
        "id": "vague_system_query",
        "query": "stuff about systems",  # Slightly less vague
        "expected_path": "internal",  # System will find something relevant
        "expected_sources": [],
        "min_judge_score": 3,
        "notes": "Vague queries may match various chunks; system chooses best match",
    },
]
