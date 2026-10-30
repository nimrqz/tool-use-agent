# Agente com ferramentas

Um agente que recebe uma pergunta e decide sozinho quais ferramentas usar: listar e ler arquivos de uma pasta (`workspace/`), buscar texto e fazer contas. Na interface dá para ver cada ferramenta que ele chamou.

Exemplo: "Qual produto gerou mais receita no Q3 e o trimestre bateu a meta das notas da reunião?"

## Como rodar

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python cli.py "Qual produto gerou mais receita no Q3?"
streamlit run app.py
python -m pytest tests
```

## O que tem

- O loop do agente está em `tool_agent/agent.py`, escrito sem framework: chama o modelo, executa as ferramentas pedidas, devolve os resultados e repete até ele responder.
- Tem limite de passos para não ficar em loop infinito.
- Se uma ferramenta der erro, o erro volta para o modelo e ele tenta de outro jeito.
- A calculadora não usa `eval` (usa o módulo `ast`), e a leitura de arquivos não deixa sair da pasta `workspace`.
- Opção `--web` para buscar na internet.

Os 12 testes cobrem o loop, os erros de ferramenta, o limite de passos, a calculadora e a proteção da pasta de arquivos.

## Próximos passos

- Criar um conjunto de tarefas com respostas esperadas para medir o agente
- Pedir confirmação do usuário antes de ferramentas mais sensíveis
