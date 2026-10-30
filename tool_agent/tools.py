import ast
import operator
from pathlib import Path

class ToolError(Exception):
    pass

_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UN = {ast.USub: operator.neg, ast.UAdd: operator.pos}

def calculate(expression: str) -> str:
    """Avalia aritmética com segurança (sem eval): + - * / ** % //, parênteses."""

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ToolError("Expoente grande demais")
            return _BIN[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UN:
            return _UN[type(node.op)](ev(node.operand))
        raise ToolError("Expressão inválida: só números e operadores aritméticos")

    try:
        result = ev(ast.parse(expression.strip(), mode="eval").body)
    except ZeroDivisionError:
        raise ToolError("Divisão por zero") from None
    except SyntaxError:
        raise ToolError("Sintaxe inválida") from None
    return f"{result:.10g}"

class Workspace:
    """Acesso a arquivos restrito a uma pasta (bloqueia ../ e links para fora)."""

    def __init__(self, root: Path, max_chars: int = 20_000):
        self.root = root.resolve()
        self.max_chars = max_chars

    def _resolve(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ToolError("Caminho fora do workspace")
        return path

    def list_files(self) -> str:
        files = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())
        return "\n".join(files) or "(vazio)"

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"Arquivo não encontrado: {path}")
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > self.max_chars:
            return text[: self.max_chars] + f"\n... [truncado em {self.max_chars} caracteres]"
        return text

    def search_text(self, query: str) -> str:
        needle = query.lower()
        found = []
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if needle in line.lower():
                    found.append(f"{p.relative_to(self.root)}:{n}: {line.strip()}")
        return "\n".join(found[:50]) or "Nenhuma ocorrência."

def tool_schemas() -> list[dict]:
    def schema(name, description, props, required):
        return {
            "name": name,
            "description": description,
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            },
        }

    return [
        schema("calculate", "Calcula uma expressão aritmética. Use SEMPRE para contas, nunca calcule de cabeça.",
               {"expression": {"type": "string", "description": "Ex.: (120*49.90)+(60*129)"}}, ["expression"]),
        schema("list_files", "Lista os arquivos disponíveis no workspace.", {}, []),
        schema("read_file", "Lê o conteúdo de um arquivo do workspace.",
               {"path": {"type": "string", "description": "Caminho relativo, ex.: vendas_q3.csv"}}, ["path"]),
        schema("search_text", "Busca um texto (sem diferenciar maiúsculas) em todos os arquivos.",
               {"query": {"type": "string"}}, ["query"]),
    ]

def build_registry(workspace: Workspace) -> dict:
    return {
        "calculate": lambda a: calculate(a["expression"]),
        "list_files": lambda a: workspace.list_files(),
        "read_file": lambda a: workspace.read_file(a["path"]),
        "search_text": lambda a: workspace.search_text(a["query"]),
    }
