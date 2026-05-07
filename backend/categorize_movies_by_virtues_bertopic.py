"""
BERTopic-based Movie Categorization by Virtues

Dependencies (install into your venv):
pip install pandas bertopic[all] sentence-transformers transformers torch

This script:
- Loads movies and reviews from movies.db
- Combines summary, reviews, genres, keywords, and related-movie metadata into documents
- Fits BERTopic with a SentenceTransformer embedding model
- Assigns each discovered topic to the best-matching virtue by embedding similarity
- Assigns each movie the virtue of its topic and writes results to `movie_virtues_bertopic`

Notes:
- For speed, consider sampling documents or using a faster embedding model.
"""

import sqlite3
import re
from pathlib import Path
from typing import List

import pandas as pd
import numpy as np

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline

# Config
DB_PATH = Path('movies.db')
EMB_MODEL_NAME = 'all-MiniLM-L6-v2'  # small + fast; change if you prefer
MAX_DOCS = None  # set to an int to limit documents for quicker iteration
TOPIC_PROB_GAMMA = 1.8  # >1 sharpens topic probability distributions
VIRTUE_SIM_TEMPERATURE = 0.35  # lower values make topic->virtue mapping more peaked
TOP_K_TOPICS = 3  # only the strongest topics contribute to each document's virtue score
FINAL_SCORE_GAMMA = 1.15  # slightly sharpen final per-movie virtue distribution
USE_ZERO_SHOT_TOPIC_SCORING = True
ZERO_SHOT_MODEL_NAME = 'facebook/bart-large-mnli'
ZERO_SHOT_HYPOTHESIS_TEMPLATE = 'This topic is about {}.'
ZERO_SHOT_BATCH_SIZE = 8
TOPIC_REPR_WORDS = 12
TOPIC_REPR_DOCS = 2
TOPIC_REPR_DOC_CHARS = 220

# BERTopic tuning to reduce topic -1 outliers
BERTOPIC_MIN_TOPIC_SIZE = 5  # lower = more topics, fewer outliers (try 3-10)
BERTOPIC_N_GRAM_RANGE = (1, 2)  # unigrams + bigrams for better matching
BERTOPIC_TOP_N_WORDS = 10  # number of top words per topic
REDUCE_OUTLIERS_AGGRESSIVE = True  # reassign -1 docs to nearest topic if any remain

VIRTUE_CATEGORIES = {
    'wisdom': 'Knowledge learning intelligence understanding truth insight reflection guidance discernment study scholarship wisdom judgment curiosity planning strategy',
    'humanity': 'Compassion empathy kindness care connection helping forgiveness support friendship warmth tenderness mercy generosity family community solidarity love',
    'purpose': 'Meaning goal mission direction fulfillment destiny calling ambition quest growth journey intention resolve aspiration meaningfully purposeful contribution',
    'justice': 'Fairness equality rights morality law accountability ethics judgment responsibility justice fairness truth integrity punishment innocence balance rule order',
    'restraint': 'Self-control discipline moderation patience balance restraint temperance composure humility limits boundaries caution delay sacrifice self-discipline',
    'courage': 'Bravery strength determination risk heroism courage defiance perseverance resistance sacrifice protect confront fight survive endure bold fearless'
}

VIRTUE_LABELS = {
    'wisdom': 'wisdom and understanding',
    'humanity': 'humanity and compassion',
    'purpose': 'purpose and meaning',
    'justice': 'justice and fairness',
    'restraint': 'restraint and self control',
    'courage': 'courage and bravery',
}

# Utility functions

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ''
    text = re.sub(r"\s+", ' ', text)
    text = re.sub(r"\S*@\S*\s?", '', text)
    text = re.sub(r"'", '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 400) -> str:
    if not isinstance(text, str):
        return ''
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0]


# Data loading

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
        movie_texts[row['id']] = [row['summary'] or '']

    for _, r in reviews_df.iterrows():
        mid = r['movie_id']
        if mid not in movie_texts:
            movie_texts[mid] = []
        if pd.notna(r['review_text']):
            movie_texts[mid].append(r['review_text'])

    genres_lookup = dict(zip(genres_df['movie_id'], genres_df['genre_text'])) if not genres_df.empty else {}
    keywords_lookup = dict(zip(keywords_df['movie_id'], keywords_df['keyword_text'])) if not keywords_df.empty else {}

    related_lookup = {}
    if not related_df.empty:
        for movie_id, grp in related_df.groupby('movie_id'):
            snippets = []
            for _, rel in grp.iterrows():
                title = rel.get('title') or ''
                overview = truncate_text(preprocess_text(rel.get('overview') or ''), 180)
                if title or overview:
                    snippets.append(f"related {title} {overview}".strip())
            related_lookup[movie_id] = ' '.join(snippets)

    ids, titles, docs = [], [], []
    for _, row in movies_df.iterrows():
        mid = row['id']
        text_parts = movie_texts.get(mid, [])
        genre_text = genres_lookup.get(mid, '')
        keyword_text = keywords_lookup.get(mid, '')
        related_text = related_lookup.get(mid, '')

        combined = ' '.join([
            ' '.join(text_parts[:6]),
            f'genres {genre_text}' if genre_text else '',
            f'keywords {keyword_text}' if keyword_text else '',
            related_text,
        ])
        cleaned = preprocess_text(combined)
        if len(cleaned) < 20:
            continue
        ids.append(mid)
        titles.append(row['title'])
        docs.append(cleaned)

    df = pd.DataFrame({'id': ids, 'title': titles, 'doc': docs})
    return df


def topic_virtue_similarity_matrix(topic_model: BERTopic, embedder: SentenceTransformer):
    """Return matrix (n_topics x n_virtues) of cosine similarities between topic repr and virtue embeddings."""
    topics_info = topic_model.get_topic_info()
    topic_ids = list(topics_info['Topic'])

    virtue_texts = list(VIRTUE_CATEGORIES.values())
    virtue_keys = list(VIRTUE_CATEGORIES.keys())
    virtue_emb = embedder.encode(virtue_texts, convert_to_tensor=True)

    sim_matrix = []
    for topic_id in topic_ids:
        if topic_id == -1:
            # outlier topic: assign uniform distribution (equal affinity to all virtues)
            sims = np.ones(len(virtue_keys), dtype=float) / len(virtue_keys)
        else:
            topic_repr = topic_model.get_topic(topic_id)
            words = ' '.join([w for w, _ in topic_repr])
            if not words:
                sims = np.zeros(len(virtue_keys), dtype=float)
            else:
                emb = embedder.encode(words, convert_to_tensor=True)
                sims = util.cos_sim(emb, virtue_emb)[0].cpu().numpy()
                # shift cosine similarities from [-1, 1] to [0, 1]
                sims = np.clip((sims + 1.0) / 2.0, 0.0, 1.0)
                # sharpen topic->virtue affinities with temperature-scaled softmax
                logits = np.log(sims + 1e-9) / VIRTUE_SIM_TEMPERATURE
                logits = logits - np.max(logits)
                sims = np.exp(logits)
                sims = sims / (np.sum(sims) + 1e-9)
        sim_matrix.append(sims)

    sim_matrix = np.vstack(sim_matrix)  # shape (n_topics, n_virtues)
    
    # DEBUG: Print matrix statistics
    print('\n=== DEBUG: Similarity Matrix Stats ===')
    print(f'Shape: {sim_matrix.shape}')
    print(f'Min value: {sim_matrix.min():.6f}')
    print(f'Max value: {sim_matrix.max():.6f}')
    print(f'Mean value: {sim_matrix.mean():.6f}')
    print(f'Rows summing to ~0: {np.sum(np.abs(sim_matrix.sum(axis=1) - 0.0) < 0.01)}')
    print(f'Rows summing to ~1: {np.sum(np.abs(sim_matrix.sum(axis=1) - 1.0) < 0.01)}')
    print('First 5 row sums:', sim_matrix[:5].sum(axis=1))
    
    return topic_ids, virtue_keys, sim_matrix


def build_topic_description(topic_model: BERTopic, topic_id: int) -> str:
    topic_repr = topic_model.get_topic(topic_id) or []
    keywords = [w for w, _ in topic_repr[:TOPIC_REPR_WORDS]]

    rep_docs: List[str] = []
    try:
        docs = topic_model.get_representative_docs(topic_id) or []
        for d in docs[:TOPIC_REPR_DOCS]:
            cleaned = truncate_text(preprocess_text(d), TOPIC_REPR_DOC_CHARS)
            if cleaned:
                rep_docs.append(cleaned)
    except Exception:
        pass

    parts = []
    if keywords:
        parts.append(f"keywords: {', '.join(keywords)}")
    if rep_docs:
        parts.append('representative snippets: ' + ' || '.join(rep_docs))

    return '. '.join(parts).strip()


def topic_virtue_similarity_matrix_zero_shot(topic_model: BERTopic):
    """Return matrix (n_topics x n_virtues) from zero-shot classification over topic descriptions."""
    topics_info = topic_model.get_topic_info()
    topic_ids = list(topics_info['Topic'])

    virtue_keys = list(VIRTUE_CATEGORIES.keys())
    candidate_labels = [VIRTUE_LABELS.get(k, k) for k in virtue_keys]

    print(f'Loading zero-shot model: {ZERO_SHOT_MODEL_NAME}')
    classifier = pipeline('zero-shot-classification', model=ZERO_SHOT_MODEL_NAME)

    sim_lookup = {}
    active_topic_ids = []
    active_descriptions = []

    for topic_id in topic_ids:
        if topic_id == -1:
            continue
        desc = build_topic_description(topic_model, topic_id)
        if not desc:
            continue
        active_topic_ids.append(topic_id)
        active_descriptions.append(desc)

    if active_descriptions:
        for start in range(0, len(active_descriptions), ZERO_SHOT_BATCH_SIZE):
            batch_desc = active_descriptions[start:start + ZERO_SHOT_BATCH_SIZE]
            batch_topic_ids = active_topic_ids[start:start + ZERO_SHOT_BATCH_SIZE]

            outputs = classifier(
                batch_desc,
                candidate_labels=candidate_labels,
                hypothesis_template=ZERO_SHOT_HYPOTHESIS_TEMPLATE,
                multi_label=False,
            )
            if isinstance(outputs, dict):
                outputs = [outputs]

            for tid, out in zip(batch_topic_ids, outputs):
                score_map = dict(zip(out.get('labels', []), out.get('scores', [])))
                sims = np.array([float(score_map.get(lbl, 0.0)) for lbl in candidate_labels], dtype=float)
                sims_sum = float(np.sum(sims))
                if sims_sum > 0:
                    sims = sims / sims_sum
                sim_lookup[tid] = sims

    sim_matrix = []
    for topic_id in topic_ids:
        if topic_id == -1:
            sims = np.ones(len(virtue_keys), dtype=float) / len(virtue_keys)
        else:
            sims = sim_lookup.get(topic_id)
            if sims is None:
                sims = np.ones(len(virtue_keys), dtype=float) / len(virtue_keys)
        sim_matrix.append(sims)

    sim_matrix = np.vstack(sim_matrix)

    print('\n=== DEBUG: Zero-Shot Similarity Matrix Stats ===')
    print(f'Shape: {sim_matrix.shape}')
    print(f'Min value: {sim_matrix.min():.6f}')
    print(f'Max value: {sim_matrix.max():.6f}')
    print(f'Mean value: {sim_matrix.mean():.6f}')
    print(f'Rows summing to ~1: {np.sum(np.abs(sim_matrix.sum(axis=1) - 1.0) < 0.01)}')
    print('First 5 row sums:', sim_matrix[:5].sum(axis=1))

    return topic_ids, virtue_keys, sim_matrix


def get_topic_virtue_matrix(topic_model: BERTopic, embedder: SentenceTransformer):
    if USE_ZERO_SHOT_TOPIC_SCORING:
        try:
            return topic_virtue_similarity_matrix_zero_shot(topic_model)
        except Exception as e:
            print(f'Zero-shot topic scoring failed, falling back to embedding similarity: {e}')
    return topic_virtue_similarity_matrix(topic_model, embedder)


def reassign_outliers_to_nearest_topic(doc_embeddings, topics, topic_model: BERTopic):
    """Reassign documents in topic -1 to the nearest non-outlier topic based on embedding similarity."""
    outlier_mask = topics == -1
    if not np.any(outlier_mask):
        print('No documents in topic -1; outlier reassignment skipped.')
        return topics
    
    outlier_indices = np.where(outlier_mask)[0]
    outlier_embeddings = doc_embeddings[outlier_indices]
    
    # Get topic embeddings (centroids) for non-outlier topics
    non_outlier_topics = np.unique(topics[~outlier_mask])
    topic_embeddings_dict = {}
    for tid in non_outlier_topics:
        if tid >= 0:
            mask = topics == tid
            centroids = np.mean(doc_embeddings[mask], axis=0)
            topic_embeddings_dict[tid] = centroids
    
    if not topic_embeddings_dict:
        print('No non-outlier topics found; cannot reassign.')
        return topics
    
    # Compute similarities and assign to nearest
    for idx in outlier_indices:
        outlier_emb = outlier_embeddings[idx - outlier_indices[0]]
        sims = {tid: float(util.cos_sim(outlier_emb, emb)) for tid, emb in topic_embeddings_dict.items()}
        nearest_topic = max(sims, key=sims.get)
        topics[idx] = nearest_topic
    
    print(f'Reassigned {len(outlier_indices)} outlier documents to nearest topics.')
    return topics


def save_results_to_db(result_df: pd.DataFrame, table_name: str = 'movie_virtues_bertopic'):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f'DROP TABLE IF EXISTS {table_name}')

    # create table with virtue score columns if provided
    extra_cols = [c for c in result_df.columns if c.endswith('_score') and c not in ('primary_virtue_score',)]
    cols_sql = ',\n'.join([f'{c} REAL' for c in extra_cols])
    create_sql = f'''
        CREATE TABLE {table_name} (
            movie_id INTEGER PRIMARY KEY,
            primary_virtue TEXT,
            primary_virtue_score REAL,
            {cols_sql}
        )
    '''
    conn.execute(create_sql)

    for _, r in result_df.iterrows():
        pid = int(r['id'])
        pvirt = r.get('primary_virtue', 'unknown') or 'unknown'
        pscore = float(r.get('primary_virtue_score', 0.0) or 0.0)
        values = [float(r.get(c, 0.0) or 0.0) for c in extra_cols]
        placeholders = ','.join(['?'] * (3 + len(values)))
        sql = f'INSERT INTO {table_name} (movie_id, primary_virtue, primary_virtue_score{"," if values else ""} {",".join(extra_cols) if extra_cols else ""}) VALUES ({placeholders})'
        conn.execute(sql, (pid, pvirt, pscore, *values) if values else (pid, pvirt, pscore))

    conn.commit()
    conn.close()


def main():
    print('Loading data...')
    movies_df, reviews_df, genres_df, keywords_df, related_df = load_movies_and_reviews(limit=MAX_DOCS)
    doc_df = combine_documents(movies_df, reviews_df, genres_df, keywords_df, related_df)
    print(f'Documents prepared: {len(doc_df)}')

    if len(doc_df) == 0:
        print('No documents to process. Exiting.')
        return

    print('Loading embedding model...')
    embedder = SentenceTransformer(EMB_MODEL_NAME)

    print('Fitting BERTopic (this may take some time)...')
    topic_model = BERTopic(
        embedding_model=embedder,
        min_topic_size=BERTOPIC_MIN_TOPIC_SIZE,
        n_gram_range=BERTOPIC_N_GRAM_RANGE,
        top_n_words=BERTOPIC_TOP_N_WORDS,
        verbose=True
    )
    topics, probs = topic_model.fit_transform(doc_df['doc'].tolist())

    # Attempt to reduce outliers: reassign docs in topic -1 to nearest topics
    try:
        print('\nAttempting to reduce outliers (reassign -1 topics) using BERTopic.reduce_outliers...')
        reduced = None
        try:
            reduced = topic_model.reduce_outliers(doc_df['doc'].tolist(), topics, probs)
        except TypeError:
            # Some BERTopic versions accept only (docs, topics) or (docs, topics, probabilities)
            try:
                reduced = topic_model.reduce_outliers(doc_df['doc'].tolist(), topics)
            except Exception as e:
                print('reduce_outliers inner call failed:', e)

        if reduced is not None:
            topics = reduced
            print('Outliers reduced. New topic distribution (top 20):')
            print(pd.Series(topics).value_counts().head(20))
        else:
            print('reduce_outliers returned None; keeping original topics.')
    except Exception as e:
        print('reduce_outliers failed:', e)

    # Aggressive outlier reassignment: if many docs still in -1, assign to nearest topic
    outlier_count = np.sum(topics == -1)
    print(f'\nDocuments in topic -1: {outlier_count}')
    if REDUCE_OUTLIERS_AGGRESSIVE and outlier_count > 0:
        print('Running aggressive outlier reassignment...')
        doc_embeddings = topic_model._extract_embeddings(doc_df['doc'].tolist(), method='document')
        topics = reassign_outliers_to_nearest_topic(doc_embeddings, topics, topic_model)
        outlier_count_after = np.sum(topics == -1)
        print(f'Documents in topic -1 after reassignment: {outlier_count_after}')
        print('New topic distribution (top 20):')
        print(pd.Series(topics).value_counts().head(20))

    print('\nTopic Info:')
    print(topic_model.get_topic_info().head(30))

    print('\nMapping topics to virtues...')
    # Compute soft mapping: topic -> virtue similarity matrix, then aggregate per-document
    if USE_ZERO_SHOT_TOPIC_SCORING:
        print('\nComputing topic->virtue matrix with zero-shot classification...')
    else:
        print('\nComputing soft topic->virtue similarity matrix...')
    topic_ids, virtue_keys, sim_matrix = get_topic_virtue_matrix(topic_model, embedder)
    print('Topic ids (order for similarity matrix):', topic_ids)
    print('Virtue keys:', virtue_keys)
    print('\nSample similarity matrix (first 5 topics x all virtues):')
    print(sim_matrix[:min(5, len(topic_ids))])

    # Build result DataFrame
    result = doc_df.copy()
    result['topic'] = topics  # assigned topic id per doc

    # probs: if available, convert to numpy array aligned with topic_ids order
    probs_arr = None
    try:
        probs_arr = np.array(probs)
    except Exception:
        probs_arr = None
    
    # DEBUG: Print topic assignments
    print('\n=== DEBUG: Topic Assignment Distribution ===')
    print(f'Topic value counts:\n{pd.Series(topics).value_counts().head(15)}')
    
    # Find Finding Nemo and print its raw assignments
    finding_nemo_idx = result[result['title'].str.contains('Finding Nemo', case=False, na=False)].index
    if len(finding_nemo_idx) > 0:
        fn_idx = finding_nemo_idx[0]
        print(f'\nFinding Nemo (index {fn_idx}):')
        print(f'  Assigned topic: {topics[fn_idx]}')
        if probs_arr is not None and probs_arr.ndim == 2 and fn_idx < len(probs_arr):
            print(f'  Raw probs shape: {probs_arr.shape}')
            fn_probs = probs_arr[fn_idx]
            print(f'  Top 5 prob values: {np.sort(fn_probs)[-5:][::-1]}')
            print(f'  Sum of probs: {fn_probs.sum():.6f}')
            print(f'  Number of non-zero probs: {(fn_probs > 0).sum()}')

    # Initialize virtue score columns
    for vk in virtue_keys:
        result[f'{vk}_score'] = 0.0

    if probs_arr is not None and probs_arr.ndim == 2:
        # probs_arr rows align with topic_ids ordering returned by BERTopic.get_topic_info()
        # Keep only the top-k topic probabilities per document and sharpen them before aggregation.
        try:
            topic_weights = np.power(np.clip(probs_arr, 0.0, 1.0), TOPIC_PROB_GAMMA)
            if TOP_K_TOPICS and TOP_K_TOPICS < topic_weights.shape[1]:
                topk_mask = np.zeros_like(topic_weights)
                topk_idx = np.argpartition(topic_weights, -TOP_K_TOPICS, axis=1)[:, -TOP_K_TOPICS:]
                for row_idx in range(topic_weights.shape[0]):
                    topk_mask[row_idx, topk_idx[row_idx]] = topic_weights[row_idx, topk_idx[row_idx]]
                topic_weights = topk_mask

            topic_weight_sums = topic_weights.sum(axis=1, keepdims=True)
            topic_weights = np.divide(topic_weights, topic_weight_sums, out=np.zeros_like(topic_weights), where=topic_weight_sums > 0)

            virtue_scores_all = topic_weights.dot(sim_matrix)  # (n_docs, n_virtues)
            virtue_scores_all = np.power(np.clip(virtue_scores_all, 0.0, 1.0), FINAL_SCORE_GAMMA)
            for j, vk in enumerate(virtue_keys):
                result[f'{vk}_score'] = virtue_scores_all[:, j]
        except Exception:
            # Fallback: use assigned topic only
            for i, t in enumerate(result['topic']):
                if t in topic_ids:
                    idx = topic_ids.index(t)
                    sims = sim_matrix[idx]
                    for j, vk in enumerate(virtue_keys):
                        result.at[i, f'{vk}_score'] = float(sims[j])
    else:
        # No probs matrix: fall back to using assigned topic's similarity vector
        for i, t in enumerate(result['topic']):
            if t in topic_ids:
                idx = topic_ids.index(t)
                sims = sim_matrix[idx]
                for j, vk in enumerate(virtue_keys):
                    result.at[i, f'{vk}_score'] = float(sims[j])

    # Normalize virtue scores per document to sum to 1 (if sum>0)
    virtue_cols = [f'{vk}_score' for vk in virtue_keys]
    
    # DEBUG: Print stats before normalization
    print('\n=== DEBUG: Virtue Scores Before Normalization ===')
    print(f'Min per-virtue score: {result[virtue_cols].min().min():.6f}')
    print(f'Max per-virtue score: {result[virtue_cols].max().max():.6f}')
    print(f'Mean per-virtue score: {result[virtue_cols].mean().mean():.6f}')
    scores_sum = result[virtue_cols].sum(axis=1)
    print(f'Min sum per doc: {scores_sum.min():.6f}')
    print(f'Max sum per doc: {scores_sum.max():.6f}')
    print(f'Mean sum per doc: {scores_sum.mean():.6f}')
    print(f'Docs with sum=0: {(scores_sum == 0).sum()}')
    
    # Find Finding Nemo if present
    finding_nemo_idx = result[result['title'].str.contains('Finding Nemo', case=False, na=False)].index
    if len(finding_nemo_idx) > 0:
        fn_idx = finding_nemo_idx[0]
        print(f'\nFinding Nemo (index {fn_idx}):')
        print(f'  Topic assigned: {result.loc[fn_idx, "topic"]}')
        print(f'  Raw virtue scores: {result.loc[fn_idx, virtue_cols].values}')
        print(f'  Sum: {scores_sum.loc[fn_idx]:.6f}')
        if probs_arr is not None and probs_arr.ndim == 2 and fn_idx < len(probs_arr):
            print(f'  Topic probabilities (first 10): {probs_arr[fn_idx, :10]}')
    
    scores_sum = result[virtue_cols].sum(axis=1).replace(0, np.nan)
    for col in virtue_cols:
        result[col] = result[col].divide(scores_sum).fillna(0.0)

    # Re-sharpen after normalization so evenly matched movies do not collapse to flat vectors
    for col in virtue_cols:
        result[col] = np.power(np.clip(result[col], 0.0, 1.0), FINAL_SCORE_GAMMA)
    scores_sum = result[virtue_cols].sum(axis=1).replace(0, np.nan)
    for col in virtue_cols:
        result[col] = result[col].divide(scores_sum).fillna(0.0)

    # DEBUG: Print stats after normalization
    print('\n=== DEBUG: Virtue Scores After Normalization ===')
    print(f'Min per-virtue score: {result[virtue_cols].min().min():.6f}')
    print(f'Max per-virtue score: {result[virtue_cols].max().max():.6f}')
    if len(finding_nemo_idx) > 0:
        fn_idx = finding_nemo_idx[0]
        print(f'Finding Nemo after norm: {result.loc[fn_idx, virtue_cols].values}')

    # primary virtue = argmax of virtue scores
    result['primary_virtue'] = result[virtue_cols].idxmax(axis=1).str.replace('_score', '')
    result['primary_virtue_score'] = result[virtue_cols].max(axis=1)

    # Save full virtue scores to DB
    save_results_to_db(result[['id', 'primary_virtue', 'primary_virtue_score'] + virtue_cols])

    print('\nSample categorized movies:')
    print(result[['title', 'primary_virtue', 'primary_virtue_score'] + virtue_cols].head(20))


if __name__ == '__main__':
    main()
