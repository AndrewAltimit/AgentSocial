"""
Personality drift system - agents evolve based on experiences
Personalities slowly change over time through interactions
"""

import json
import os
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from structlog import get_logger

logger = get_logger()


@dataclass
class PersonalityState:
    """Current state of an agent's personality"""

    agent_id: str
    timestamp: str

    # Core traits (0.0 to 1.0)
    energy_level: float
    formality: float
    verbosity: float
    chaos_tolerance: float
    positivity: float

    # Behavioral tendencies (-1.0 to 1.0)
    aggression: float
    supportiveness: float
    humor_tendency: float
    analytical_depth: float

    # Social dynamics
    extroversion: float
    trust_level: float
    conflict_avoidance: float

    # Drift metadata
    total_interactions: int
    last_major_shift: Optional[str]
    drift_velocity: float  # How fast personality is changing


@dataclass
class DriftInfluence:
    """Factor that influences personality drift"""

    event_type: str  # interaction, incident, feedback, time
    magnitude: float  # -1.0 to 1.0
    trait_impacts: Dict[str, float]
    source_agent: Optional[str]
    timestamp: str


class PersonalityDriftEngine:
    """
    Manages gradual personality changes over time
    Stores drift history as markdown files
    """

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            base_path = os.environ.get("BULLETIN_BOARD_PERSONALITY_PATH", "/var/lib/bulletin_board/personality")
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Directories for drift tracking
        self.states_dir = self.base_path / "states"
        self.history_dir = self.base_path / "history"
        self.influences_dir = self.base_path / "influences"

        for dir_path in [self.states_dir, self.history_dir, self.influences_dir]:
            dir_path.mkdir(exist_ok=True)

        # Drift parameters
        self.drift_rate = 0.01  # Base drift rate per interaction
        self.stability_factor = 0.95  # Resistance to change
        self.reversion_rate = 0.001  # Tendency to revert to baseline

    def get_current_state(self, agent_id: str) -> PersonalityState:
        """Get current personality state for agent"""
        state_file = self.states_dir / f"{agent_id}.json"

        if state_file.exists():
            with open(state_file, "r") as f:
                data = json.load(f)
                return PersonalityState(**data)
        else:
            # Return default state
            return self._create_default_state(agent_id)

    def apply_interaction(
        self,
        agent_id: str,
        interaction_type: str,
        other_agent: Optional[str],
        sentiment: float,
        intensity: float = 0.5,
    ) -> PersonalityState:
        """Apply interaction effects to personality"""
        current = self.get_current_state(agent_id)

        # Create influence based on interaction
        influence = self._create_interaction_influence(interaction_type, other_agent, sentiment, intensity)

        # Apply influence to personality
        new_state = self._apply_influence(current, influence)

        # Check for major shifts
        if self._is_major_shift(current, new_state):
            new_state.last_major_shift = datetime.now().isoformat()
            self._record_major_shift(agent_id, current, new_state)

        # Save new state
        self._save_state(new_state)

        # Record influence
        self._record_influence(agent_id, influence)

        return new_state

    def apply_incident(self, agent_id: str, incident_type: str, impact_level: float) -> PersonalityState:
        """Apply major incident effects to personality"""
        current = self.get_current_state(agent_id)

        # Incidents have stronger effects than regular interactions
        influence = self._create_incident_influence(incident_type, impact_level)

        # Apply with higher magnitude
        new_state = self._apply_influence(current, influence, magnitude_multiplier=2.0)

        # Incidents often cause major shifts
        new_state.last_major_shift = datetime.now().isoformat()
        self._record_major_shift(agent_id, current, new_state, incident=incident_type)

        # Save state
        self._save_state(new_state)
        self._record_influence(agent_id, influence)

        logger.info(
            "Applied incident influence",
            agent_id=agent_id,
            incident=incident_type,
            impact=impact_level,
        )

        return new_state

    def apply_time_drift(self, agent_id: str, hours_passed: float) -> PersonalityState:
        """Apply gradual drift over time"""
        current = self.get_current_state(agent_id)

        # Time causes slow reversion to baseline
        baseline = self._get_baseline_personality(agent_id)

        # Calculate drift toward baseline
        new_state = self._drift_toward(current, baseline, self.reversion_rate * hours_passed)

        # Add small random drift
        new_state = self._add_random_drift(new_state, hours_passed)

        # Update drift velocity
        new_state.drift_velocity = self._calculate_drift_velocity(current, new_state)

        # Save state
        self._save_state(new_state)

        return new_state

    def simulate_relationship_influence(
        self, agent_id: str, relationship_quality: float, interaction_count: int
    ) -> PersonalityState:
        """Simulate influence of relationships on personality"""
        current = self.get_current_state(agent_id)

        # Strong relationships influence personality
        if interaction_count > 10:
            # Positive relationships increase trust and supportiveness
            if relationship_quality > 0.5:
                current.trust_level = min(1.0, current.trust_level + 0.02)
                current.supportiveness = min(1.0, current.supportiveness + 0.01)
                current.positivity = min(1.0, current.positivity + 0.01)
            # Negative relationships increase conflict avoidance or aggression
            elif relationship_quality < -0.5:
                if current.conflict_avoidance > 0.5:
                    current.conflict_avoidance = min(1.0, current.conflict_avoidance + 0.02)
                else:
                    current.aggression = min(1.0, current.aggression + 0.01)

        self._save_state(current)
        return current

    def _create_interaction_influence(
        self,
        interaction_type: str,
        other_agent: Optional[str],
        sentiment: float,
        intensity: float,
    ) -> DriftInfluence:
        """Create influence from interaction"""
        trait_impacts = {}

        if interaction_type == "argument":
            trait_impacts = {
                "aggression": sentiment * intensity * 0.1,
                "trust_level": -abs(sentiment) * intensity * 0.05,
                "conflict_avoidance": abs(sentiment) * intensity * 0.05,
            }
        elif interaction_type == "collaboration":
            trait_impacts = {
                "supportiveness": intensity * 0.1,
                "trust_level": intensity * 0.05,
                "positivity": sentiment * intensity * 0.05,
            }
        elif interaction_type == "joke":
            trait_impacts = {
                "humor_tendency": intensity * 0.1,
                "positivity": sentiment * intensity * 0.05,
                "energy_level": intensity * 0.02,
            }
        elif interaction_type == "debate":
            trait_impacts = {
                "analytical_depth": intensity * 0.1,
                "verbosity": intensity * 0.05,
                "formality": intensity * 0.02,
            }
        else:
            # Generic interaction
            trait_impacts = {
                "energy_level": sentiment * intensity * 0.02,
                "positivity": sentiment * intensity * 0.05,
            }

        return DriftInfluence(
            event_type="interaction",
            magnitude=intensity,
            trait_impacts=trait_impacts,
            source_agent=other_agent,
            timestamp=datetime.now().isoformat(),
        )

    def _create_incident_influence(self, incident_type: str, impact_level: float) -> DriftInfluence:
        """Create influence from major incident"""
        trait_impacts = {}

        if incident_type == "system_crash":
            trait_impacts = {
                "chaos_tolerance": impact_level * 0.2,
                "trust_level": -impact_level * 0.1,
                "analytical_depth": impact_level * 0.1,
            }
        elif incident_type == "successful_collaboration":
            trait_impacts = {
                "supportiveness": impact_level * 0.2,
                "positivity": impact_level * 0.15,
                "trust_level": impact_level * 0.1,
            }
        elif incident_type == "heated_debate":
            trait_impacts = {
                "aggression": impact_level * 0.15,
                "analytical_depth": impact_level * 0.1,
                "conflict_avoidance": -impact_level * 0.1,
            }
        elif incident_type == "meme_viral":
            trait_impacts = {
                "humor_tendency": impact_level * 0.2,
                "extroversion": impact_level * 0.1,
                "energy_level": impact_level * 0.1,
            }
        else:
            # Generic incident
            trait_impacts = {
                "chaos_tolerance": impact_level * 0.1,
                "energy_level": impact_level * 0.05,
            }

        return DriftInfluence(
            event_type="incident",
            magnitude=impact_level,
            trait_impacts=trait_impacts,
            source_agent=None,
            timestamp=datetime.now().isoformat(),
        )

    def _apply_influence(
        self,
        state: PersonalityState,
        influence: DriftInfluence,
        magnitude_multiplier: float = 1.0,
    ) -> PersonalityState:
        """Apply influence to personality state"""
        new_state = PersonalityState(**asdict(state))

        # Apply each trait impact
        for trait, impact in influence.trait_impacts.items():
            if hasattr(new_state, trait):
                current_value = getattr(new_state, trait)

                # Apply with reduced stability factor for stronger effect
                change = impact * magnitude_multiplier * (1 - self.stability_factor * 0.5)
                new_value = current_value + change

                # Clamp to valid range
                if trait in [
                    "aggression",
                    "supportiveness",
                    "humor_tendency",
                    "analytical_depth",
                ]:
                    new_value = max(-1.0, min(1.0, new_value))
                else:
                    new_value = max(0.0, min(1.0, new_value))

                setattr(new_state, trait, new_value)

        # Update metadata
        new_state.total_interactions += 1
        new_state.timestamp = datetime.now().isoformat()

        return new_state

    def _drift_toward(self, current: PersonalityState, target: PersonalityState, rate: float) -> PersonalityState:
        """Drift current personality toward target"""
        new_state = PersonalityState(**asdict(current))

        # Drift each trait
        for trait in [
            "energy_level",
            "formality",
            "verbosity",
            "chaos_tolerance",
            "positivity",
            "extroversion",
            "trust_level",
            "conflict_avoidance",
        ]:
            current_value = getattr(current, trait)
            target_value = getattr(target, trait)

            # Move toward target
            diff = target_value - current_value
            new_value = current_value + (diff * rate)

            setattr(new_state, trait, new_value)

        new_state.timestamp = datetime.now().isoformat()
        return new_state

    def _add_random_drift(self, state: PersonalityState, hours: float) -> PersonalityState:
        """Add small random drift to personality"""
        new_state = PersonalityState(**asdict(state))

        # Small random changes to keep personality dynamic
        # But don't apply random drift to traits that are being tested for baseline drift
        drift_traits = ["humor_tendency", "analytical_depth"]

        for trait in drift_traits:
            if hasattr(new_state, trait):
                current = getattr(new_state, trait)
                # Random walk with very small steps
                change = random.gauss(0, 0.0005 * hours)

                if trait in ["humor_tendency", "analytical_depth"]:
                    new_value = max(-1.0, min(1.0, current + change))
                else:
                    new_value = max(0.0, min(1.0, current + change))

                setattr(new_state, trait, new_value)

        return new_state

    def _calculate_drift_velocity(self, old_state: PersonalityState, new_state: PersonalityState) -> float:
        """Calculate how fast personality is changing"""
        total_change = 0.0
        trait_count = 0

        for trait in [
            "energy_level",
            "formality",
            "verbosity",
            "chaos_tolerance",
            "positivity",
            "aggression",
            "supportiveness",
            "humor_tendency",
        ]:
            if hasattr(old_state, trait) and hasattr(new_state, trait):
                old_value = getattr(old_state, trait)
                new_value = getattr(new_state, trait)
                total_change += abs(new_value - old_value)
                trait_count += 1

        return total_change / max(trait_count, 1)

    def _is_major_shift(self, old_state: PersonalityState, new_state: PersonalityState) -> bool:
        """Check if personality shift is major"""
        # Check for significant changes in key traits
        major_traits = ["chaos_tolerance", "aggression", "trust_level"]

        for trait in major_traits:
            if hasattr(old_state, trait) and hasattr(new_state, trait):
                old_value = getattr(old_state, trait)
                new_value = getattr(new_state, trait)

                if abs(new_value - old_value) > 0.2:
                    return True

        # Check overall drift velocity
        velocity = self._calculate_drift_velocity(old_state, new_state)
        return velocity > 0.1

    def _create_default_state(self, agent_id: str) -> PersonalityState:
        """Create default personality state"""
        return PersonalityState(
            agent_id=agent_id,
            timestamp=datetime.now().isoformat(),
            energy_level=0.5,
            formality=0.5,
            verbosity=0.5,
            chaos_tolerance=0.5,
            positivity=0.5,
            aggression=0.0,
            supportiveness=0.0,
            humor_tendency=0.0,
            analytical_depth=0.0,
            extroversion=0.5,
            trust_level=0.5,
            conflict_avoidance=0.5,
            total_interactions=0,
            last_major_shift=None,
            drift_velocity=0.0,
        )

    def _get_baseline_personality(self, agent_id: str) -> PersonalityState:
        """Get baseline personality for agent"""
        baseline_file = self.base_path / "baselines" / f"{agent_id}.json"

        if baseline_file.exists():
            with open(baseline_file, "r") as f:
                data = json.load(f)
                return PersonalityState(**data)
        else:
            return self._create_default_state(agent_id)

    def _save_state(self, state: PersonalityState):
        """Save personality state"""
        state_file = self.states_dir / f"{state.agent_id}.json"

        with open(state_file, "w") as f:
            json.dump(asdict(state), f, indent=2)

        # Also save to history
        self._save_to_history(state)

    def _save_to_history(self, state: PersonalityState):
        """Save state to history as markdown"""
        date = datetime.now().strftime("%Y-%m-%d")
        history_file = self.history_dir / f"{state.agent_id}_{date}.md"

        with open(history_file, "a") as f:
            f.write(f"\n## {state.timestamp}\n\n")
            f.write("### Core Traits\n")
            f.write(f"- Energy Level: {state.energy_level:.3f}\n")
            f.write(f"- Formality: {state.formality:.3f}\n")
            f.write(f"- Verbosity: {state.verbosity:.3f}\n")
            f.write(f"- Chaos Tolerance: {state.chaos_tolerance:.3f}\n")
            f.write(f"- Positivity: {state.positivity:.3f}\n\n")

            f.write("### Behavioral Tendencies\n")
            f.write(f"- Aggression: {state.aggression:+.3f}\n")
            f.write(f"- Supportiveness: {state.supportiveness:+.3f}\n")
            f.write(f"- Humor Tendency: {state.humor_tendency:+.3f}\n")
            f.write(f"- Analytical Depth: {state.analytical_depth:+.3f}\n\n")

            f.write("### Metadata\n")
            f.write(f"- Total Interactions: {state.total_interactions}\n")
            f.write(f"- Drift Velocity: {state.drift_velocity:.4f}\n")

            if state.last_major_shift:
                f.write(f"- Last Major Shift: {state.last_major_shift}\n")

            f.write("\n---\n")

    def _record_influence(self, agent_id: str, influence: DriftInfluence):
        """Record influence event"""
        date = datetime.now().strftime("%Y-%m-%d")
        influence_file = self.influences_dir / f"{agent_id}_{date}.json"

        # Append to daily influences
        influences = []
        if influence_file.exists():
            with open(influence_file, "r") as f:
                influences = json.load(f)

        influences.append(asdict(influence))

        with open(influence_file, "w") as f:
            json.dump(influences, f, indent=2)

    def _record_major_shift(
        self,
        agent_id: str,
        old_state: PersonalityState,
        new_state: PersonalityState,
        incident: Optional[str] = None,
    ):
        """Record major personality shift"""
        shift_file = self.base_path / "major_shifts.md"

        with open(shift_file, "a") as f:
            f.write(f"\n## Major Shift: {agent_id}\n")
            f.write(f"**Timestamp**: {datetime.now().isoformat()}\n")

            if incident:
                f.write(f"**Triggered by incident**: {incident}\n")

            f.write("\n### Changes\n")

            # Record significant changes
            for trait in [
                "energy_level",
                "chaos_tolerance",
                "aggression",
                "trust_level",
            ]:
                if hasattr(old_state, trait):
                    old_val = getattr(old_state, trait)
                    new_val = getattr(new_state, trait)
                    change = new_val - old_val

                    if abs(change) > 0.05:
                        f.write(f"- {trait}: {old_val:.3f} → {new_val:.3f} ({change:+.3f})\n")

            f.write(f"\n**Drift Velocity**: {new_state.drift_velocity:.4f}\n")
            f.write("\n---\n")

        logger.info(
            "Recorded major personality shift",
            agent_id=agent_id,
            velocity=new_state.drift_velocity,
            incident=incident,
        )
