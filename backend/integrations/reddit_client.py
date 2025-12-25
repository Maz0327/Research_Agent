"""Reddit API integration using PRAW."""
import os
from typing import List, Dict
from datetime import datetime
from loguru import logger

try:
    import praw
    from prawcore.exceptions import ResponseException, RequestException
    PRAW_AVAILABLE = True
except ImportError:
    logger.warning("PRAW not installed. Install with: pip install praw")
    PRAW_AVAILABLE = False


class RedditClient:
    """Reddit API client for fetching posts and comments."""

    def __init__(self):
        """Initialize Reddit client with credentials."""
        if not PRAW_AVAILABLE:
            raise ImportError("PRAW library is required. Install with: pip install praw")

        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT", "ResearchAgent/1.0")

        if not client_id or not client_secret:
            raise ValueError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set in environment")

        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        self.reddit.read_only = True  # We only need read access
        logger.info("Reddit client initialized in read-only mode")

    def search_subreddit(
        self,
        subreddit_name: str,
        query: str,
        limit: int = 10,
        sort: str = "relevance",  # relevance, hot, top, new
        time_filter: str = "all"   # all, day, week, month, year
    ) -> List[Dict]:
        """
        Search a subreddit for posts matching query.

        Returns list of post data including comments.
        """
        posts = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # Search posts
            search_results = subreddit.search(
                query,
                sort=sort,
                time_filter=time_filter,
                limit=limit
            )

            for submission in search_results:
                post_data = {
                    "id": submission.id,
                    "title": submission.title,
                    "url": f"https://reddit.com{submission.permalink}",
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
                    "score": submission.score,
                    "upvote_ratio": submission.upvote_ratio,
                    "num_comments": submission.num_comments,
                    "text": submission.selftext,
                    "subreddit": subreddit_name,
                    "comments": []
                }

                # Fetch top comments
                try:
                    submission.comments.replace_more(limit=0)  # Remove MoreComments
                    for comment in submission.comments.list()[:20]:  # Top 20 comments
                        if hasattr(comment, 'body') and hasattr(comment, 'score'):
                            post_data["comments"].append({
                                "author": str(comment.author) if comment.author else "[deleted]",
                                "body": comment.body,
                                "score": comment.score,
                                "created_utc": datetime.fromtimestamp(comment.created_utc).isoformat() if hasattr(comment, 'created_utc') else None
                            })
                except Exception as e:
                    logger.debug(f"Error fetching comments for post {submission.id}: {e}")

                posts.append(post_data)
                logger.debug(f"Fetched post: {post_data['title'][:50]}...")

        except ResponseException as e:
            logger.error(f"Reddit API error searching r/{subreddit_name}: {e}")
        except RequestException as e:
            logger.error(f"Reddit request error searching r/{subreddit_name}: {e}")
        except Exception as e:
            logger.error(f"Error fetching Reddit posts from r/{subreddit_name}: {e}")

        logger.info(f"Fetched {len(posts)} posts from r/{subreddit_name}")
        return posts

    def search_multiple_subreddits(
        self,
        query: str,
        subreddits: List[str] = None,
        limit_per_sub: int = 5,
        sort: str = "relevance",
        time_filter: str = "all"
    ) -> List[Dict]:
        """Search multiple subreddits for a query."""
        if not subreddits:
            # Default subreddits for news/politics
            subreddits = [
                "politics",
                "news",
                "worldnews",
                "OutOfTheLoop",
                "NeutralPolitics"
            ]

        all_posts = []
        for sub in subreddits:
            logger.info(f"Searching r/{sub} for: {query}")
            try:
                posts = self.search_subreddit(
                    sub,
                    query,
                    limit=limit_per_sub,
                    sort=sort,
                    time_filter=time_filter
                )
                all_posts.extend(posts)
            except Exception as e:
                logger.warning(f"Failed to search r/{sub}: {e}")
                continue

        logger.info(f"Total Reddit posts fetched: {len(all_posts)} from {len(subreddits)} subreddits")
        return all_posts

    def get_hot_posts(
        self,
        subreddit_name: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get hot posts from a subreddit."""
        posts = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            for submission in subreddit.hot(limit=limit):
                post_data = {
                    "id": submission.id,
                    "title": submission.title,
                    "url": f"https://reddit.com{submission.permalink}",
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
                    "score": submission.score,
                    "upvote_ratio": submission.upvote_ratio,
                    "num_comments": submission.num_comments,
                    "text": submission.selftext,
                    "subreddit": subreddit_name,
                    "comments": []
                }
                posts.append(post_data)

        except Exception as e:
            logger.error(f"Error fetching hot posts from r/{subreddit_name}: {e}")

        return posts


def extract_reddit_content(posts: List[Dict]) -> str:
    """Convert Reddit posts to markdown for processing."""
    if not posts:
        return "# Reddit Discussions\n\nNo Reddit posts found.\n"

    lines = ["# Reddit Discussions\n"]
    lines.append(f"*{len(posts)} posts from Reddit*\n")

    for post in posts:
        lines.append(f"## {post['title']}")
        lines.append(f"*r/{post['subreddit']} | Score: {post['score']} | {post.get('created_utc', 'Unknown date')}*\n")
        lines.append(f"**Link:** {post['url']}\n")

        if post.get('text'):
            lines.append(f"{post['text']}\n")

        comments = post.get('comments', [])
        if comments:
            lines.append("### Top Comments:\n")
            for comment in comments[:5]:  # Top 5 comments
                author = comment.get('author', '[deleted]')
                score = comment.get('score', 0)
                body = comment.get('body', '')
                lines.append(f"> **{author} ({score} points):**")
                lines.append(f"> {body}\n")

        lines.append("---\n")

    return "\n".join(lines)
