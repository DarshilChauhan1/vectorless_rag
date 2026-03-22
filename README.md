# Vectorless RAG Setup Guide

This guide shows how to:
- Clone this repo
- Clone the `PageIndex` repo
- Copy `chatbot.py`
- Set PDF/tree paths
- Run `run_pageindex.py` first, then `chatbot.py`

## 1) Clone this repository

```zsh
git clone https://github.com/DarshilChauhan1/vectorless_rag.git
cd vectorless_rag
```

## 2) Clone PageIndex inside this repo

```zsh
git clone https://github.com/VectifyAI/PageIndex.git PageIndex
```

## 3) Enter `PageIndex` and install dependencies

```zsh
cd PageIndex
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install openai
```

## 4) Set your API key

Create a `.env` file in `PageIndex/`:

```env
OPENAI_API_KEY=your_openai_key_here
```

(`CHATGPT_API_KEY` also works in this project, but `OPENAI_API_KEY` is preferred.)

## 5) Add/copy `chatbot.py`

Place your chatbot script at:

```text
PageIndex/chatbot.py
```

## 6) Set paths in `chatbot.py`

Update these values in `PageIndex/chatbot.py`:

```python
PDF_PATH = "./your-document.pdf"
TREE_PATH = "./results/your-document_structure.json"
```

Example:

```python
PDF_PATH = "./69496235abd9b-mistress-wilding-by-rafael-sabatini.pdf"
TREE_PATH = "./results/69496235abd9b-mistress-wilding-by-rafael-sabatini_structure.json"
```

## 7) Run PageIndex first (generate tree)

```zsh
python run_pageindex.py --pdf_path ./69496235abd9b-mistress-wilding-by-rafael-sabatini.pdf
```

This creates a tree JSON in `PageIndex/results/`.

## 8) Run chatbot second

```zsh
python chatbot.py
```

## Run order (important)

1. `python run_pageindex.py --pdf_path ...`
2. `python chatbot.py`
