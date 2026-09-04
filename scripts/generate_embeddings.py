#!/usr/bin/env python3
"""
Generate OpenAI Embeddings for Scene Descriptions

This script:
1. Fetches all scene descriptions from database
2. Generates embeddings using OpenAI API
3. Stores embeddings in scene_embeddings table
4. Creates vector indexes for semantic search

Usage:
    python scripts/generate_embeddings.py --openai-key sk-...

Environment variables:
    TIMESCALE_HOST, TIMESCALE_USER, TIMESCALE_PASSWORD
    TIMESCALE_DB (default: tsdb)

Cost:
    ~0.02 - 0.05 USD for ~100 locations with OpenAI text-embedding-3-small
"""

import os
import sys
import argparse
import psycopg
import openai
from tqdm import tqdm

# Configuration
TIMESCALE_HOST = os.getenv("TIMESCALE_HOST")
TIMESCALE_PORT = os.getenv("TIMESCALE_PORT", "5432")
TIMESCALE_USER = os.getenv("TIMESCALE_USER")
TIMESCALE_PASSWORD = os.getenv("TIMESCALE_PASSWORD")
TIMESCALE_DB = os.getenv("TIMESCALE_DB", "tsdb")

# Embedding model
EMBEDDING_MODEL = "text-embedding-3-small"  # $0.02 per 1M tokens
EMBEDDING_DIM = 1536

def connect():
    """Create DB connection"""
    try:
        return psycopg.connect(
            f"postgresql://{TIMESCALE_USER}:{TIMESCALE_PASSWORD}@"
            f"{TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}"
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def generate_embedding(text, client):
    """Generate embedding for text using OpenAI API"""
    if not text or not text.strip():
        return None

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:8000],  # API limit
            encoding_format="float"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Embedding failed for text: {e}")
        return None

def fetch_events_without_embeddings(conn):
    """Get all filming events that don't have embeddings yet"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT fe.time, fe.production_id, fe.location_id, fe.scene_description
            FROM filming_events fe
            WHERE fe.scene_embedding IS NULL
              AND fe.scene_description IS NOT NULL
            ORDER BY fe.time DESC
        """)
        return cur.fetchall()

def update_embedding(conn, time, prod_id, loc_id, embedding):
    """Update filming_events table with embedding"""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE filming_events
            SET scene_embedding = %s
            WHERE time = %s AND production_id = %s AND location_id = %s
        """, (embedding, time, prod_id, loc_id))
    conn.commit()

def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description="Generate OpenAI embeddings for scene descriptions"
    )
    parser.add_argument("--openai-key", required=True, help="OpenAI API key")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--limit", type=int, help="Limit number of embeddings to generate")
    args = parser.parse_args()

    print("\n🎬 Generating OpenAI Embeddings\n")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Dimensions: {EMBEDDING_DIM}")
    print()

    # Initialize OpenAI client
    try:
        client = openai.OpenAI(api_key=args.openai_key)
    except Exception as e:
        print(f"❌ OpenAI initialization failed: {e}")
        sys.exit(1)

    # Connect to database
    conn = connect()
    print("✅ Connected to TimescaleDB\n")

    try:
        # Fetch events needing embeddings
        events = fetch_events_without_embeddings(conn)
        print(f"Found {len(events)} filming events without embeddings\n")

        if not events:
            print("✅ All events already have embeddings!")
            return

        if args.dry_run:
            print("📋 DRY RUN - Would process:")
            for i, (time, prod_id, loc_id, desc) in enumerate(events[:5]):
                print(f"   {i+1}. {desc[:60]}...")
            print(f"   ... and {len(events)-5} more")
            return

        # Process events
        limit = args.limit or len(events)
        total_cost = 0

        with tqdm(total=min(limit, len(events)), desc="Generating embeddings") as pbar:
            for i, (time, prod_id, loc_id, description) in enumerate(events[:limit]):
                if i >= limit:
                    break

                # Generate embedding
                embedding = generate_embedding(description, client)

                if embedding:
                    # Update database
                    update_embedding(conn, time, prod_id, loc_id, embedding)

                    # Rough cost estimation
                    token_count = len(description.split())
                    total_cost += (token_count / 1_000_000) * 0.02  # $0.02 per 1M tokens

                pbar.update(1)

        print(f"\n✅ Embeddings generated!")
        print(f"   Processed: {min(limit, len(events))} events")
        print(f"   Estimated cost: ${total_cost:.4f}")

        # Create indexes if needed
        print("\n📑 Creating vector indexes...")
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_filming_events_embedding
                    ON filming_events
                    USING ivfflat (scene_embedding vector_cosine_ops)
                    WHERE scene_embedding IS NOT NULL
                """)
                conn.commit()
                print("✅ Vector index created")
            except Exception as e:
                print(f"⚠️  Index creation: {e}")

        # Show sample semantic search
        print("\n💡 Now you can do semantic search queries like:")
        print("""
    -- Find all scenes with characters in dark settings
    SELECT p.title, l.address, fe.scene_description,
           (fe.scene_embedding <-> embedding_from_openai('dark basement scene')) as similarity
    FROM filming_events fe
    JOIN productions p ON fe.production_id = p.id
    JOIN locations l ON fe.location_id = l.id
    WHERE (fe.scene_embedding <-> embedding_from_openai('dark basement scene')) < 0.3
    ORDER BY similarity
    LIMIT 10;
        """)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    finally:
        conn.close()
        print("\n✓ Connection closed\n")

if __name__ == "__main__":
    main()
