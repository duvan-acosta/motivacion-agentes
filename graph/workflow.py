"""Orquestación LangGraph end-to-end."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from agents.base import WorkflowState
from agents.content_creator import ContentCreatorAgent
from agents.director import DirectorAgent
from agents.publisher import PublisherAgent
from agents.video_producer import VideoProducerAgent
from agents.visual_designer import VisualDesignerAgent
from pipelines.image_pipeline import ImagePipeline
from pipelines.video_pipeline import VideoPipeline
from publishing.adapters.meta_instagram import MetaInstagramAdapter
from publishing.adapters.tiktok import TikTokAdapter
from publishing.adapters.twitter import TwitterAdapter
from publishing.adapters.youtube import YouTubeAdapter
from utils.config import ensure_dir, get_settings

logger = logging.getLogger(__name__)


class MotivacionWorkflow:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.director = DirectorAgent()
        self.content = ContentCreatorAgent()
        self.visual = VisualDesignerAgent()
        self.video_agent = VideoProducerAgent()
        self.publisher = PublisherAgent()
        self.image_pipeline = ImagePipeline()
        self.video_pipeline = VideoPipeline()
        self.graph = self._build_graph()

    def _node_director(self, state: WorkflowState) -> WorkflowState:
        plan = self.director.plan(state.get("theme"))
        state["theme"] = plan["theme"]
        state["content_id"] = plan["content_id"]
        state["metadata"] = {"planned_at": plan["planned_at"], "brand": plan["brand"]}
        state["errors"] = state.get("errors", [])
        return state

    def _node_content(self, state: WorkflowState) -> WorkflowState:
        result = self.content.generate(state["theme"], state.get("content_id"))
        state["content_id"] = result["content_id"]
        state["message"] = result["message"]
        state["caption"] = result["caption"]
        state["hashtags"] = result["hashtags"]
        state["visual_keywords"] = result["visual_keywords"]
        if result.get("script"):
            state["script"] = result["script"]
        return state

    def _node_visual(self, state: WorkflowState) -> WorkflowState:
        spec = self.visual.design(
            state["theme"], state["message"], state.get("visual_keywords")
        )
        state["visual_spec"] = spec
        return state

    def _node_images(self, state: WorkflowState) -> WorkflowState:
        try:
            images = self.image_pipeline.generate(
                state["message"], state["theme"], state["visual_spec"]
            )
            state["images"] = images
        except Exception as exc:
            logger.error("Image pipeline error: %s", exc)
            state.setdefault("errors", []).append(str(exc))
        return state

    def _node_video_script(self, state: WorkflowState) -> WorkflowState:
        result = self.video_agent.produce_script(
            state["message"], state["theme"], state.get("script", "")
        )
        state["script"] = result["script"]
        return state

    def _node_video(self, state: WorkflowState) -> WorkflowState:
        try:
            keywords = self.video_agent.get_video_keywords(
                state["theme"], state.get("visual_keywords", [])
            )
            video_path = self.video_pipeline.generate(
                state["script"], state["theme"], state["message"], keywords
            )
            state["video_path"] = video_path
        except Exception as exc:
            logger.error("Video pipeline error: %s", exc)
            state.setdefault("errors", []).append(str(exc))
            state["video_path"] = ""
        return state

    def _node_package(self, state: WorkflowState) -> WorkflowState:
        package = self.publisher.package(
            content_id=state["content_id"],
            theme=state["theme"],
            message=state["message"],
            caption=state["caption"],
            hashtags=state["hashtags"],
            script=state.get("script", ""),
            images=state.get("images", {}),
            video_path=state.get("video_path", ""),
            metadata=state.get("metadata"),
        )
        state["package_path"] = str(package)
        state["status"] = "ready"
        return state

    def _build_graph(self):
        graph = StateGraph(WorkflowState)
        graph.add_node("director", self._node_director)
        graph.add_node("content", self._node_content)
        graph.add_node("visual", self._node_visual)
        graph.add_node("images", self._node_images)
        graph.add_node("video_script", self._node_video_script)
        graph.add_node("video", self._node_video)
        graph.add_node("package", self._node_package)

        graph.set_entry_point("director")
        graph.add_edge("director", "content")
        graph.add_edge("content", "visual")
        graph.add_edge("visual", "images")
        graph.add_edge("images", "video_script")
        graph.add_edge("video_script", "video")
        graph.add_edge("video", "package")
        graph.add_edge("package", END)
        return graph.compile()

    def run(self, theme: str | None = None) -> dict[str, Any]:
        initial: WorkflowState = {"theme": theme or "", "errors": []}
        result = self.graph.invoke(initial)
        return dict(result)

    def publish_package(self, package_path: str, platforms: list[str] | None = None) -> list[dict]:
        from pathlib import Path

        path = Path(package_path)
        adapters = {
            "instagram": MetaInstagramAdapter(),
            "facebook": MetaInstagramAdapter(),
            "tiktok": TikTokAdapter(),
            "youtube": YouTubeAdapter(),
            "twitter": TwitterAdapter(),
        }
        targets = platforms or list(adapters.keys())
        results = []
        for name in targets:
            adapter = adapters.get(name)
            if not adapter:
                continue
            if name == "facebook" and isinstance(adapter, MetaInstagramAdapter):
                r = adapter.publish_facebook(path)
            else:
                r = adapter.publish(path)
            results.append(r.to_dict())
        return results


def run_generation(theme: str | None = None) -> dict[str, Any]:
    workflow = MotivacionWorkflow()
    return workflow.run(theme)
