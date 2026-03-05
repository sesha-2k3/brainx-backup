"""
Semantic Search to find the contacts (Search bot, will use embeddings once scaled)
"""
import json
import logging
import httpx
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def semantic_search_with_explanation(query: str, contacts: list[dict]) -> dict:
    """
    Semantic search that returns only highly relevant matches.
    """
    if not contacts:
        return {"matches": [], "explanation": "No contacts in database."}
    
    # Build context from contacts
    context_parts = []
    for i, c in enumerate(contacts):
        parts = [f"#{i+1} {c.get('name', 'Unknown')}"]
        if c.get('company'):
            parts.append(f"({c['company']})")
        if c.get('role'):
            parts.append(f"[{c['role']}]")
        if c.get('category'):
            parts.append(f"<{c['category']}>")
        if c.get('notes'):
            parts.append(f"Notes: {c['notes'][:200]}")
        if c.get('context'):
            parts.append(f"Context: {c['context'][:200]}")
        if c.get('interactions'):
            parts.append(f"Interactions: {c['interactions'][:300]}")
        context_parts.append(" | ".join(parts))
    
    context = "\n".join(context_parts)
    
    prompt = f"""You are a precise CRM search assistant. Return ONLY contacts that DIRECTLY match the query.

CONTACTS:
{context}

QUERY: "{query}"

STRICT RULES:
- Only return contacts where the query topic appears in their notes, context, or interactions
- Do NOT return contacts just because they share a category (e.g., don't return all "investors" for a specific topic)
- If asking "who discussed X", only return contacts whose interactions mention X
- If asking "who is X", only return contacts named X
- Be STRICT - fewer accurate results is better than many irrelevant ones
- If no contacts directly match, return empty array

Respond with JSON only:
{{
  "matches": [1, 2],
  "explanation": "Why these specific contacts match"
}}

JSON:"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 300,
                },
                timeout=30.0,
            )
            
            if response.status_code != 200:
                logger.error(f"Groq API error: {response.status_code}")
                return {"matches": [], "explanation": "Search service unavailable."}
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"Query: {query}")
            logger.info(f"LLM response: {content}")
            
            # Clean up
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            
            result = json.loads(content)
            
            # Convert indices to actual contacts
            matches = []
            for idx in result.get("matches", []):
                actual_idx = idx - 1
                if 0 <= actual_idx < len(contacts):
                    matches.append(contacts[actual_idx])
            
            return {
                "matches": matches,
                "explanation": result.get("explanation", ""),
            }
            
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return {"matches": [], "explanation": "Search failed."}