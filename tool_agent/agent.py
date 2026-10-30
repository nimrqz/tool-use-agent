import os
from dataclasses import dataclass, field
from typing import Callable

import anthropic

from .tools import ToolError, Workspace, build_registry, tool_schemas

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")

SYSTEM = """Você é um analista que investiga arquivos do workspace para responder perguntas.
Descubra os arquivos com list_files, leia o que precisar e use calculate para QUALQUER conta.
Chame ferramentas independentes em paralelo. Responda em português, citando de qual arquivo veio cada número.
Se não houver dados suficientes, diga o que falta em vez de inventar."""

@dataclass
class Step:
    kind: str  # "tool_call" | "text"
    name: str = ""
    input: dict = field(default_factory=dict)
    output: str = ""
    is_error: bool = False

@dataclass
class AgentResult:
    answer: str
    trace: list[Step]
    steps: int
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0

class Agent:
    def __init__(
        self,
        workspace: Workspace,
        client: anthropic.Anthropic | None = None,
        max_steps: int = 10,
        use_web_search: bool = False,
        on_step: Callable[[Step], None] | None = None,
    ):
        self.client = client or anthropic.Anthropic()
        self.registry = build_registry(workspace)
        self.tools: list[dict] = tool_schemas()
        if use_web_search:  # ferramenta de servidor: roda nos servidores da Anthropic
            self.tools.append({"type": "web_search_20260209", "name": "web_search", "max_uses": 3})
        self.max_steps = max_steps
        self.on_step = on_step or (lambda step: None)

    def _run_tool(self, name: str, args: dict) -> tuple[str, bool]:
        handler = self.registry.get(name)
        if handler is None:
            return f"Ferramenta desconhecida: {name}", True
        try:
            return handler(args), False
        except ToolError as exc:
            return f"Erro: {exc}", True
        except Exception as exc:  # nunca derruba o loop por bug de ferramenta
            return f"Erro inesperado ({type(exc).__name__}): {exc}", True

    def run(self, task: str) -> AgentResult:
        messages: list[dict] = [{"role": "user", "content": task}]
        trace: list[Step] = []
        in_tok = out_tok = 0

        for step in range(1, self.max_steps + 1):
            response = self.client.messages.create(
                model=MODEL, max_tokens=8000, system=SYSTEM, tools=self.tools, messages=messages
            )
            usage = getattr(response, "usage", None)
            in_tok += getattr(usage, "input_tokens", 0) or 0
            out_tok += getattr(usage, "output_tokens", 0) or 0
            messages.append({"role": "assistant", "content": response.content})

            texts = [b.text for b in response.content if b.type == "text"]
            if response.stop_reason == "tool_use":
                results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    output, is_error = self._run_tool(block.name, dict(block.input))
                    entry = Step("tool_call", block.name, dict(block.input), output, is_error)
                    trace.append(entry)
                    self.on_step(entry)
                    results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": output, "is_error": is_error,
                    })
                # todos os resultados na MESMA mensagem de usuário
                messages.append({"role": "user", "content": results})
                continue
            if response.stop_reason == "pause_turn":  # ferramenta de servidor ainda rodando
                continue

            final = "\n".join(texts).strip()
            if response.stop_reason == "refusal":
                final = final or "O modelo recusou esta solicitação."
            elif response.stop_reason == "max_tokens":
                final += "\n\n[resposta truncada por limite de tokens]"
            trace.append(Step("text", output=final))
            return AgentResult(final, trace, step, response.stop_reason, in_tok, out_tok)

        return AgentResult(
            f"Parei após {self.max_steps} passos sem concluir.", trace, self.max_steps, "max_steps", in_tok, out_tok
        )
