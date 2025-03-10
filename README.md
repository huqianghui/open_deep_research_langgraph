https://github.com/langchain-ai/open_deep_research?tab=readme-ov-file#quickstart

## 1. terminal go to the open_deep_research_langgraph folder
## 2. Edit the .env file with your API keys (e.g., the API keys for default selections are shown below):
   cp .env.example .env

## 3. Windows
# Install dependencies 
python.exe -m pip install --upgrade pip
pip install -e .
pip install langgraph-cli[inmem]

# Start the LangGraph server
langgraph dev

## 3. Mac

pip install -e .
pip install "langgraph-cli[inmem]"

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and start the LangGraph server
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev

## 4. Use this to open the Studio UI:

- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
please follow web-operation-mannual.ipynb

- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs


