import argparse
import json
from pathlib import Path

from tool_agent.agent import Agent
from tool_agent.tools import Workspace

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("--workspace", type=Path, default=Path(__file__).parent / "workspace")
    parser.add_argument("--web", action="store_true", help="habilita busca na web")
    parser.add_argument("--max-steps", type=int, default=10)
    args = parser.parse_args()

    def show(step):
        flag = " (ERRO)" if step.is_error else ""
        print(f"→ {step.name}({json.dumps(step.input, ensure_ascii=False)}){flag}\n  {step.output[:200]}")

    agent = Agent(Workspace(args.workspace), max_steps=args.max_steps, use_web_search=args.web, on_step=show)
    result = agent.run(args.task)
    print(f"\n{result.answer}\n\n[{result.steps} passos, {result.input_tokens} tokens in / {result.output_tokens} out]")

if __name__ == "__main__":
    main()
