from pathlib import Path

import streamlit as st

from tool_agent.agent import Agent
from tool_agent.tools import Workspace

st.set_page_config(page_title="Agente com ferramentas", page_icon="🛠️")
st.title("🛠️ Agente com ferramentas")
st.caption("Cada chamada de ferramenta aparece abaixo: dá para auditar como o agente chegou na resposta.")

web = st.sidebar.checkbox("Permitir busca na web", value=False)
max_steps = st.sidebar.slider("Máximo de passos", 2, 20, 10)
task = st.text_area(
    "Tarefa",
    "Qual produto gerou mais receita no Q3 e o trimestre bateu a meta mencionada nas notas da reunião?",
)

if st.button("Executar", type="primary") and task.strip():
    log = st.container()

    def show(step):
        with log.expander(f"{'❌' if step.is_error else '🔧'} {step.name}  {step.input}"):
            st.code(step.output)

    agent = Agent(Workspace(Path(__file__).parent / "workspace"), max_steps=max_steps,
                  use_web_search=web, on_step=show)
    with st.spinner("Trabalhando..."):
        result = agent.run(task)
    st.subheader("Resposta")
    st.markdown(result.answer)
    st.caption(f"{result.steps} passos · {result.input_tokens} tokens in · {result.output_tokens} out")
