"""
Persistent memory system for inbox-Hero agent.

Provides long-term memory that survives process restarts by storing data in JSON.
The agent can call `remember()` to store facts and `recall()` to retrieve them.
"""

# Cert-ID: cert-aai-2026-06-0024

import json
from pathlib import Path
from datetime import datetime
from typing import Any


MEMORY_FILE = Path(__file__).parent / "model" / "memory_store.json"


class MemoryStore:
    """Manages persistent memory with conflict resolution."""

    def __init__(self):
        self.data = self._load_memory()

    def _load_memory(self) -> dict:
        """Load memory from disk if it exists, otherwise start with empty dict."""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load memory from {MEMORY_FILE}, starting fresh.")
                return {}
        return {}

    def _save_memory(self) -> None:
        """Save current memory to disk."""
        try:
            MEMORY_FILE.parent.mkdir(exist_ok=True)
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save memory to {MEMORY_FILE}: {e}")

    def remember(self, key: str, value: Any, source: str = "agent") -> dict[str, Any]:
        """
        Store a fact in persistent memory.

        Conflict Resolution Rule (LAST_WRITE_WINS):
        - If the key already exists with a DIFFERENT value, the new value overwrites it.
        - Metadata is updated to track the source and timestamp of the most recent write.
        - Old values are discarded (not versioned).

        Args:
            key: Unique identifier for the memory item
            value: The fact/data to store (can be string, number, dict, list, etc.)
            source: Who/what is storing this (default: "agent")

        Returns:
            dict with status, key, value, and metadata
        """
        if not key or not isinstance(key, str):
            return {
                "status": "error",
                "message": "Key must be a non-empty string",
                "key": key,
            }

        # Check if conflicting memory exists
        conflict_detected = False
        if key in self.data:
            old_value = self.data[key].get("value")
            if old_value != value:
                conflict_detected = True
                print(
                    f"[MEMORY] Conflict detected for key '{key}': "
                    f"old={old_value} -> new={value} (LAST_WRITE_WINS)"
                )

        # Store the new value with metadata
        self.data[key] = {
            "value": value,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "conflict_detected": conflict_detected,
        }

        self._save_memory()

        return {
            "status": "success",
            "message": f"Memory stored for key '{key}'",
            "key": key,
            "value": value,
            "conflict_detected": conflict_detected,
        }

    def recall(self, query: str) -> dict[str, Any]:
        """
        Retrieve previously stored memory.

        Supports two modes:
        1. Exact key match: if query is a registered key, return its value.
        2. Semantic search: if no exact match, search key names and values for the query term.

        Args:
            query: Either a key name or a search term

        Returns:
            dict with status and matching memories
        """
        if not query or not isinstance(query, str):
            return {
                "status": "error",
                "message": "Query must be a non-empty string",
            }

        query_lower = query.lower()

        # Try exact key match first
        if query in self.data:
            memory_item = self.data[query]
            return {
                "status": "success",
                "found": "exact_key_match",
                "key": query,
                "value": memory_item["value"],
                "source": memory_item.get("source", "unknown"),
                "timestamp": memory_item.get("timestamp"),
            }

        # Semantic search: find keys/values that contain the query term
        matches = []
        for key, item in self.data.items():
            value = item.get("value", "")
            
            # Search in key
            if query_lower in key.lower():
                matches.append({
                    "key": key,
                    "value": value,
                    "match_location": "key_name",
                    "source": item.get("source", "unknown"),
                    "timestamp": item.get("timestamp"),
                })
            # Search in value (if it's a string)
            elif isinstance(value, str) and query_lower in value.lower():
                matches.append({
                    "key": key,
                    "value": value,
                    "match_location": "value",
                    "source": item.get("source", "unknown"),
                    "timestamp": item.get("timestamp"),
                })

        if matches:
            return {
                "status": "success",
                "found": "semantic_search",
                "query": query,
                "matches": matches,
            }

        return {
            "status": "not_found",
            "message": f"No memory found for query '{query}'",
            "query": query,
        }

    def get_summary(self) -> str:
        """
        Return a concise summary of all stored memories for the system prompt.

        Returns:
            A formatted string summarizing all memories
        """
        if not self.data:
            return "No stored memories yet."

        lines = ["=== Stored Memories Summary ==="]
        for key, item in self.data.items():
            value = item.get("value", "N/A")
            source = item.get("source", "unknown")
            lines.append(f"- {key}: {value} (source: {source})")

        return "\n".join(lines)


# Global instance
_memory_store = None


def get_memory_store() -> MemoryStore:
    """Get or create the global memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store


def remember(key: str, value: Any, source: str = "agent") -> dict[str, Any]:
    """Convenience function to store memory."""
    return get_memory_store().remember(key, value, source)


def recall(query: str) -> dict[str, Any]:
    """Convenience function to retrieve memory."""
    return get_memory_store().recall(query)


def get_memory_summary() -> str:
    """Convenience function to get memory summary for system prompt."""
    return get_memory_store().get_summary()
