import shlex
import subprocess
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class KimiCLIChatModel(BaseChatModel):
    """LangChain-compatible chat model wrapper for the Kimi CLI."""

    cli_command: str = "kimi"
    model: str = "moonshot-v1-8k"
    model_arg: str = "--model"
    prompt_arg: Optional[str] = None
    extra_args: Optional[str] = None
    timeout_seconds: int = 300

    @property
    def _llm_type(self) -> str:
        return "kimi-cli"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "cli_command": self.cli_command,
            "model": self.model,
            "model_arg": self.model_arg,
            "prompt_arg": self.prompt_arg,
            "extra_args": self.extra_args,
            "timeout_seconds": self.timeout_seconds,
        }

    def _build_prompt(self, messages: List[BaseMessage]) -> str:
        lines: List[str] = []
        for message in messages:
            role = message.type.upper()
            content = message.content
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            lines.append(f"[{role}] {content}")
        return "\n\n".join(lines)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if stop:
            # Kimi CLI wrapper currently does not support explicit stop tokens.
            pass

        prompt = self._build_prompt(messages)
        cmd = shlex.split(self.cli_command, posix=False)

        if self.model_arg and self.model:
            cmd.extend([self.model_arg, self.model])

        if self.extra_args:
            cmd.extend(shlex.split(self.extra_args, posix=False))

        stdin_payload: Optional[str] = prompt
        if self.prompt_arg:
            cmd.extend([self.prompt_arg, prompt])
            stdin_payload = None

        try:
            result = subprocess.run(
                cmd,
                input=stdin_payload,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Kimi CLI command not found: {self.cli_command}. Install/configure the CLI first."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Kimi CLI timed out after {self.timeout_seconds}s"
            ) from exc

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(
                f"Kimi CLI failed with exit code {result.returncode}: {stderr or 'no stderr'}"
            )

        text = (result.stdout or "").strip()
        generation = ChatGeneration(message=AIMessage(content=text))
        return ChatResult(generations=[generation])
