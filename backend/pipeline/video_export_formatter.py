"""Formatter for video analysis export to Google Docs and Markdown."""
from datetime import datetime
from typing import Any, Optional


def format_video_analysis_for_export(
    artifacts: dict[str, Any],
    title: str = "Video Analysis",
    research_topic: str = "",
) -> str:
    """
    Format video analysis artifacts into a beautiful document.
    
    Args:
        artifacts: The job artifacts containing clips, quotes, blueprints, etc.
        title: Document title
        research_topic: The research topic/query
        
    Returns:
        Formatted string suitable for Google Docs or Markdown
    """
    lines = []
    
    # Header
    lines.append(f"# {title}")
    if research_topic:
        lines.append(f"**Research Topic:** {research_topic}")
    lines.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    lines.append("")
    
    # Summary section
    clips = artifacts.get("clips", [])
    quotes = artifacts.get("quotes", [])
    blueprints = artifacts.get("content_blueprints", [])
    gap_analysis = artifacts.get("gap_analysis", {})
    research_starter = artifacts.get("research_starter", {})
    
    lines.append("---")
    lines.append("")
    lines.append("## 📊 Summary")
    lines.append("")
    lines.append(f"- **{len(clips)}** clips extracted")
    lines.append(f"- **{len(quotes)}** notable quotes")
    lines.append(f"- **{len(blueprints)}** videos analyzed")
    
    if gap_analysis:
        missing = len(gap_analysis.get("missing_perspectives", []))
        questions = len(gap_analysis.get("unanswered_questions", []))
        lines.append(f"- **{missing}** missing perspectives identified")
        lines.append(f"- **{questions}** unanswered questions")
    
    if research_starter:
        queries = len(research_starter.get("search_queries", []))
        lines.append(f"- **{queries}** research queries generated")
    
    lines.append("")
    
    # Clips Section
    if clips:
        lines.append("---")
        lines.append("")
        lines.append("## 🎬 Clips & Timestamps")
        lines.append("")
        
        # Group clips by video
        clips_by_video: dict[str, list] = {}
        for clip in clips:
            video_title = clip.get("video_title", "Unknown Video")
            if video_title not in clips_by_video:
                clips_by_video[video_title] = []
            clips_by_video[video_title].append(clip)
        
        for video_title, video_clips in clips_by_video.items():
            lines.append(f"### {video_title}")
            lines.append("")
            
            for clip in video_clips:
                timestamp = clip.get("timestamp", "0:00")
                clip_type = clip.get("type", "clip")
                description = clip.get("description", "")
                
                # Format type label
                type_labels = {
                    "hook": "🎣 Hook",
                    "key_point": "💡 Key Point", 
                    "quote": "💬 Quote",
                    "story": "📖 Story",
                    "data": "📊 Data",
                    "controversy": "⚡ Controversy",
                    "conclusion": "🎯 Conclusion",
                }
                type_label = type_labels.get(clip_type, f"📌 {clip_type.title()}")
                
                lines.append(f"- **[{timestamp}]** {type_label}")
                if description:
                    lines.append(f"  {description}")
                lines.append("")
        
    # Quotes Section
    if quotes:
        lines.append("---")
        lines.append("")
        lines.append("## 💬 Notable Quotes")
        lines.append("")
        
        for quote in quotes:
            text = quote.get("text", "")
            speaker = quote.get("speaker", "Unknown")
            timestamp = quote.get("timestamp", "")
            video_title = quote.get("video_title", "")
            
            lines.append(f"> \"{text}\"")
            attribution = f"— {speaker}"
            if timestamp:
                attribution += f" [{timestamp}]"
            if video_title:
                attribution += f" ({video_title})"
            lines.append(f"> {attribution}")
            lines.append("")
    
    # Content Blueprints Section
    if blueprints:
        lines.append("---")
        lines.append("")
        lines.append("## 📋 Content Blueprints")
        lines.append("")
        
        for i, bp in enumerate(blueprints, 1):
            bp_title = bp.get("title", f"Video {i}")
            lines.append(f"### {i}. {bp_title}")
            lines.append("")
            
            # Hook
            hook = bp.get("hook")
            if hook:
                lines.append(f"**Hook:** {hook}")
                lines.append("")
            
            # Acts
            acts = bp.get("acts", [])
            if acts:
                lines.append("**Structure:**")
                for act in acts:
                    act_name = act.get("name", "")
                    act_summary = act.get("summary", "")
                    lines.append(f"- **{act_name}:** {act_summary}")
                lines.append("")
            
            # Open loops
            open_loops = bp.get("open_loops", [])
            if open_loops:
                lines.append("**Open Loops (Curiosity Hooks):**")
                for loop in open_loops:
                    question = loop.get("question", "")
                    resolved = "✅" if loop.get("resolved") else "❓"
                    lines.append(f"- {resolved} {question}")
                lines.append("")
    
    # Gap Analysis Section
    if gap_analysis:
        lines.append("---")
        lines.append("")
        lines.append("## 🔍 Research Gaps")
        lines.append("")
        
        missing_perspectives = gap_analysis.get("missing_perspectives", [])
        if missing_perspectives:
            lines.append("### Missing Perspectives")
            lines.append("")
            for mp in missing_perspectives:
                if isinstance(mp, dict):
                    perspective = mp.get("perspective", "")
                    importance = mp.get("importance", "")
                    lines.append(f"- **{perspective}**")
                    if importance:
                        lines.append(f"  *Why it matters:* {importance}")
                else:
                    lines.append(f"- {mp}")
            lines.append("")
        
        unanswered = gap_analysis.get("unanswered_questions", [])
        if unanswered:
            lines.append("### Unanswered Questions")
            lines.append("")
            for q in unanswered:
                if isinstance(q, dict):
                    question = q.get("question", "")
                    lines.append(f"- {question}")
                else:
                    lines.append(f"- {q}")
            lines.append("")
        
        contradictions = gap_analysis.get("contradictions", [])
        if contradictions:
            lines.append("### Contradictions Found")
            lines.append("")
            for c in contradictions:
                if isinstance(c, dict):
                    claim1 = c.get("claim1", "")
                    claim2 = c.get("claim2", "")
                    lines.append(f"- ⚡ \"{claim1}\" vs \"{claim2}\"")
                else:
                    lines.append(f"- {c}")
            lines.append("")
    
    # Research Starter Section
    if research_starter:
        lines.append("---")
        lines.append("")
        lines.append("## 🚀 Next Steps")
        lines.append("")
        
        search_queries = research_starter.get("search_queries", [])
        if search_queries:
            lines.append("### Search Queries to Try")
            lines.append("")
            for i, sq in enumerate(search_queries, 1):
                if isinstance(sq, dict):
                    query = sq.get("query", "")
                    platform = sq.get("platform", "Google")
                    rationale = sq.get("rationale", "")
                    lines.append(f"{i}. **{query}** ({platform})")
                    if rationale:
                        lines.append(f"   *{rationale}*")
                else:
                    lines.append(f"{i}. {sq}")
            lines.append("")
        
        source_suggestions = research_starter.get("source_suggestions", [])
        if source_suggestions:
            lines.append("### Suggested Sources")
            lines.append("")
            for ss in source_suggestions:
                if isinstance(ss, dict):
                    source_type = ss.get("type", "")
                    description = ss.get("description", "")
                    lines.append(f"- **{source_type}:** {description}")
                else:
                    lines.append(f"- {ss}")
            lines.append("")
        
        content_angles = research_starter.get("content_angles", [])
        if content_angles:
            lines.append("### Content Angles")
            lines.append("")
            for ca in content_angles:
                if isinstance(ca, dict):
                    angle = ca.get("angle", "")
                    description = ca.get("description", "")
                    lines.append(f"- **{angle}**")
                    if description:
                        lines.append(f"  {description}")
                else:
                    lines.append(f"- {ca}")
            lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by Research Agent*")
    
    return "\n".join(lines)


def format_clips_only(clips: list[dict]) -> str:
    """Format just the clips for quick export."""
    lines = ["# Video Clips", ""]
    
    for clip in clips:
        video = clip.get("video_title", "Unknown")
        timestamp = clip.get("timestamp", "0:00")
        description = clip.get("description", "")
        url = clip.get("url", "")
        
        lines.append(f"**[{timestamp}]** {video}")
        if description:
            lines.append(f"{description}")
        if url:
            lines.append(f"🔗 {url}")
        lines.append("")
    
    return "\n".join(lines)


def format_quotes_only(quotes: list[dict]) -> str:
    """Format just the quotes for quick export."""
    lines = ["# Notable Quotes", ""]
    
    for quote in quotes:
        text = quote.get("text", "")
        speaker = quote.get("speaker", "Unknown")
        timestamp = quote.get("timestamp", "")
        
        lines.append(f"> \"{text}\"")
        attribution = f"— {speaker}"
        if timestamp:
            attribution += f" [{timestamp}]"
        lines.append(f"> {attribution}")
        lines.append("")
    
    return "\n".join(lines)

