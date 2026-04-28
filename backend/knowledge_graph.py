# ========= KNOWLEDGE GRAPH ENGINE =========
# Extracts concepts and relationships from PDF text using AI,
# stores them in a NetworkX graph, and provides visualization data.

import json
import os
import networkx as nx
from config import client, MODEL_NAME


def extract_concepts_from_text(text: str) -> dict:
    """
    Use Gemini to extract key concepts and their relationships
    from a chunk of text.
    """
    prompt = f"""Analyze the following text and extract key concepts and their relationships.

Return ONLY a valid JSON object with this exact structure:
{{
  "concepts": ["concept1", "concept2", "concept3"],
  "relationships": [
    {{"source": "concept1", "target": "concept2", "relation": "is part of"}},
    {{"source": "concept2", "target": "concept3", "relation": "depends on"}}
  ]
}}

Rules:
- Extract 5-15 key concepts (nouns, technical terms, important ideas)
- Identify meaningful relationships between them (e.g., "is part of", "causes", "depends on", "is type of", "produces", "requires", "regulates", "contains")
- Keep concept names SHORT (1-3 words)
- Only return the JSON, no extra text

Text:
{text[:3000]}"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        raw = response.text.strip()

        # Clean markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)
    except Exception as e:
        print(f"[KG] Extraction error: {e}")
        return {"concepts": [], "relationships": []}


def build_knowledge_graph(chunks: list) -> nx.DiGraph:
    """
    Build a NetworkX directed graph from a list of text chunks.
    Each chunk is analyzed for concepts and relationships.
    """
    G = nx.DiGraph()

    for i, chunk in enumerate(chunks):
        text = chunk if isinstance(chunk, str) else getattr(chunk, 'page_content', str(chunk))
        result = extract_concepts_from_text(text)

        # Add concept nodes
        for concept in result.get("concepts", []):
            concept_clean = concept.strip().title()
            if concept_clean:
                if G.has_node(concept_clean):
                    G.nodes[concept_clean]["weight"] = G.nodes[concept_clean].get("weight", 1) + 1
                    G.nodes[concept_clean]["chunks"].append(i)
                else:
                    G.add_node(concept_clean, weight=1, chunks=[i], mastery=0)

        # Add relationship edges
        for rel in result.get("relationships", []):
            source = rel.get("source", "").strip().title()
            target = rel.get("target", "").strip().title()
            relation = rel.get("relation", "related to")

            if source and target and source != target:
                # Ensure both nodes exist
                if not G.has_node(source):
                    G.add_node(source, weight=1, chunks=[i], mastery=0)
                if not G.has_node(target):
                    G.add_node(target, weight=1, chunks=[i], mastery=0)

                if G.has_edge(source, target):
                    G[source][target]["weight"] = G[source][target].get("weight", 1) + 1
                else:
                    G.add_edge(source, target, relation=relation, weight=1)

    return G


def graph_to_vis_data(G: nx.DiGraph, mastery_data: dict = None) -> dict:
    """
    Convert a NetworkX graph to vis-network compatible JSON format.
    mastery_data: optional dict of {concept: score} for coloring nodes.
    """
    if mastery_data is None:
        mastery_data = {}

    nodes = []
    for node, data in G.nodes(data=True):
        weight = data.get("weight", 1)
        mastery = mastery_data.get(node.lower(), data.get("mastery", 0))

        # Color based on mastery: red (0) -> yellow (50) -> green (100)
        if mastery >= 70:
            color = "#34d399"  # emerald
            border = "#059669"
        elif mastery >= 40:
            color = "#fbbf24"  # amber
            border = "#d97706"
        else:
            color = "#818cf8"  # indigo (default/unlearned)
            border = "#6366f1"

        nodes.append({
            "id": node,
            "label": node,
            "value": max(weight * 5, 10),
            "color": {
                "background": color,
                "border": border,
                "highlight": {"background": "#c084fc", "border": "#a855f7"}
            },
            "font": {"color": "#ffffff", "size": 12},
            "mastery": mastery,
            "weight": weight
        })

    edges = []
    for source, target, data in G.edges(data=True):
        edges.append({
            "from": source,
            "to": target,
            "label": data.get("relation", ""),
            "arrows": "to",
            "color": {"color": "rgba(255,255,255,0.2)", "highlight": "#818cf8"},
            "font": {"color": "rgba(255,255,255,0.5)", "size": 9, "align": "middle"},
            "smooth": {"type": "curvedCW", "roundness": 0.2}
        })

    return {"nodes": nodes, "edges": edges}


def save_graph(G: nx.DiGraph, filepath: str):
    """Save a NetworkX graph to disk as JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    data = nx.node_link_data(G)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def load_graph(filepath: str) -> nx.DiGraph:
    """Load a NetworkX graph from disk."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return nx.node_link_graph(data, directed=True)
    except Exception as e:
        print(f"[KG] Load error: {e}")
        return None


def merge_graphs(existing: nx.DiGraph, new_graph: nx.DiGraph) -> nx.DiGraph:
    """Merge a new graph into an existing one, combining weights."""
    merged = existing.copy() if existing else nx.DiGraph()

    for node, data in new_graph.nodes(data=True):
        if merged.has_node(node):
            merged.nodes[node]["weight"] = merged.nodes[node].get("weight", 1) + data.get("weight", 1)
            existing_chunks = merged.nodes[node].get("chunks", [])
            new_chunks = data.get("chunks", [])
            merged.nodes[node]["chunks"] = list(set(existing_chunks + new_chunks))
        else:
            merged.add_node(node, **data)

    for source, target, data in new_graph.edges(data=True):
        if merged.has_edge(source, target):
            merged[source][target]["weight"] = merged[source][target].get("weight", 1) + data.get("weight", 1)
        else:
            merged.add_edge(source, target, **data)

    return merged
