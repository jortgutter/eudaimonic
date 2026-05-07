"""
Movie Categorization by Virtues using Topic Modeling

This script categorizes movies from the movies.db database into virtue categories
(wisdom, humanity, purpose, justice, restraint, courage) using LDA topic modeling
on combined movie summaries and reviews.
"""

import sqlite3
import re
from pathlib import Path

import pandas as pd
import numpy as np
import gensim
import gensim.corpora as corpora
from gensim.models import ldamodel, CoherenceModel
import nltk
from nltk.corpus import stopwords
import spacy

# ============================================================================
# SETUP & CONFIGURATION
# ============================================================================

# Download NLTK stopwords if not already present
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords')

stop_words = stopwords.words('english')

# Load spaCy model for lemmatization
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("spaCy model not found. Installing...")
    import os
    os.system('python -m spacy download en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')

# Disable parser and NER for faster processing
nlp.disable_pipes(['parser', 'ner'])

# Database path
DB_PATH = Path('movies.db')

# Domain-specific stopwords to remove generic movie words that pollute topics
DOMAIN_STOPWORDS = set([
    'film', 'movie', 'one', 'like', 'get', 'make', 'see', 'time', 'first',
    'story', 'show', 'series', 'episode', 'watch', 'also', 'would', 'many',
    'character', 'characters'
])

# Virtue category definitions
VIRTUE_CATEGORIES = {
    'wisdom': 'Knowledge, learning, intelligence, understanding, truth',
    'humanity': 'Compassion, empathy, kindness, care, connection',
    'purpose': 'Meaning, goal, mission, direction, fulfillment',
    'justice': 'Fairness, equality, rights, morality, law',
    'restraint': 'Self-control, discipline, moderation, patience, balance',
    'courage': 'Bravery, strength, determination, risk, heroism'
}

# Topic-to-virtue mapping (adjust based on discovered topic keywords)
TOPIC_TO_VIRTUE = {
    0: 'courage',
    1: 'wisdom',
    2: 'justice',
    3: 'humanity',
    4: 'restraint',
    5: 'purpose'
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def preprocess_text(text):
    """Preprocess text: remove special chars, lowercase, etc."""
    text = re.sub(r'\s+', ' ', text)  # Remove extra spaces
    text = re.sub(r'\S*@\S*\s?', '', text)  # Remove emails
    text = re.sub(r"'", '', text)  # Remove apostrophes
    text = re.sub(r'[^a-zA-Z]', ' ', text)  # Remove non-alphabet
    text = text.lower()  # Lowercase
    return text.strip()


def tokenize_text(text):
    """Tokenize and remove stopwords."""
    tokens = gensim.utils.simple_preprocess(text, deacc=True)
    tokens = [token for token in tokens if token not in stop_words and token not in DOMAIN_STOPWORDS]
    return tokens


def lemmatize_tokens(tokens):
    """Lemmatize tokens using spaCy."""
    doc = nlp(" ".join(tokens))
    return [token.lemma_ for token in doc]


# ============================================================================
# DATA LOADING
# ============================================================================

def load_movies_and_reviews():
    """Load movies with summaries and their reviews from database."""
    print("Connecting to database...")
    conn = sqlite3.connect(DB_PATH)

    print("Loading movies with summaries...")
    movies_query = """
    SELECT m.id, m.title, m.summary, COUNT(r.id) as review_count
    FROM movies m
    LEFT JOIN reviews r ON m.id = r.movie_id
    WHERE m.summary IS NOT NULL AND m.summary != ''
    GROUP BY m.id
    ORDER BY review_count DESC
    """
    movies_df = pd.read_sql_query(movies_query, conn)
    print(f"✓ Loaded {len(movies_df)} movies with summaries")

    print("Loading reviews...")
    reviews_query = """
    SELECT movie_id, review_text
    FROM reviews
    WHERE movie_id IN (SELECT id FROM movies WHERE summary IS NOT NULL)
    LIMIT 5000
    """
    reviews_df = pd.read_sql_query(reviews_query, conn)
    conn.close()
    print(f"✓ Loaded {len(reviews_df)} reviews")

    return movies_df, reviews_df


def combine_movie_documents(movies_df, reviews_df):
    """Combine movie summaries with their reviews into single documents."""
    print("\nCombining summaries with reviews...")
    
    movie_text_dict = {}

    # Add summaries
    for _, row in movies_df.iterrows():
        movie_text_dict[row['id']] = [row['summary']]

    # Add reviews grouped by movie
    for _, row in reviews_df.iterrows():
        if row['movie_id'] not in movie_text_dict:
            movie_text_dict[row['movie_id']] = []
        if pd.notna(row['review_text']):
            movie_text_dict[row['movie_id']].append(row['review_text'])

    # Create combined documents
    movie_docs = []
    movie_ids = []
    for movie_id, texts in movie_text_dict.items():
        combined_text = ' '.join(texts[:6])  # Summary + up to 5 reviews
        if len(combined_text) > 50:  # Only include if substantial content
            movie_docs.append(combined_text)
            movie_ids.append(movie_id)

    movie_df_processed = movies_df[movies_df['id'].isin(movie_ids)].copy()
    movie_df_processed['combined_text'] = movie_docs

    avg_length = movie_df_processed['combined_text'].str.len().mean()
    print(f"✓ Created {len(movie_df_processed)} combined documents")
    print(f"  Average document length: {avg_length:.0f} characters")

    return movie_df_processed


# ============================================================================
# TEXT PROCESSING PIPELINE
# ============================================================================

def process_documents(movie_df_processed):
    """Apply full text processing pipeline."""
    print("\nProcessing documents...")

    # Preprocess
    print("  - Preprocessing...")
    movie_df_processed['cleaned_text'] = movie_df_processed['combined_text'].apply(preprocess_text)

    # Tokenize
    print("  - Tokenizing...")
    movie_df_processed['tokens'] = movie_df_processed['cleaned_text'].apply(tokenize_text)

    # Lemmatize
    print("  - Lemmatizing...")
    movie_df_processed['lemmas'] = movie_df_processed['tokens'].apply(lemmatize_tokens)

    print("✓ Processing complete")
    return movie_df_processed


# ============================================================================
# TOPIC MODELING
# ============================================================================

def build_lda_model(movie_df_processed):
    """Build LDA model and return dictionary, corpus, and model."""
    print("\nBuilding LDA model...")

    # Create dictionary and corpus
    print("  - Creating dictionary and corpus...")
    movie_id2word = corpora.Dictionary(movie_df_processed['lemmas'])
    movie_corpus = [movie_id2word.doc2bow(text) for text in movie_df_processed['lemmas']]

    print(f"    Dictionary: {len(movie_id2word)} unique tokens")
    print(f"    Corpus: {len(movie_corpus)} documents")

    # Diagnostic: how many documents have non-empty token lists
    nonempty_docs = sum(1 for tokens in movie_df_processed['lemmas'] if len(tokens) > 0)
    print(f"    Documents with tokens: {nonempty_docs} / {len(movie_df_processed)}")

    # Train LDA model
    print("  - Training LDA model (6 topics)...")
    movie_lda_model = ldamodel.LdaModel(
        corpus=movie_corpus,
        id2word=movie_id2word,
        num_topics=6,
        random_state=100,
        update_every=1,
        chunksize=50,
        passes=10,
        alpha='auto',
        per_word_topics=True
    )

    print("✓ LDA model trained")

    # Compute coherence score
    print("  - Computing coherence score...")
    coherence_model = CoherenceModel(
        model=movie_lda_model,
        texts=movie_df_processed['lemmas'],
        dictionary=movie_id2word,
        coherence='c_v'
    )
    coherence_score = coherence_model.get_coherence()
    print(f"    Coherence Score: {coherence_score:.4f}")

    return movie_id2word, movie_corpus, movie_lda_model


def display_topics(movie_lda_model):
    """Display discovered topics."""
    print("\nDiscovered Topics:")
    print("-" * 80)
    movie_topics = movie_lda_model.print_topics(num_words=15)
    for i, topic in enumerate(movie_topics):
        virtue = TOPIC_TO_VIRTUE[i]
        print(f"\nTopic {i} → {virtue.upper()}: {topic}")
    print("-" * 80)


# ============================================================================
# VIRTUE CATEGORIZATION
# ============================================================================

def categorize_movies(movie_df_processed, movie_corpus, movie_lda_model):
    """Get topic distribution and assign virtue categories."""
    print("\nCategorizing movies by virtues...")

    # Get topic distribution for each movie
    movie_topics_dist = []

    for doc_bow in movie_corpus:
        # request a full distribution (include near-zero topics)
        topic_dist = movie_lda_model.get_document_topics(doc_bow, minimum_probability=0)

        # Create complete vector with all topic probabilities
        topic_vector = {i: 0.0 for i in range(6)}
        for topic_id, prob in topic_dist:
            topic_vector[topic_id] = prob

        movie_topics_dist.append(topic_vector)

    # Convert to DataFrame
    topics_df = pd.DataFrame(movie_topics_dist)
    topics_df.columns = [f'topic_{i}' for i in range(6)]
    # Ensure no NaNs in topic probabilities
    topics_df = topics_df.fillna(0.0)

    # Combine with movie data
    result_df = movie_df_processed[['id', 'title']].reset_index(drop=True).copy()
    result_df = pd.concat([result_df, topics_df], axis=1)

    # Map topics to virtues
    virtue_scores = pd.DataFrame()
    for virtue in VIRTUE_CATEGORIES.keys():
        virtue_scores[virtue] = 0.0

    for topic_id, virtue in TOPIC_TO_VIRTUE.items():
        virtue_scores[virtue] += result_df[f'topic_{topic_id}']

    # Assign primary virtue and all virtue scores
    # idxmax on ties yields the first arg; ensure no NaN and cast to str
    result_df['primary_virtue'] = virtue_scores.idxmax(axis=1).fillna('unknown').astype(str)
    result_df['primary_virtue_score'] = virtue_scores.max(axis=1)

    for virtue in VIRTUE_CATEGORIES.keys():
        result_df[f'{virtue}_score'] = virtue_scores[virtue]

    print(f"✓ Categorized {len(result_df)} movies")

    return result_df


def display_distribution(result_df):
    """Display distribution of movies by virtue category."""
    print("\nMovies per virtue category:")
    print("-" * 50)
    virtue_counts = result_df['primary_virtue'].value_counts()
    for virtue in VIRTUE_CATEGORIES.keys():
        count = virtue_counts.get(virtue, 0)
        percentage = (count / len(result_df)) * 100
        print(f"  {virtue.capitalize():<12}: {count:>4} movies ({percentage:>5.1f}%)")
    print("-" * 50)


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def save_to_database(result_df):
    """Save categorization results to database."""
    print("\nSaving to database...")

    conn = sqlite3.connect(DB_PATH)

    # Create or update movie_virtues table
    print("  - Creating movie_virtues table...")
    conn.execute('DROP TABLE IF EXISTS movie_virtues')

    conn.execute('''
        CREATE TABLE movie_virtues (
            movie_id INTEGER PRIMARY KEY,
            primary_virtue TEXT,
            primary_virtue_score REAL,
            wisdom_score REAL,
            humanity_score REAL,
            purpose_score REAL,
            justice_score REAL,
            restraint_score REAL,
            courage_score REAL,
            FOREIGN KEY (movie_id) REFERENCES movies(id)
        )
    ''')

    # Insert data
    print(f"  - Inserting {len(result_df)} movie records...")
    for _, row in result_df.iterrows():
        primary_virtue = row['primary_virtue']
        if pd.isna(primary_virtue) or primary_virtue is None:
            primary_virtue = 'unknown'
        else:
            primary_virtue = str(primary_virtue)
        # Ensure numeric scores
        def _safe_float(x):
            try:
                if x is None:
                    return 0.0
                return float(x)
            except Exception:
                return 0.0

        conn.execute('''
            INSERT INTO movie_virtues 
            (movie_id, primary_virtue, primary_virtue_score, 
             wisdom_score, humanity_score, purpose_score, 
             justice_score, restraint_score, courage_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(row['id']),
            primary_virtue,
            _safe_float(row.get('primary_virtue_score')),
            _safe_float(row.get('wisdom_score')),
            _safe_float(row.get('humanity_score')),
            _safe_float(row.get('purpose_score')),
            _safe_float(row.get('justice_score')),
            _safe_float(row.get('restraint_score')),
            _safe_float(row.get('courage_score'))
        ))

    conn.commit()
    print("✓ Data saved to database")

    # Display sample results
    print("\nSample Results:")
    print("-" * 70)
    samples = conn.execute('''
        SELECT m.title, mv.primary_virtue, ROUND(mv.primary_virtue_score, 3) as score
        FROM movies m
        JOIN movie_virtues mv ON m.id = mv.movie_id
        ORDER BY mv.primary_virtue_score DESC
        LIMIT 10
    ''').fetchall()

    for title, virtue, score in samples:
        virtue = virtue if virtue is not None else 'unknown'
        try:
            score_val = float(score) if score is not None else 0.0
        except Exception:
            score_val = 0.0
        print(f"  {title:<45} → {virtue:<12} ({score_val:.3f})")
    print("-" * 70)

    conn.close()
    print("✓ Database connection closed")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution pipeline."""
    print("=" * 80)
    print("MOVIE CATEGORIZATION BY VIRTUES - Topic Modeling Pipeline")
    print("=" * 80)

    try:
        # Load data
        movies_df, reviews_df = load_movies_and_reviews()

        # Combine documents
        movie_df_processed = combine_movie_documents(movies_df, reviews_df)

        # Process text
        movie_df_processed = process_documents(movie_df_processed)

        # Build LDA model
        movie_id2word, movie_corpus, movie_lda_model = build_lda_model(movie_df_processed)

        # Display topics
        display_topics(movie_lda_model)

        # Categorize movies
        result_df = categorize_movies(movie_df_processed, movie_corpus, movie_lda_model)

        # Display distribution
        display_distribution(result_df)

        # Save results
        save_to_database(result_df)

        print("\n" + "=" * 80)
        print("✓ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
