"""Database tools for the Implications Agent.

All tools return JSON-serializable dicts/lists for the LLM.
"""

import json
import psycopg2
import psycopg2.extras
from agent.config import Config


def _get_conn():
    return psycopg2.connect(Config.db_dsn())


def get_news(news_id: int) -> dict:
    """Get full news article by ID."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT news_id, title, content, native_summary, publish_date::text,
                       url, news_category_id, news_source_id, language,
                       sanitized_content, news_highlights, cluster_id
                FROM public.news
                WHERE news_id = %s
                """,
                (news_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else {"error": f"News {news_id} not found"}


def search_news(query: str, limit: int = 10) -> list:
    """Full-text search on news content. Returns matching articles."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT news_id, title, native_summary, publish_date::text, url,
                       ts_rank(search_content, websearch_to_tsquery('english', %s)) AS rank
                FROM public.news
                WHERE search_content @@ websearch_to_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
                """,
                (query, query, limit),
            )
            return [dict(r) for r in cur.fetchall()]


def get_newsfeed_context(news_id: int, feed_id: int) -> dict:
    """Get newsfeed metadata for a specific news+feed combination."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT nf.news_feed_id, nf.feed_id, nf.news_id, nf.news_priority_id,
                       nf.indication, nf.match, nf.product, nf.company, nf.summary,
                       nf.nct_number, nf.acronym, nf.is_keyword_match, nf.cluster_id
                FROM public.news_feed nf
                WHERE nf.news_id = %s AND nf.feed_id = %s
                """,
                (news_id, feed_id),
            )
            row = cur.fetchone()
            return dict(row) if row else {"error": f"No newsfeed entry for news={news_id}, feed={feed_id}"}


def get_alert_email(news_id: int, feed_id: int) -> dict:
    """Get the alert email already generated for this news+feed."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT news_alert_email_id, news_id, feed_id, alert_title, body,
                       created_at::text, reviewer_notes
                FROM public.news_alert_emails
                WHERE news_id = %s AND feed_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (news_id, feed_id),
            )
            row = cur.fetchone()
            return dict(row) if row else {"error": f"No alert email for news={news_id}, feed={feed_id}"}


def get_recent_alerts(feed_id: int, limit: int = 10) -> list:
    """Get recent alert emails sent to this feed, with their news context."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT nae.alert_title, nae.body, nae.created_at::text,
                       n.title AS news_title, n.native_summary, n.publish_date::text,
                       nf.company, nf.product, nf.indication
                FROM public.news_alert_emails nae
                JOIN public.news n ON n.news_id = nae.news_id
                LEFT JOIN public.news_feed nf ON nf.news_id = nae.news_id AND nf.feed_id = nae.feed_id
                WHERE nae.feed_id = %s
                ORDER BY nae.created_at DESC
                LIMIT %s
                """,
                (feed_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]


def search_news_for_feed(query: str, feed_id: int, limit: int = 10) -> list:
    """Search news that are linked to a specific feed (via news_feed)."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT n.news_id, n.title, n.native_summary, n.publish_date::text,
                       nf.news_priority_id, nf.company, nf.product, nf.indication, nf.summary,
                       ts_rank(n.search_content, websearch_to_tsquery('english', %s)) AS rank
                FROM public.news n
                JOIN public.news_feed nf ON nf.news_id = n.news_id
                WHERE nf.feed_id = %s
                  AND n.search_content @@ websearch_to_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
                """,
                (query, feed_id, query, limit),
            )
            return [dict(r) for r in cur.fetchall()]
