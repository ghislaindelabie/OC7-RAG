#!/usr/bin/env python3
"""
Test script for the baseline RAG system.
Executes all notebook cells to verify functionality.
"""

import json
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from langchain.docstore.document import Document
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

print("="*60)
print("BASELINE RAG SYSTEM TEST")
print("="*60)

# ============================================================
# Cell 1: Setup & Imports
# ============================================================
print("\n[Cell 1] Setup & Imports")
print("-"*60)

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in environment. Please check your .env file.")

print("✓ All imports successful")
print(f"✓ Mistral API key loaded (length: {len(MISTRAL_API_KEY)} characters)")

# ============================================================
# Cell 2: Load and Explore Data
# ============================================================
print("\n[Cell 2] Load and Explore Data")
print("-"*60)

DATA_PATH = Path("data/processed/events_filtered.json")

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    events = json.load(f)

print(f"Total events loaded: {len(events):,}")

df = pd.DataFrame(events)

print("\nDepartment Distribution:")
print(df['location_department'].value_counts())

df['firstdate_begin_dt'] = pd.to_datetime(df['firstdate_begin'], errors='coerce')
print(f"\nDate Range:")
print(f"  Earliest: {df['firstdate_begin_dt'].min()}")
print(f"  Latest: {df['firstdate_begin_dt'].max()}")

print("\nTop 10 Categories:")
print(df['category'].value_counts().head(10))

# ============================================================
# Cell 3: Data Preprocessing
# ============================================================
print("\n[Cell 3] Data Preprocessing")
print("-"*60)

def clean_html(html_text):
    """Remove HTML tags from text."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, 'lxml')
    return soup.get_text(separator=' ', strip=True)


def build_document_text(event):
    """Build comprehensive document text from event data."""
    parts = []

    title = event.get('title_fr', '')
    if title:
        parts.append(f"Événement: {title}")

    long_desc = clean_html(event.get('longdescription_fr', ''))
    short_desc = event.get('description_fr', '')
    description = long_desc if long_desc else short_desc
    if description:
        parts.append(f"Description: {description}")

    city = event.get('location_city', '')
    location_name = event.get('location_name', '')
    address = event.get('location_address', '')
    department = event.get('location_department', '')

    location_parts = []
    if location_name:
        location_parts.append(location_name)
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if department:
        location_parts.append(department)

    if location_parts:
        parts.append(f"Lieu: {', '.join(location_parts)}")

    daterange = event.get('daterange_fr', '')
    if daterange:
        parts.append(f"Date: {daterange}")

    category = event.get('category', '')
    if category:
        parts.append(f"Catégorie: {category}")

    keywords = event.get('keywords_fr', '')
    if keywords:
        parts.append(f"Mots-clés: {keywords}")

    return '\n'.join(parts)


documents = []

for event in events:
    doc_text = build_document_text(event)

    metadata = {
        'title': event.get('title_fr', ''),
        'city': event.get('location_city', ''),
        'department': event.get('location_department', ''),
        'category': event.get('category', ''),
        'daterange': event.get('daterange_fr', ''),
        'firstdate': event.get('firstdate_begin', ''),
    }

    documents.append(Document(page_content=doc_text, metadata=metadata))

print(f"✓ Created {len(documents):,} documents")
print("\nSample document (first 300 chars):")
print(documents[0].page_content[:300])
print("...")

# ============================================================
# Cell 4: Embedding Setup
# ============================================================
print("\n[Cell 4] Embedding Setup")
print("-"*60)

embeddings = MistralAIEmbeddings(
    model="mistral-embed",
    api_key=MISTRAL_API_KEY
)

test_text = "Concert de musique classique à Annecy"
print(f"Testing embeddings with: '{test_text}'")
test_embedding = embeddings.embed_query(test_text)

print(f"✓ Embeddings initialized")
print(f"✓ Test embedding generated")
print(f"  - Embedding dimension: {len(test_embedding)}")
print(f"  - First 5 values: {test_embedding[:5]}")

# ============================================================
# Cell 5: FAISS Index Creation
# ============================================================
print("\n[Cell 5] FAISS Index Creation")
print("-"*60)
print("Creating FAISS index... This may take a few minutes.")
print(f"Processing {len(documents):,} documents...")

vectorstore = FAISS.from_documents(documents, embeddings)

INDEX_PATH = "data/index/faiss_baseline"
Path(INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
vectorstore.save_local(INDEX_PATH)

print(f"\n✓ FAISS index created successfully")
print(f"✓ Index saved to: {INDEX_PATH}")
print(f"  - Number of documents indexed: {len(documents):,}")

test_query = "concerts à Annecy"
test_results = vectorstore.similarity_search(test_query, k=3)

print(f"\nTest retrieval for query: '{test_query}'")
print(f"Retrieved {len(test_results)} documents")
print("\nTop result:")
print(test_results[0].page_content[:200])
print(f"\nMetadata: {test_results[0].metadata}")

# ============================================================
# Cell 6: RAG Chain Setup
# ============================================================
print("\n[Cell 6] RAG Chain Setup")
print("-"*60)

llm = ChatMistralAI(
    model="mistral-small-latest",
    api_key=MISTRAL_API_KEY,
    temperature=0.1
)

prompt_template = """Tu es un assistant spécialisé dans les événements culturels de Savoie, Haute-Savoie et Isère.
Utilise les informations suivantes pour répondre à la question de l'utilisateur.
Si tu ne trouves pas l'information dans le contexte, dis-le clairement.

Contexte:
{context}

Question: {question}

Réponse détaillée:"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)

retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"prompt": PROMPT}
)

print("✓ RAG chain initialized successfully")
print(f"  - LLM: mistral-small-latest")
print(f"  - Retriever: similarity search (k=5)")
print(f"  - Chain type: stuff")

# ============================================================
# Cell 7: Testing & Validation
# ============================================================
print("\n[Cell 7] Testing & Validation")
print("-"*60)

test_queries = [
    "Quels concerts ont lieu à Annecy?",
    "Événements pour enfants à Grenoble",
]

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*60}")
    print(f"TEST QUERY {i}: {query}")
    print(f"{'='*60}")

    result = qa_chain.invoke({"query": query})

    print("\nRÉPONSE:")
    print(result['result'])

    print(f"\nSOURCES ({len(result['source_documents'])} documents):")
    for j, doc in enumerate(result['source_documents'][:3], 1):
        print(f"\n  {j}. {doc.metadata.get('title', 'N/A')}")
        print(f"     Lieu: {doc.metadata.get('city', 'N/A')}, {doc.metadata.get('department', 'N/A')}")
        print(f"     Date: {doc.metadata.get('daterange', 'N/A')}")

print("\n" + "="*60)
print("TEST COMPLETE - All cells executed successfully!")
print("="*60)
