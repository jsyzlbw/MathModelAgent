"""LLM 工厂模块，根据运行配置创建各 Agent 使用的 LLM 实例。"""

from app.config.runtime_registry import RuntimeConfigRegistry, get_runtime_registry
from app.core.llm.llm import LLM


class LLMFactory:
    """LLM 工厂类，根据配置创建协调者、建模手、代码手和写作手的 LLM 实例。"""

    task_id: str

    def __init__(
        self,
        task_id: str,
        registry: RuntimeConfigRegistry | None = None,
    ) -> None:
        self.task_id = task_id
        self.registry = registry or get_runtime_registry()

    def get_all_llms(self) -> tuple[LLM, LLM, LLM, LLM]:
        """创建所有 Agent 的 LLM 实例。

        Returns:
            包含 (coordinator_llm, modeler_llm, coder_llm, writer_llm) 的元组。
        """
        coordinator = self.registry.llm_role("coordinator")
        modeler = self.registry.llm_role("modeler")
        coder = self.registry.llm_role("coder")
        writer = self.registry.llm_role("writer")

        coordinator_llm = LLM(
            api_type=coordinator.api_type,
            api_key=coordinator.api_key,
            model=coordinator.model,
            base_url=coordinator.base_url,
            task_id=self.task_id,
            max_tokens=coordinator.max_tokens,
        )

        modeler_llm = LLM(
            api_type=modeler.api_type,
            api_key=modeler.api_key,
            model=modeler.model,
            base_url=modeler.base_url,
            task_id=self.task_id,
            max_tokens=modeler.max_tokens,
        )

        coder_llm = LLM(
            api_type=coder.api_type,
            api_key=coder.api_key,
            model=coder.model,
            base_url=coder.base_url,
            task_id=self.task_id,
            max_tokens=coder.max_tokens,
        )

        writer_llm = LLM(
            api_type=writer.api_type,
            api_key=writer.api_key,
            model=writer.model,
            base_url=writer.base_url,
            task_id=self.task_id,
            max_tokens=writer.max_tokens,
        )

        return coordinator_llm, modeler_llm, coder_llm, writer_llm
