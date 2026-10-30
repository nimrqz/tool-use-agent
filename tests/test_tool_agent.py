import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tool_agent.agent import Agent  # noqa: E402
from tool_agent.tools import ToolError, Workspace, calculate  # noqa: E402

def tool_use(id, name, **inp):
    return NS(type="tool_use", id=id, name=name, input=inp)

def text(t):
    return NS(type="text", text=t)

class ScriptedClient:
    """Devolve respostas pré-definidas em sequência e guarda as requisições."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = NS(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs["messages"][:])
        content, stop = self.responses.pop(0)
        return NS(content=content, stop_reason=stop, usage=NS(input_tokens=10, output_tokens=5))

@pytest.fixture
def ws():
    return Workspace(ROOT / "workspace")

def test_calculate_basic_and_precedence():
    assert calculate("2 + 3 * 4") == "14"
    assert calculate("(120*49.90)+(60*129)") == "13728"

@pytest.mark.parametrize("bad", ["__import__('os').system('ls')", "2 ** 9999", "1/0", "abc", "2 +"])
def test_calculate_rejects_unsafe_or_invalid(bad):
    with pytest.raises(ToolError):
        calculate(bad)

def test_workspace_blocks_path_traversal(ws):
    with pytest.raises(ToolError):
        ws.read_file("../../etc/passwd")

def test_workspace_read_and_search(ws):
    assert "Plano Pro" in ws.read_file("vendas_q3.csv")
    assert "notas_reuniao.md" in ws.search_text("meta")

def test_agent_executes_parallel_tools_in_single_message(ws):
    client = ScriptedClient(
        ([tool_use("a", "list_files"), tool_use("b", "calculate", expression="2+2")], "tool_use"),
        ([text("Resultado 4")], "end_turn"),
    )
    result = Agent(ws, client=client).run("teste")
    assert result.answer == "Resultado 4" and result.steps == 2
    results_msg = client.requests[1][-1]
    assert results_msg["role"] == "user" and len(results_msg["content"]) == 2
    assert [s.name for s in result.trace if s.kind == "tool_call"] == ["list_files", "calculate"]
    assert result.input_tokens == 20

def test_agent_reports_tool_errors_back_to_model(ws):
    client = ScriptedClient(
        ([tool_use("a", "read_file", path="nao_existe.txt")], "tool_use"),
        ([text("Arquivo ausente")], "end_turn"),
    )
    result = Agent(ws, client=client).run("teste")
    assert result.trace[0].is_error
    sent = client.requests[1][-1]["content"][0]
    assert sent["is_error"] is True

def test_agent_unknown_tool_does_not_crash(ws):
    client = ScriptedClient(([tool_use("a", "rm_rf")], "tool_use"), ([text("ok")], "end_turn"))
    assert Agent(ws, client=client).run("x").trace[0].is_error

def test_agent_stops_at_max_steps(ws):
    loop = ([tool_use("a", "list_files")], "tool_use")
    client = ScriptedClient(*[loop] * 3)
    result = Agent(ws, client=client, max_steps=3).run("x")
    assert result.stop_reason == "max_steps"
