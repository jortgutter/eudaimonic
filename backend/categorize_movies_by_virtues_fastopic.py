"""
FASTopic-based Movie Categorization by Virtues.

This script mirrors the BERTopic pipeline, but uses FASTopic to discover topics
and then maps those topics onto six virtue categories:
wisdom, humanity, purpose, justice, restraint, courage.

Dependencies:
  pip install fastopic topmost sentence-transformers pandas numpy seaborn matplotlib

Run from the backend folder:
  python3 categorize_movies_by_virtues_fastopic.py
"""

import os
import re
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sentence_transformers import SentenceTransformer, util

try:
    from fastopic import FASTopic
except Exception as exc:
    FASTopic = None
    FASTOPIC_IMPORT_ERROR = exc
else:
    FASTOPIC_IMPORT_ERROR = None

try:
    from topmost.preprocess import Preprocess
except Exception:
    try:
        from topmost import Preprocess
    except Exception as exc:
        Preprocess = None
        PREPROCESS_IMPORT_ERROR = exc
    else:
        PREPROCESS_IMPORT_ERROR = None
else:
    PREPROCESS_IMPORT_ERROR = None

DB_PATH = Path("movies.db")
EMB_MODEL_NAME = "all-MiniLM-L6-v2"
MAX_DOCS = None
NUM_TOPICS = 50
LOW_MEMORY = True
LOW_MEMORY_BATCH_SIZE = 2000
EPOCHS = 80
LEARNING_RATE = 0.01
DT_ALPHA = 10.0
NORMALIZE_EMBEDDINGS = True
RANDOM_SEED = 42

TOPIC_PROB_GAMMA = 1.6
VIRTUE_SIM_TEMPERATURE = 0.45
FINAL_SCORE_GAMMA = 1.15

VIRTUE_CATEGORIES = {
    "wisdom": "Knowledge learning intelligence understanding truth insight reflection guidance discernment study scholarship wisdom judgment curiosity planning strategy",
    "humanity": "Compassion empathy kindness care connection helping forgiveness support friendship warmth tenderness mercy generosity family community solidarity love",
    "purpose": "Meaning goal mission direction fulfillment destiny calling ambition quest growth journey intention resolve aspiration meaningfully purposeful contribution",
    "justice": "Fairness equality rights morality law accountability ethics judgment responsibility justice fairness truth integrity punishment innocence balance rule order",
    "restraint": "Self-control discipline moderation patience balance restraint temperance composure humility limits boundaries caution delay sacrifice self-discipline",
    "courage": "Bravery strength determination risk heroism courage defiance perseverance resistance sacrifice protect confront fight survive endure bold fearless",
}


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\S*@\S*\s?", "", text)
    text = re.sub(r"'", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 400) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0]


def load_movies_and_reviews(limit=None):
    conn = sqlite3.connect(DB_PATH)

    movies_q = """
    SELECT m.id, m.title, m.summary
    FROM movies m
    WHERE m.summary IS NOT NULL AND m.summary != ''
    """
    movies_df = pd.read_sql_query(movies_q, conn)

    reviews_q = """
    SELECT movie_id, review_text
    FROM reviews
    WHERE movie_id IN (SELECT id FROM movies WHERE summary IS NOT NULL)
    """
    reviews_df = pd.read_sql_query(reviews_q, conn)

    genres_q = """
    SELECT mg.movie_id, GROUP_CONCAT(g.name, ' | ') AS genre_text
    FROM movie_genres mg
    JOIN genres g ON g.id = mg.genre_id
    GROUP BY mg.movie_id
    """
    genres_df = pd.read_sql_query(genres_q, conn)

    keywords_q = """
    SELECT mk.movie_id, GROUP_CONCAT(k.name, ' | ') AS keyword_text
    FROM movie_keywords mk
    JOIN keywords k ON k.id = mk.keyword_id
    GROUP BY mk.movie_id
    """
    keywords_df = pd.read_sql_query(keywords_q, conn)

    related_q = """
    SELECT movie_id, title, overview
    FROM (
        SELECT movie_id, title, overview, 'similar' AS source, ROW_NUMBER() OVER (PARTITION BY movie_id ORDER BY similar_movie_id) AS rn
        FROM similar_movies
        UNION ALL
        SELECT movie_id, title, overview, 'recommended' AS source, ROW_NUMBER() OVER (PARTITION BY movie_id ORDER BY recommended_movie_id) AS rn
        FROM recommended_movies
    )
    WHERE rn <= 3
    """
    related_df = pd.read_sql_query(related_q, conn)
    conn.close()

    if limit:
        movies_df = movies_df.head(limit)

    return movies_df, reviews_df, genres_df, keywords_df, related_df


def combine_documents(movies_df, reviews_df, genres_df, keywords_df, related_df):
    movie_texts = {}
    for _, row in movies_df.iterrows():
        movie_texts[row["id"]] = [row["summary"] or ""]

    for _, review in reviews_df.iterrows():
        movie_id = review["movie_id"]
        movie_texts.setdefault(movie_id, [])
        if pd.notna(review["review_text"]):
            movie_texts[movie_id].append(review["review_text"])

    genres_lookup = dict(zip(genres_df["movie_id"], genres_df["genre_text"])) if not genres_df.empty else {}
    keywords_lookup = dict(zip(keywords_df["movie_id"], keywords_df["keyword_text"])) if not keywords_df.empty else {}

    related_lookup = {}
    if not related_df.empty:
        for movie_id, group in related_df.groupby("movie_id"):
            snippets = []
            for _, rel in group.iterrows():
                title = rel.get("title") or ""
                overview = truncate_text(preprocess_text(rel.get("overview") or ""), 180)
                if title or overview:
                    snippets.append(f"related {title} {overview}".strip())
            related_lookup[movie_id] = " ".join(snippets)

    ids, titles, docs = [], [], []
    for _, row in movies_df.iterrows():
        movie_id = row["id"]
        combined = " ".join(
            [
                " ".join(movie_texts.get(movie_id, [])[:6]),
                f"genres {genres_lookup.get(movie_id, '')}" if genres_lookup.get(movie_id, "") else "",
                f"keywords {keywords_lookup.get(movie_id, '')}" if keywords_lookup.get(movie_id, "") else "",
                related_lookup.get(movie_id, ""),
            ]
        )
        cleaned = preprocess_text(combined)
        if len(cleaned) < 20:
            continue
        ids.append(movie_id)
        titles.append(row["title"])
        docs.append(cleaned)

    return pd.DataFrame({"id": ids, "title": titles, "doc": docs})


def format_topic_words(topic_words):
    if not topic_words:
        return ""
    if isinstance(topic_words[0], tuple):
        return " ".join(word for word, _ in topic_words)
    return " ".join(str(word) for word in topic_words)


def compute_topic_virtue_matrix(top_words, embedder):
    virtue_keys = list(VIRTUE_CATEGORIES.keys())
    virtue_emb = embedder.encode(list(VIRTUE_CATEGORIES.values()), convert_to_tensor=True)

    sim_rows = []
    for topic_idx, topic_words in enumerate(top_words):
        topic_text = format_topic_words(topic_words)
        if not topic_text.strip():
            sims = np.ones(len(virtue_keys), dtype=float) / len(virtue_keys)
        else:
            topic_emb = embedder.encode(topic_text, convert_to_tensor=True)
            sims = util.cos_sim(topic_emb, virtue_emb)[0].cpu().numpy()
            sims = np.clip((sims + 1.0) / 2.0, 0.0, 1.0)
            logits = np.log(sims + 1e-9) / VIRTUE_SIM_TEMPERATURE
            logits = logits - np.max(logits)
            sims = np.exp(logits)
            sims = sims / (np.sum(sims) + 1e-9)
        sim_rows.append(sims)

    sim_matrix = np.vstack(sim_rows)
    print("\n=== FASTopic topic->virtue matrix ===")
    print(f"Shape: {sim_matrix.shape}")
    print(f"First row sum: {sim_matrix[0].sum():.6f}")
    return virtue_keys, sim_matrix


def save_results_to_db(result_df: pd.DataFrame, table_name: str = "movie_virtues_fastopic"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    extra_cols = [c for c in result_df.columns if c.endswith("_score") and c != "primary_virtue_score"]
    cols_sql = ",\n".join([f"{c} REAL" for c in extra_cols])
    create_sql = f"""
        CREATE TABLE {table_name} (
            movie_id INTEGER PRIMARY KEY,
            primary_virtue TEXT,
            primary_virtue_score REAL,
            {cols_sql}
        )
    """
    conn.execute(create_sql)

    for _, row in result_df.iterrows():
        movie_id = int(row["id"])
        primary_virtue = row.get("primary_virtue", "unknown") or "unknown"
        primary_score = float(row.get("primary_virtue_score", 0.0) or 0.0)
        values = [float(row.get(col, 0.0) or 0.0) for col in extra_cols]
        placeholders = ",".join(["?"] * (3 + len(values)))
        sql = f"INSERT INTO {table_name} (movie_id, primary_virtue, primary_virtue_score{',' if values else ''} {','.join(extra_cols) if extra_cols else ''}) VALUES ({placeholders})"
        conn.execute(sql, (movie_id, primary_virtue, primary_score, *values) if values else (movie_id, primary_virtue, primary_score))

    conn.commit()
    conn.close()


def plot_topic_distribution(topics, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    counts = pd.Series(topics).value_counts().sort_values(ascending=False)
    plt.figure(figsize=(10, 8))
    sns.barplot(y=counts.index.astype(str)[:50], x=counts.values[:50], palette="viridis")
    plt.title("Top 50 FASTopic Topic Counts")
    plt.xlabel("Count")
    plt.ylabel("Topic")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "fastopic_topic_distribution.png"), dpi=160)
    plt.close()


def plot_topic_virtue_heatmap(sim_matrix, virtue_keys, out_dir, max_rows=50):
    os.makedirs(out_dir, exist_ok=True)
    rows = min(max_rows, sim_matrix.shape[0])
    df = pd.DataFrame(sim_matrix[:rows, :], columns=virtue_keys)
    df.index = [str(i) for i in range(rows)]
    plt.figure(figsize=(8, max(4, rows * 0.2)))
    sns.heatmap(df, cmap="YlGnBu", cbar_kws={"label": "Affinity"})
    plt.xlabel("Virtue")
    plt.ylabel("Topic")
    plt.title(f"FASTopic Topic -> Virtue Affinity (first {rows} topics)")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "fastopic_topic_virtue_heatmap.png"), dpi=160)
    plt.close()


def main():
    if FASTopic is None:
        raise ImportError(f"fastopic is not installed: {FASTOPIC_IMPORT_ERROR}")
    if Preprocess is None:
        raise ImportError(f"topmost is not installed: {PREPROCESS_IMPORT_ERROR}")

    print("Loading data...")
    movies_df, reviews_df, genres_df, keywords_df, related_df = load_movies_and_reviews(limit=MAX_DOCS)
    doc_df = combine_documents(movies_df, reviews_df, genres_df, keywords_df, related_df)
    print(f"Documents prepared: {len(doc_df)}")

    if doc_df.empty:
        print("No documents to process. Exiting.")
        return

    print("Loading embedding model...")
    embedder = SentenceTransformer(EMB_MODEL_NAME)

    print("Building FASTopic preprocesser...")
    preprocess = Preprocess(vocab_size=10000)

    print("Fitting FASTopic...")
    np.random.seed(RANDOM_SEED)
    model = FASTopic(
        NUM_TOPICS,
        preprocess=preprocess,
        doc_embed_model=embedder,
        low_memory=LOW_MEMORY,
        low_memory_batch_size=LOW_MEMORY_BATCH_SIZE,
        DT_alpha=DT_ALPHA,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        verbose=True,
    )

    top_words, doc_topic_dist = model.fit_transform(doc_df["doc"].tolist(), epochs=EPOCHS, learning_rate=LEARNING_RATE)
    doc_topic_dist = np.asarray(doc_topic_dist)
    print(f"Top words discovered: {len(top_words)}")
    print(f"Document-topic matrix shape: {doc_topic_dist.shape}")

    virtue_keys, topic_virtue_matrix = compute_topic_virtue_matrix(top_words, embedder)

    topic_ids = list(range(doc_topic_dist.shape[1]))
    result = doc_df.copy()

    topic_weights = np.power(np.clip(doc_topic_dist, 0.0, 1.0), TOPIC_PROB_GAMMA)
    topic_weight_sums = topic_weights.sum(axis=1, keepdims=True)
    topic_weights = np.divide(topic_weights, topic_weight_sums, out=np.zeros_like(topic_weights), where=topic_weight_sums > 0)

    virtue_scores = topic_weights.dot(topic_virtue_matrix)
    virtue_scores = np.power(np.clip(virtue_scores, 0.0, 1.0), FINAL_SCORE_GAMMA)

    result["topic"] = np.argmax(doc_topic_dist, axis=1)
    for col_idx, virtue_key in enumerate(virtue_keys):
        result[f"{virtue_key}_score"] = virtue_scores[:, col_idx]

    virtue_cols = [f"{vk}_score" for vk in virtue_keys]
    score_sums = result[virtue_cols].sum(axis=1).replace(0, np.nan)
    for col in virtue_cols:
        result[col] = result[col].divide(score_sums).fillna(0.0)

    for col in virtue_cols:
        result[col] = np.power(np.clip(result[col], 0.0, 1.0), FINAL_SCORE_GAMMA)
    score_sums = result[virtue_cols].sum(axis=1).replace(0, np.nan)
    for col in virtue_cols:
        result[col] = result[col].divide(score_sums).fillna(0.0)

    result["primary_virtue"] = result[virtue_cols].idxmax(axis=1).str.replace("_score", "", regex=False)
    result["primary_virtue_score"] = result[virtue_cols].max(axis=1)

    print("\n=== FASTopic topic distribution ===")
    print(result["topic"].value_counts().head(15))
    print("\nSample categorized movies:")
    print(result[["title", "primary_virtue", "primary_virtue_score"] + virtue_cols].head(20))

    out_dir = os.path.join(os.path.dirname(__file__), "plots_fastopic")
    try:
        plot_topic_distribution(np.argmax(doc_topic_dist, axis=1), out_dir)
        plot_topic_virtue_heatmap(topic_virtue_matrix, virtue_keys, out_dir, max_rows=50)
        print(f"Visualisations saved to: {out_dir}")
    except Exception as exc:
        print(f"Visualization generation failed: {exc}")

    save_results_to_db(result[["id", "primary_virtue", "primary_virtue_score"] + virtue_cols])
    print(f"Results saved to {DB_PATH}")


if __name__ == "__main__":
    main()
