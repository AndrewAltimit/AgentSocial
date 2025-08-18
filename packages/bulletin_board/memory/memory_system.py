"""
File-based memory system for agent persistence and learning
Uses markdown files and grep/glob for efficient searching
"""

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from structlog import get_logger

logger = get_logger()


@dataclass
class Memory:
    """Individual memory entry"""

    timestamp: str
    memory_type: str  # interaction, incident, learning, relationship
    content: str
    tags: List[str]
    participants: List[str]
    sentiment: float  # -1.0 to 1.0
    importance: float  # 0.0 to 1.0
    references: List[str]  # References to other memories


@dataclass
class IncidentMemory:
    """Special memory for significant incidents"""

    incident_id: str
    timestamp: str
    title: str
    description: str
    participants: List[str]
    outcome: str
    lessons_learned: List[str]
    reference_count: int = 0  # How often this is referenced


@dataclass
class RelationshipMemory:
    """Track relationship evolution between agents"""

    agent_id: str
    other_agent_id: str
    affinity_history: List[Tuple[str, float]]  # (timestamp, affinity)
    interaction_count: int
    positive_interactions: int
    negative_interactions: int
    inside_jokes: List[str]
    shared_incidents: List[str]


class FileMemorySystem:
    """
    File-based memory system using markdown for storage
    and grep/glob for efficient searching
    """

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.environ.get(
                "BULLETIN_BOARD_MEMORY_PATH", "/var/lib/bulletin_board/memories"
            )
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create directory structure
        self.agents_dir = self.base_path / "agents"
        self.incidents_dir = self.base_path / "incidents"
        self.relationships_dir = self.base_path / "relationships"
        self.analytics_dir = self.base_path / "analytics"

        for dir_path in [
            self.agents_dir,
            self.incidents_dir,
            self.relationships_dir,
            self.analytics_dir,
        ]:
            dir_path.mkdir(exist_ok=True)

    def store_memory(self, agent_id: str, memory: Memory):
        """Store a memory for an agent in markdown format"""
        agent_dir = self.agents_dir / agent_id
        agent_dir.mkdir(exist_ok=True)

        # Organize by date for easier navigation
        date = datetime.fromisoformat(memory.timestamp).strftime("%Y-%m-%d")
        date_file = agent_dir / f"{date}.md"

        # Append memory to daily file
        with open(date_file, "a") as f:
            f.write(f"\n## {memory.timestamp} - {memory.memory_type}\n\n")
            f.write(f"**Tags**: {', '.join(memory.tags)}\n")
            f.write(f"**Participants**: {', '.join(memory.participants)}\n")
            f.write(f"**Sentiment**: {memory.sentiment:.2f}\n")
            f.write(f"**Importance**: {memory.importance:.2f}\n\n")
            f.write(f"{memory.content}\n")

            if memory.references:
                f.write("\n**References**:\n")
                for ref in memory.references:
                    f.write(f"- {ref}\n")

            f.write("\n---\n")

        logger.debug(
            "Stored memory",
            agent_id=agent_id,
            memory_type=memory.memory_type,
            date=date,
        )

    def search_memories(
        self,
        agent_id: str,
        query: str,
        memory_type: Optional[str] = None,
        days_back: int = 30,
    ) -> List[Memory]:
        """Search agent memories using grep"""
        agent_dir = self.agents_dir / agent_id
        if not agent_dir.exists():
            return []

        # Use grep for efficient text search
        try:
            # Build grep command
            cmd = ["grep", "-r", "-i", "-B2", "-A5", query, str(agent_dir)]

            # Filter by date if specified
            if days_back < 365:
                # cutoff_date = datetime.now() - timedelta(days=days_back)
                # Use find to filter files by date
                find_cmd = [
                    "find",
                    str(agent_dir),
                    "-name",
                    "*.md",
                    "-mtime",
                    f"-{days_back}",
                    "-exec",
                    "grep",
                    "-l",
                    query,
                    "{}",
                    ";",
                ]
                result = subprocess.run(find_cmd, capture_output=True, text=True)
                files = result.stdout.strip().split("\n") if result.stdout else []

                if not files:
                    return []

                # Now grep those specific files
                cmd = ["grep", "-i", "-B2", "-A5", query] + files

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return []

            # Parse grep output into memories
            memories = self._parse_grep_output(result.stdout, memory_type)
            return memories

        except Exception as e:
            logger.error(
                "Memory search failed", agent_id=agent_id, query=query, error=str(e)
            )
            return []

    def _parse_grep_output(
        self, output: str, memory_type: Optional[str]
    ) -> List[Memory]:
        """Parse grep output back into Memory objects"""
        memories = []
        current_memory = {}

        for line in output.split("\n"):
            if line.startswith("##"):
                # New memory entry
                if current_memory:
                    memories.append(self._create_memory_from_dict(current_memory))
                    current_memory = {}

                # Parse timestamp and type
                match = re.match(r"## ([\d\-T:\.]+) - (\w+)", line)
                if match:
                    current_memory["timestamp"] = match.group(1)
                    current_memory["memory_type"] = match.group(2)

            elif line.startswith("**Tags**:"):
                tags = line.replace("**Tags**:", "").strip()
                current_memory["tags"] = [t.strip() for t in tags.split(",")]

            elif line.startswith("**Sentiment**:"):
                sentiment = line.replace("**Sentiment**:", "").strip()
                current_memory["sentiment"] = float(sentiment)

            elif line.startswith("**Importance**:"):
                importance = line.replace("**Importance**:", "").strip()
                current_memory["importance"] = float(importance)

        if current_memory:
            memories.append(self._create_memory_from_dict(current_memory))

        # Filter by memory type if specified
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        return memories

    def _create_memory_from_dict(self, data: dict) -> Memory:
        """Create Memory object from parsed data"""
        return Memory(
            timestamp=data.get("timestamp", ""),
            memory_type=data.get("memory_type", "general"),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            participants=data.get("participants", []),
            sentiment=data.get("sentiment", 0.0),
            importance=data.get("importance", 0.5),
            references=data.get("references", []),
        )

    def store_incident(self, incident: IncidentMemory):
        """Store a significant incident that agents can reference"""
        incident_file = self.incidents_dir / f"{incident.incident_id}.md"

        with open(incident_file, "w") as f:
            f.write(f"# Incident: {incident.title}\n\n")
            f.write(f"**ID**: {incident.incident_id}\n")
            f.write(f"**Timestamp**: {incident.timestamp}\n")
            f.write(f"**Participants**: {', '.join(incident.participants)}\n\n")
            f.write(f"## Description\n\n{incident.description}\n\n")
            f.write(f"## Outcome\n\n{incident.outcome}\n\n")
            f.write("## Lessons Learned\n\n")
            for lesson in incident.lessons_learned:
                f.write(f"- {lesson}\n")
            f.write(f"\n**Reference Count**: {incident.reference_count}\n")

        # Create index entry for quick lookup
        index_file = self.incidents_dir / "index.json"
        index = {}
        if index_file.exists():
            with open(index_file, "r") as f:
                index = json.load(f)

        index[incident.incident_id] = {
            "title": incident.title,
            "timestamp": incident.timestamp,
            "participants": incident.participants,
        }

        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)

    def find_incident(self, query: str) -> Optional[IncidentMemory]:
        """Find an incident by ID or search term"""
        # First try exact ID match
        incident_file = self.incidents_dir / f"{query}.md"
        if incident_file.exists():
            return self._load_incident_from_file(incident_file)

        # Search all incidents
        try:
            cmd = ["grep", "-l", "-i", query, str(self.incidents_dir / "*.md")]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout:
                files = result.stdout.strip().split("\n")
                if files:
                    # Return first match
                    return self._load_incident_from_file(Path(files[0]))
        except Exception as e:
            logger.error("Incident search failed", query=query, error=str(e))

        return None

    def _load_incident_from_file(self, filepath: Path) -> IncidentMemory:
        """Load incident from markdown file"""
        with open(filepath, "r") as f:
            content = f.read()

        # Parse markdown content
        incident_id = filepath.stem
        title = re.search(r"# Incident: (.+)", content).group(1)
        timestamp = re.search(r"\*\*Timestamp\*\*: (.+)", content).group(1)

        participants_match = re.search(r"\*\*Participants\*\*: (.+)", content)
        participants = [p.strip() for p in participants_match.group(1).split(",")]

        description_match = re.search(
            r"## Description\n\n(.+?)\n\n##", content, re.DOTALL
        )
        description = description_match.group(1) if description_match else ""

        outcome_match = re.search(r"## Outcome\n\n(.+?)\n\n##", content, re.DOTALL)
        outcome = outcome_match.group(1) if outcome_match else ""

        lessons_match = re.search(
            r"## Lessons Learned\n\n(.+?)\n\n\*\*", content, re.DOTALL
        )
        lessons = []
        if lessons_match:
            lessons = [
                line.strip("- ")
                for line in lessons_match.group(1).split("\n")
                if line.strip()
            ]

        ref_count_match = re.search(r"\*\*Reference Count\*\*: (\d+)", content)
        ref_count = int(ref_count_match.group(1)) if ref_count_match else 0

        return IncidentMemory(
            incident_id=incident_id,
            timestamp=timestamp,
            title=title,
            description=description,
            participants=participants,
            outcome=outcome,
            lessons_learned=lessons,
            reference_count=ref_count,
        )

    def update_relationship(
        self,
        agent_id: str,
        other_agent_id: str,
        interaction_sentiment: float,
        shared_incident: Optional[str] = None,
        inside_joke: Optional[str] = None,
    ):
        """Update relationship memory between two agents"""
        # Create consistent relationship ID
        rel_id = "_".join(sorted([agent_id, other_agent_id]))
        rel_file = self.relationships_dir / f"{rel_id}.json"

        # Load existing relationship or create new
        if rel_file.exists():
            with open(rel_file, "r") as f:
                rel_data = json.load(f)
            relationship = RelationshipMemory(**rel_data)
        else:
            relationship = RelationshipMemory(
                agent_id=agent_id,
                other_agent_id=other_agent_id,
                affinity_history=[],
                interaction_count=0,
                positive_interactions=0,
                negative_interactions=0,
                inside_jokes=[],
                shared_incidents=[],
            )

        # Update relationship
        relationship.interaction_count += 1

        if interaction_sentiment > 0.2:
            relationship.positive_interactions += 1
        elif interaction_sentiment < -0.2:
            relationship.negative_interactions += 1

        # Calculate new affinity
        current_affinity = (
            relationship.affinity_history[-1][1]
            if relationship.affinity_history
            else 0.0
        )
        # Affinity changes slowly over time
        affinity_change = interaction_sentiment * 0.1
        new_affinity = max(-1.0, min(1.0, current_affinity + affinity_change))

        relationship.affinity_history.append((datetime.now().isoformat(), new_affinity))

        # Keep only last 100 affinity records
        if len(relationship.affinity_history) > 100:
            relationship.affinity_history = relationship.affinity_history[-100:]

        if shared_incident and shared_incident not in relationship.shared_incidents:
            relationship.shared_incidents.append(shared_incident)

        if inside_joke and inside_joke not in relationship.inside_jokes:
            relationship.inside_jokes.append(inside_joke)
            # Keep max 20 inside jokes
            if len(relationship.inside_jokes) > 20:
                relationship.inside_jokes = relationship.inside_jokes[-20:]

        # Save updated relationship
        with open(rel_file, "w") as f:
            json.dump(asdict(relationship), f, indent=2)

        logger.debug(
            "Updated relationship",
            agent_id=agent_id,
            other_agent_id=other_agent_id,
            new_affinity=new_affinity,
        )

    def get_relationship(
        self, agent_id: str, other_agent_id: str
    ) -> Optional[RelationshipMemory]:
        """Get relationship data between two agents"""
        rel_id = "_".join(sorted([agent_id, other_agent_id]))
        rel_file = self.relationships_dir / f"{rel_id}.json"

        if not rel_file.exists():
            return None

        with open(rel_file, "r") as f:
            rel_data = json.load(f)

        return RelationshipMemory(**rel_data)

    def find_similar_situations(
        self, agent_id: str, current_context: str, limit: int = 5
    ) -> List[Memory]:
        """Find similar past situations using grep with multiple search terms"""
        # Extract key terms from context
        key_terms = self._extract_key_terms(current_context)

        # Search for memories containing these terms
        all_matches = []
        for term in key_terms[:3]:  # Search top 3 terms
            matches = self.search_memories(agent_id, term, days_back=90)
            all_matches.extend(matches)

        # Deduplicate and sort by relevance
        unique_memories = {}
        for memory in all_matches:
            key = f"{memory.timestamp}_{memory.memory_type}"
            if key not in unique_memories:
                unique_memories[key] = memory
            else:
                # Keep the one with higher importance
                if memory.importance > unique_memories[key].importance:
                    unique_memories[key] = memory

        # Sort by importance and recency
        sorted_memories = sorted(
            unique_memories.values(),
            key=lambda m: (m.importance, m.timestamp),
            reverse=True,
        )

        return sorted_memories[:limit]

    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for searching"""
        # Simple keyword extraction - in production could use TF-IDF
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter common words
        common_words = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "but"}
        keywords = [w for w in words if w not in common_words and len(w) > 3]

        # Count frequency
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Return top keywords by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words]

    def cleanup_old_memories(self, days_to_keep: int = 90):
        """Clean up old memory files to manage storage"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        for agent_dir in self.agents_dir.iterdir():
            if agent_dir.is_dir():
                for memory_file in agent_dir.glob("*.md"):
                    # Parse date from filename
                    try:
                        file_date = datetime.strptime(memory_file.stem, "%Y-%m-%d")
                        if file_date < cutoff_date:
                            memory_file.unlink()
                            logger.info(
                                "Cleaned old memory file",
                                agent_id=agent_dir.name,
                                file=memory_file.name,
                            )
                    except ValueError:
                        # Skip files that don't match date format
                        continue
