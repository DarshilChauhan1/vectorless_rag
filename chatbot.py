import os
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# CONFIG — update these two lines
# ─────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("CHATGPT_API_KEY")
PDF_PATH       = "PDF_PATH"   # path to the PDF you indexed
TREE_PATH      = "./results/PDF_PATH"         # your generated PageIndex tree
MODEL          = "gpt-5.1"              # or "gpt-4o-mini" for cheaper/faster
# ─────────────────────────────────────────────

from openai import OpenAI
if not OPENAI_API_KEY:
    raise EnvironmentError(
        "Missing API key. Set OPENAI_API_KEY (preferred) or CHATGPT_API_KEY in your shell or .env file."
    )
client = OpenAI(api_key=OPENAI_API_KEY)


# ── Load the PageIndex tree ───────────────────
def load_tree(path: str) -> list:
    with open(path, "r") as f:
        data = json.load(f)
    # Handle {"structure": [...]}, {"result": [...]}, and plain list formats
    if isinstance(data, dict) and "structure" in data:
        return data["structure"]
    if isinstance(data, dict) and "result" in data:
        return data["result"]
    return data


# ── Recursively find a node by ID ────────────
def find_node(tree, node_id: str):
    nodes = tree if isinstance(tree, list) else [tree]
    for node in nodes:
        if node.get("node_id") == node_id:
            return node
        for child_key in ("nodes", "structure"):
            if child_key in node and isinstance(node[child_key], list):
                result = find_node(node[child_key], node_id)
                if result:
                    return result
    return None


# ── Strip heavy fields to keep tree prompt small ──
def strip_text_fields(obj):
    if isinstance(obj, list):
        return [strip_text_fields(i) for i in obj]
    if isinstance(obj, dict):
        return {
            k: strip_text_fields(v)
            for k, v in obj.items()
            if k not in ("text", "content")
        }
    return obj


# ── Extract text from PDF page range ─────────
def fetch_pages(pdf_path: str, start: int, end: int) -> str:
    doc = fitz.open(pdf_path)
    total = len(doc)
    text = ""
    for i in range(start, min(end + 1, total)):
        page_text = doc[i].get_text().strip()
        if page_text:
            text += f"\n[Page {i + 1}]\n{page_text}\n"
    return text.strip()


# ── Step 1: LLM reasons over tree → returns node IDs ──
def tree_search(question: str, tree: list) -> list[str]:
    slim_tree = strip_text_fields(tree)

    prompt = f"""You are a document retrieval assistant.
You are given a question and a hierarchical tree index of a document.
Each node has a node_id, title, and summary describing what that section covers.

Your task: identify ALL node_ids whose sections are likely to contain
information needed to answer the question.

Question: {question}

Document tree:
{json.dumps(slim_tree, indent=2)}

Reply ONLY with valid JSON in this exact format:
{{
    "thinking": "<brief reasoning about which sections are relevant>",
    "node_list": ["node_id_1", "node_id_2"]
}}
Do not output anything else."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    thinking  = result.get("thinking", "")
    node_list = result.get("node_list", [])

    print(f"\n  [Tree search thinking]\n  {thinking[:300]}{'...' if len(thinking) > 300 else ''}")
    print(f"  [Matched nodes] {node_list}")
    return node_list


# ── Step 2: Fetch page text for matched nodes ──
def fetch_context(node_ids: list[str], tree: list, pdf_path: str) -> str:
    print(f"  Fetching content for nodes: {node_ids}")
    context_parts = []

    for nid in node_ids:
        node = find_node(tree, nid)
        if not node:
            print(f"  [Warning] Node {nid} not found in tree, skipping.")
            continue

        title      = node.get("title", "Untitled")
        start      = node.get("start_index", 0)
        end        = node.get("end_index", start)
        summary    = node.get("summary", "")

        page_text  = fetch_pages(pdf_path, start, end)

        section = (
            f"=== Section: {title} (Pages {start + 1}–{end + 1}) ===\n"
            f"Summary: {summary}\n\n"
            f"{page_text}"
        )
        context_parts.append(section)

    return "\n\n".join(context_parts) if context_parts else "No relevant content found."


# ── Step 3: Generate final answer ────────────
def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are a helpful document assistant.
Answer the user's question using ONLY the context provided below.
- Be concise and accurate.
- Always cite the section name and page numbers where you found the answer.
- If the context does not contain enough information, say so clearly.

Context:
{context}

Question: {question}

Answer:"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()


# ── Full RAG pipeline ─────────────────────────
def ask(question: str, tree: list, pdf_path: str) -> str:
    print("\n[Step 1] Searching tree index...")
    node_ids = tree_search(question, tree)

    if not node_ids:
        return "I could not find any relevant sections in the document for your question."

    print(f"\n[Step 2] Fetching content from {len(node_ids)} node(s)...")
    context = fetch_context(node_ids, tree, pdf_path)
    print(f"\n[Context fetched] length={len(context)} characters")
    print("[Context]")
    print(context)
    print("[End Context]")

    print("\n[Step 3] Generating answer...")
    answer = generate_answer(question, context)
    return answer


# ── Main chatbot loop ─────────────────────────
def main():
    print("=" * 55)
    print("  PageIndex Document Q&A Bot (Open-source)")
    print("=" * 55)

    # Validate files exist
    if not os.path.exists(TREE_PATH):
        print(f"\n[Error] Tree file not found: {TREE_PATH}")
        print("Run: python3 run_pageindex.py --pdf_path your_document.pdf")
        return

    if not os.path.exists(PDF_PATH):
        print(f"\n[Error] PDF not found: {PDF_PATH}")
        return

    tree = load_tree(TREE_PATH)
    print(f"\nLoaded tree: {len(tree)} top-level nodes")
    print(f"PDF: {PDF_PATH}")
    print("\nType your question, or 'quit' to exit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        answer = ask(question, tree, PDF_PATH)
        print(f"\nBot: {answer}\n")
        print("-" * 55)


if __name__ == "__main__":
    main()