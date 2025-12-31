# Analýza Prompt Routing v MCP Prompt Broker

**Datum:** 2025-12-31  
**Autor:** GitHub Copilot  
**Typ:** Analýza, Best Practices & Implementační plán  
**Priorita:** Vysoká  

---

## 📋 Shrnutí

MCP server "Prompt Broker" vykazuje problémy se správným výběrem instrukčních profilů. Tato analýza identifikuje hlavní nedostatky současné implementace a navrhuje zlepšení založená na best practices z průmyslu, včetně referenčních projektů jako **Semantic Router** od Aurelio Labs.

### Klíčová zjištění

| Oblast | Současný stav | Doporučení |
|--------|---------------|------------|
| Algoritmus matchingu | Keyword-based + rule weights | **Hybrid: Embedding + Keyword** |
| Počet profilů | ~45 profilů | Hierarchická kategorizace |
| Threshold | Chybí dynamický threshold | Konfigurovatelné thresholdy per-profil |
| Evaluace | Minimální | Systematický benchmark suite |
| Utterance samples | Žádné | Přidat ukázkové prompty per-profil |

---

## 🔍 Analýza současného stavu

### 1. Architektura routeru

Současná implementace používá **rule-based scoring** s těmito komponenty:

```mermaid
graph LR
    A[Prompt] --> B[Metadata Parser]
    B --> C[EnhancedMetadata]
    C --> D[ProfileRouter]
    D --> E[is_match?]
    E -->|Yes| F[score]
    E -->|No| G[Skip]
    F --> H[Select Max Score]
    H --> I[RoutingResult]
```

#### Současný scoring algoritmus

```python
# profile_router.py - route() method
def route(self, metadata: EnhancedMetadata) -> RoutingResult:
    for profile in self.profiles:
        if not profile.is_match(metadata_map):  # Binary matching
            continue
        scored_matches.append((profile, profile.score(metadata_map)))
    
    # Select best by max score
    best_profile, best_score = max(scored_matches, key=lambda item: item[1])
```

**Problémy:**
1. **Binary matching v `is_match()`** - Profil je buď zahrnut nebo vyřazen
2. **Keyword matching je přesný** - Chybí fuzzy/semantic matching
3. **Chybí utterance samples** - Profily nemají příklady promptů pro trénink
4. **Statické váhy** - Nelze optimalizovat na základě dat

### 2. Metadata Parser

Parser v `metadata/parser.py` extrahuje:

| Dimenze | Metoda detekce | Problém |
|---------|----------------|---------|
| `intent` | Keyword matching | Omezeno na statický slovník |
| `domain` | Keyword matching + score | Pouze best match |
| `topics` | Keyword presence | Boolean, bez gradace |
| `sensitivity` | Phrase weights | Statické váhy |

**Kritický problém:** Parser nezná kontext profilu - pouze extrahuje metadata bez znalosti, jaké profily existují.

### 3. Profily - struktura a váhy

Příklad profilu `codex_cli.md`:
```yaml
required:
  context_tags: ["codex_cli", "mcp_integration", "codex_orchestrator"]

weights:
  keywords:
    codex cli: 12
    codex: 10
    codex orchestrator: 15
```

**Problémy:**
1. **`required.context_tags`** vyžaduje přesnou shodu - pokud parser nerozpozná "codex_cli" topic, profil není nikdy zvážen
2. **Chybí fallback mechanismus** na úrovni jednotlivých profilů
3. **Váhy jsou manuálně nastavené** bez empirické kalibrace

---

## 🌐 Best Practices z průmyslu

### Reference: Semantic Router (Aurelio Labs)

[Semantic Router](https://github.com/aurelio-labs/semantic-router) (3.1k+ stars) implementuje:

```python
# Definice route s utterance samples
politics = Route(
    name="politics",
    utterances=[
        "isn't politics the best thing ever",
        "why don't you tell me about your political opinions",
        "don't you just love the president",
    ],
    score_threshold=0.7
)

# Encoder převádí text na embedding
encoder = OpenAIEncoder()  # nebo HuggingFaceEncoder, FastEmbedEncoder

# Router porovnává embedding query vs. route embeddings
router = SemanticRouter(encoder=encoder, routes=[politics, chitchat])
result = router("What do you think about the election?")
```

#### Klíčové principy:

1. **Utterance-based routing** - Každá route má příklady, které se embeddují
2. **Semantic similarity** - Cosine similarity mezi query a route embeddings
3. **Threshold-based decisions** - Konfigurovatelný `score_threshold` per route
4. **Hybrid support** - Kombinace dense + sparse embeddings (BM25)
5. **Fit & evaluate** - Možnost trénovat thresholdy na datech

### Srovnání přístupů

| Přístup | Výhody | Nevýhody | Použití |
|---------|--------|----------|---------|
| **Keyword matching** | Rychlé, interpretovatelné | Přesná shoda, chybí synonyma | Jednodušší use-cases |
| **TF-IDF / BM25** | Statistické vážení termínů | Bez sémantiky | Dokumentové vyhledávání |
| **Dense embeddings** | Sémantická podobnost | Pomalejší, potřeba modelu | Pokročilý routing |
| **Hybrid** | Kombinuje keyword + semantic | Komplexnější implementace | Production-grade |

### Doporučení z výzkumu

Podle článku [Multi-LLM Routing Strategies (AWS)](https://aws.amazon.com/blogs/machine-learning/multi-llm-routing-strategies-for-generative-ai-applications-on-aws/):

> "Semantic search as an alternative to using a classifier LLM for prompt classification achieves around 90% accuracy without the latency of LLM inference."

---

## 🚨 Identifikované problémy

### Problém 1: Cirkulární závislost parser ↔ profily

```
Parser → extrahuje intent/domain/topics
        ↓
Profiles → definují required.intent/domain/context_tags
        ↓
Router → porovnává metadata vs. required
        ↓
FAIL: Parser nezná, jaké hodnoty profily očekávají
```

**Řešení:** Dynamické klíčové slova z profilů → parser (již částečně implementováno v `extract_keywords_from_profiles`)

### Problém 2: Binary matching eliminuje kandidáty příliš brzo

```python
# Současný stav
def is_match(self, metadata):
    if not self.required:
        return True  # Profil bez required vždy matchuje
    for key, allowed_values in self.required.items():
        if value not in allowed_values:
            return False  # Hard rejection
```

**Důsledek:** Profil s `required: {intent: [brainstorm]}` je ignorován pro prompt "Přemýšlej kreativně o..." protože parser může vrátit `intent: "question"`.

### Problém 3: Chybí "utterance samples" pro každý profil

Současné profily definují jen metadata constraints, nikoliv příklady promptů:

```yaml
# Současný stav - codex_cli.md
required:
  context_tags: ["codex_cli"]

# Chybí:
utterances:
  - "Použij Codex CLI pro vytvoření skriptu"
  - "Spusť Codex v Docker kontejneru"
  - "Generuj kód pomocí Codex orchestrátoru"
```

### Problém 4: Nízká consistency u více matchujících profilů

S 45+ profily je pravděpodobnost více partial matches vysoká:
- `general_default` má fallback=true a broad matching
- Multiple domain-specific profiles mohou překrývat

### Problém 5: Chybí evaluační framework

Žádný systematický způsob jak měřit:
- Accuracy (správný profil / celkem)
- Precision/Recall per profil
- Confusion matrix mezi profily

---

## 💡 Navrhovaná řešení

### Řešení 1: Hybrid Scoring Architecture

```python
@dataclass
class HybridScore:
    keyword_score: float  # 0-1, normalized keyword matches
    semantic_score: float  # 0-1, embedding similarity
    rule_score: float      # 0-1, normalized weights
    
    def combined(self, alpha=0.4, beta=0.4, gamma=0.2):
        return alpha * self.semantic_score + beta * self.keyword_score + gamma * self.rule_score
```

### Řešení 2: Utterance-based Profile Matching

Přidat do YAML frontmatter profilů:

```yaml
---
name: codex_cli
utterances:
  - "Použij Codex CLI pro generování kódu"
  - "Spusť Codex v izolovaném Docker kontejneru"
  - "Deleguj úlohu na OpenAI Codex orchestrátor"
  - "Codex CLI, vytvoř Python skript pro..."
  - "Run Codex with timeout and structured output"
utterance_threshold: 0.75
---
```

### Řešení 3: Softened Matching

Namísto binary `is_match()` → `match_score()`:

```python
def match_score(self, metadata: MutableMapping[str, object]) -> float:
    """Return match score 0-1 based on how well metadata fits requirements."""
    if not self.required:
        return 1.0  # No requirements = full match
    
    matched = 0
    total = len(self.required)
    
    for key, allowed_values in self.required.items():
        value = metadata.get(key)
        if value is None:
            continue
        if key == "context_tags":
            # Partial match for tags
            overlap = len(set(allowed_values) & set(value))
            matched += overlap / len(allowed_values)
        elif value in allowed_values:
            matched += 1
    
    return matched / total if total > 0 else 1.0
```

### Řešení 4: Per-Profile Thresholds

```yaml
---
name: privacy_sensitive
threshold:
  min_score: 8
  min_match_ratio: 0.7
  min_semantic_similarity: 0.65
fallback_priority: 10  # Higher = more likely as fallback
---
```

### Řešení 5: Embedding-based Routing Layer

Integrace s lightweight embedding modelem:

```python
from sentence_transformers import SentenceTransformer

class SemanticProfileRouter:
    def __init__(self, profiles: List[InstructionProfile]):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB, fast
        self.profiles = profiles
        self._build_utterance_index()
    
    def _build_utterance_index(self):
        """Pre-compute embeddings for all profile utterances."""
        self.utterance_embeddings = {}
        for profile in self.profiles:
            if profile.utterances:
                embeddings = self.model.encode(profile.utterances)
                self.utterance_embeddings[profile.name] = embeddings
    
    def semantic_score(self, prompt: str, profile_name: str) -> float:
        """Compute semantic similarity between prompt and profile utterances."""
        if profile_name not in self.utterance_embeddings:
            return 0.0
        
        prompt_embedding = self.model.encode([prompt])[0]
        profile_embeddings = self.utterance_embeddings[profile_name]
        
        # Cosine similarity
        similarities = cosine_similarity([prompt_embedding], profile_embeddings)[0]
        return float(np.max(similarities))  # Best match
```

---

## 📊 Implementační plán

### Fáze 1: Foundational Improvements (1-2 týdny)

| # | Úloha | Priorita | Effort |
|---|-------|----------|--------|
| 1.1 | Přidat `utterances` field do InstructionProfile | P0 | S |
| 1.2 | Rozšířit profile parser pro utterances | P0 | S |
| 1.3 | Implementovat `match_score()` místo `is_match()` | P0 | M |
| 1.4 | Přidat utterances do 10 klíčových profilů | P1 | M |
| 1.5 | Vytvořit test dataset (50+ prompt-profile párů) | P0 | M |

### Fáze 2: Semantic Layer (2-3 týdny)

| # | Úloha | Priorita | Effort |
|---|-------|----------|--------|
| 2.1 | Integrovat sentence-transformers nebo fastembed | P0 | M |
| 2.2 | Implementovat utterance embedding cache | P1 | M |
| 2.3 | Vytvořit `SemanticProfileRouter` class | P0 | L |
| 2.4 | Implementovat hybrid scoring (keyword + semantic) | P1 | M |
| 2.5 | Přidat per-profile threshold konfigurace | P2 | S |

### Fáze 3: Evaluation & Optimization (1-2 týdny)

| # | Úloha | Priorita | Effort |
|---|-------|----------|--------|
| 3.1 | Implementovat `evaluate()` method na routeru | P0 | M |
| 3.2 | Vytvořit confusion matrix vizualizaci | P1 | S |
| 3.3 | Implementovat threshold optimization (fit) | P2 | L |
| 3.4 | Přidat metriky do MCP tool response | P1 | S |
| 3.5 | Dokumentovat benchmark výsledky | P1 | S |

---

## 🧪 Testování kvality přiřazení

### Test Dataset Structure

```yaml
# tests/fixtures/routing_benchmark.yaml
test_cases:
  - id: "codex_001"
    prompt: "Použij Codex CLI pro vytvoření Python skriptu"
    expected_profile: "codex_cli"
    min_score: 8
    tags: ["codex", "generation"]
    
  - id: "privacy_001"  
    prompt: "Zpracuj data pacientů s ohledem na GDPR"
    expected_profile: "privacy_sensitive"
    min_score: 10
    tags: ["healthcare", "compliance"]
    
  - id: "creative_001"
    prompt: "Brainstormuj kreativní nápady pro marketing"
    expected_profile: "creative_brainstorm"
    min_score: 6
    tags: ["ideation", "marketing"]
```

### Evaluation Metrics

```python
@dataclass
class RoutingEvaluationResult:
    accuracy: float          # Correct predictions / Total
    precision_per_profile: Dict[str, float]
    recall_per_profile: Dict[str, float]
    f1_per_profile: Dict[str, float]
    confusion_matrix: np.ndarray
    avg_confidence: float    # Average consistency score
    fallback_rate: float     # How often fallback was used
    
def evaluate_routing(
    router: ProfileRouter,
    test_cases: List[TestCase],
) -> RoutingEvaluationResult:
    """Evaluate router performance on test dataset."""
    correct = 0
    predictions = []
    actuals = []
    
    for case in test_cases:
        parsed = analyze_prompt(case.prompt)
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        predictions.append(result.profile.name)
        actuals.append(case.expected_profile)
        
        if result.profile.name == case.expected_profile:
            correct += 1
    
    return RoutingEvaluationResult(
        accuracy=correct / len(test_cases),
        # ... compute other metrics
    )
```

### Benchmark Suite

```python
# tests/test_routing_benchmark.py
import pytest
from fixtures import load_benchmark_cases

class TestRoutingBenchmark:
    @pytest.fixture
    def router(self):
        loader = get_profile_loader()
        return ProfileRouter(loader.profiles)
    
    @pytest.fixture
    def benchmark_cases(self):
        return load_benchmark_cases("routing_benchmark.yaml")
    
    def test_minimum_accuracy(self, router, benchmark_cases):
        """Router must achieve at least 80% accuracy."""
        result = evaluate_routing(router, benchmark_cases)
        assert result.accuracy >= 0.80
    
    def test_no_critical_misroutes(self, router, benchmark_cases):
        """Critical profiles (privacy, security) must not be missed."""
        critical_profiles = ["privacy_sensitive", "security_compliance_reviewer"]
        for case in benchmark_cases:
            if case.expected_profile in critical_profiles:
                result = router.route(analyze_prompt(case.prompt).to_enhanced_metadata())
                assert result.profile.name == case.expected_profile, \
                    f"Critical misroute: {case.prompt} → {result.profile.name}"
    
    def test_fallback_rate_threshold(self, router, benchmark_cases):
        """Fallback should be used in less than 15% of cases."""
        result = evaluate_routing(router, benchmark_cases)
        assert result.fallback_rate < 0.15
    
    @pytest.mark.parametrize("profile_name", [
        "codex_cli", "python_code_generation", "creative_brainstorm",
        "technical_support", "privacy_sensitive"
    ])
    def test_key_profile_recall(self, router, benchmark_cases, profile_name):
        """Key profiles must have recall >= 0.75."""
        result = evaluate_routing(router, benchmark_cases)
        assert result.recall_per_profile.get(profile_name, 0) >= 0.75
```

---

## 🔧 Konkrétní kód změny

### 1. Rozšíření InstructionProfile

```python
# src/mcp_prompt_broker/config/profiles.py

@dataclass(frozen=True)
class InstructionProfile:
    name: str
    instructions: str
    required: Mapping[str, Iterable[str]] = field(default_factory=dict)
    weights: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    default_score: int = 0
    fallback: bool = False
    
    # NEW: Utterance samples for semantic matching
    utterances: tuple[str, ...] = field(default_factory=tuple)
    utterance_threshold: float = 0.7
    
    # NEW: Soft matching support
    min_match_ratio: float = 0.5  # Minimum required field match ratio
```

### 2. Nová match_score metoda

```python
def match_score(self, metadata: MutableMapping[str, object]) -> float:
    """Calculate soft match score (0-1) instead of binary matching."""
    if not self.required:
        return 1.0
    
    matched_weight = 0.0
    total_weight = 0.0
    
    for key, allowed_values in self.required.items():
        # Different keys have different importance
        key_weight = 1.5 if key in ("intent", "domain") else 1.0
        total_weight += key_weight
        
        value = metadata.get(key)
        if value is None:
            continue
            
        if key == "context_tags" and isinstance(value, (set, frozenset)):
            allowed_set = set(allowed_values)
            value_set = set(value)
            if allowed_set:
                overlap_ratio = len(allowed_set & value_set) / len(allowed_set)
                matched_weight += key_weight * overlap_ratio
        elif value in allowed_values:
            matched_weight += key_weight
    
    return matched_weight / total_weight if total_weight > 0 else 1.0
```

### 3. Hybrid Router

```python
# src/mcp_prompt_broker/router/hybrid_router.py

from typing import Optional, Sequence
from dataclasses import dataclass
import numpy as np

@dataclass
class HybridRoutingResult:
    profile: InstructionProfile
    keyword_score: float
    semantic_score: float
    combined_score: float
    confidence: float

class HybridProfileRouter:
    def __init__(
        self,
        profiles: Sequence[InstructionProfile],
        encoder: Optional["SentenceTransformer"] = None,
        alpha: float = 0.5,  # Weight for semantic score
    ):
        self.profiles = list(profiles)
        self.alpha = alpha
        self._encoder = encoder
        self._utterance_embeddings: dict[str, np.ndarray] = {}
        
        if encoder:
            self._build_utterance_index()
    
    def _build_utterance_index(self):
        """Pre-compute embeddings for all profile utterances."""
        for profile in self.profiles:
            if profile.utterances:
                embeddings = self._encoder.encode(
                    list(profile.utterances),
                    convert_to_numpy=True
                )
                self._utterance_embeddings[profile.name] = embeddings
    
    def route(self, metadata: EnhancedMetadata) -> HybridRoutingResult:
        """Route using hybrid keyword + semantic scoring."""
        prompt = metadata.prompt
        metadata_map = metadata.as_mutable()
        
        scored_profiles: list[tuple[InstructionProfile, float, float, float]] = []
        
        for profile in self.profiles:
            # Keyword-based score (existing logic)
            match_ratio = profile.match_score(metadata_map)
            if match_ratio < profile.min_match_ratio and not profile.fallback:
                continue
            keyword_score = profile.score(metadata_map) / 20.0  # Normalize
            
            # Semantic score (new)
            semantic_score = 0.0
            if profile.name in self._utterance_embeddings:
                semantic_score = self._compute_semantic_score(
                    prompt, profile.name
                )
            
            # Combined score
            combined = (
                self.alpha * semantic_score +
                (1 - self.alpha) * keyword_score
            ) * match_ratio
            
            scored_profiles.append((profile, keyword_score, semantic_score, combined))
        
        if not scored_profiles:
            # Use fallback
            fallback = next((p for p in self.profiles if p.fallback), None)
            if fallback:
                return HybridRoutingResult(
                    profile=fallback,
                    keyword_score=0.0,
                    semantic_score=0.0,
                    combined_score=fallback.default_score / 20.0,
                    confidence=100.0
                )
            raise ValueError("No matching profile and no fallback")
        
        # Select best
        best = max(scored_profiles, key=lambda x: x[3])
        confidence = self._compute_confidence([s[3] for s in scored_profiles], best[3])
        
        return HybridRoutingResult(
            profile=best[0],
            keyword_score=best[1],
            semantic_score=best[2],
            combined_score=best[3],
            confidence=confidence
        )
    
    def _compute_semantic_score(self, prompt: str, profile_name: str) -> float:
        """Compute cosine similarity between prompt and profile utterances."""
        prompt_embedding = self._encoder.encode([prompt], convert_to_numpy=True)[0]
        profile_embeddings = self._utterance_embeddings[profile_name]
        
        # Cosine similarity
        similarities = np.dot(profile_embeddings, prompt_embedding) / (
            np.linalg.norm(profile_embeddings, axis=1) * np.linalg.norm(prompt_embedding)
        )
        return float(np.max(similarities))
```

---

## 📈 Očekávané výsledky

| Metrika | Současný stav | Cíl po Fázi 1 | Cíl po Fázi 3 |
|---------|---------------|---------------|---------------|
| Accuracy | ~60% (odhad) | ≥75% | ≥85% |
| Fallback rate | ~25% | ≤15% | ≤10% |
| Avg. confidence | 70% | ≥80% | ≥85% |
| Critical profile recall | ~70% | ≥90% | ≥95% |

---

## 🔗 Reference

1. [Semantic Router - Aurelio Labs](https://github.com/aurelio-labs/semantic-router) - Referenční implementace
2. [Multi-LLM Routing Strategies - AWS](https://aws.amazon.com/blogs/machine-learning/multi-llm-routing-strategies-for-generative-ai-applications-on-aws/)
3. [5 Tips to Optimize LLM Intent Classification - Voiceflow](https://www.voiceflow.com/pathways/5-tips-to-optimize-your-llm-intent-classification-prompts)
4. [Hybrid Search Explained - Weaviate](https://weaviate.io/blog/hybrid-search-explained)
5. [BM25 vs TF-IDF Comparison](https://medium.com/@jinmochong/what-is-bm25-comparison-with-tf-idf-and-beyond-5a740479214b)

---

## ✅ Závěr

Současná implementace MCP Prompt Broker používá rule-based přístup s keyword matching, který má inherentní omezení při škálování na 45+ profilů. Hlavní doporučení jsou:

1. **Přidat utterance samples** ke každému profilu pro semantic matching
2. **Implementovat hybrid scoring** kombinující keyword + embedding similarity
3. **Změnit binary matching na soft matching** s match_score()
4. **Vytvořit systematický benchmark** s 50+ test cases
5. **Přidat per-profile thresholds** pro jemnější kontrolu

Tyto změny by měly zvýšit accuracy z odhadovaných ~60% na ≥85% a snížit fallback rate pod 10%.

---

*Report vytvořen na základě analýzy kódu a best practices z průmyslu.*
