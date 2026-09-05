"""
Agent Plugin Registry — Dynamic discovery and lifecycle management for custom agent plugins.
Allows extending the multi-agent system with user-defined agent logic.
"""
import os
import sys
import logging
import importlib.util
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models import AgentPlugin
from app.services.multi_agent.blackboard import SharedBlackboard

logger = logging.getLogger(__name__)


class BaseAgentPlugin(ABC):
    """Abstract base class for all custom agent plugins."""
    name: str = "custom_agent"
    description: str = "Custom agent plugin"

    @abstractmethod
    def run(self, blackboard: SharedBlackboard, prompt: str = "") -> Dict[str, Any]:
        """Execute custom plugin logic and write results to the blackboard."""
        pass


class PluginRegistry:
    @staticmethod
    def list_plugins(db: Session) -> List[Dict[str, Any]]:
        """List all registered plugins."""
        plugins = db.query(AgentPlugin).all()
        # Seed built-in plugins if table is empty
        if not plugins:
            builtin_plugins = [
                AgentPlugin(
                    name="sentiment_analyzer",
                    description="Analyzes free-text columns for emotional sentiment and polarity score.",
                    file_path="plugins/sentiment_analyzer.py",
                    is_enabled=True
                ),
                AgentPlugin(
                    name="geo_clustering",
                    description="Clusters lat/long geographical coordinates into spatial density hotspots.",
                    file_path="plugins/geo_clustering.py",
                    is_enabled=True
                ),
                AgentPlugin(
                    name="cohort_retention",
                    description="Computes user retention curves and cohort heatmaps over time intervals.",
                    file_path="plugins/cohort_retention.py",
                    is_enabled=False
                )
            ]
            for p in builtin_plugins:
                db.add(p)
            db.commit()
            plugins = db.query(AgentPlugin).all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "file_path": p.file_path,
                "is_enabled": p.is_enabled,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in plugins
        ]

    @staticmethod
    def toggle_plugin(plugin_id: str, is_enabled: bool, db: Session) -> Dict[str, Any]:
        """Enable or disable a plugin."""
        plugin = db.query(AgentPlugin).filter(AgentPlugin.id == plugin_id).first()
        if not plugin:
            raise ValueError(f"Plugin {plugin_id} not found")

        plugin.is_enabled = is_enabled
        db.commit()
        return {
            "id": plugin.id,
            "name": plugin.name,
            "is_enabled": plugin.is_enabled
        }
