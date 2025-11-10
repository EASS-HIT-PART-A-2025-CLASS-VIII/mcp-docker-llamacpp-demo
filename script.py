import argparse
import asyncio
import os
import re
from typing import List

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from openai import AsyncOpenAI
from pydantic import BaseModel
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Defaults can be overridden via CLI flags or env vars.
DEFAULT_MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT", "http://localhost:8080/mcp")
DEFAULT_LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:1234/v1")
DEFAULT_PEOPLE = ["Sam Altman", "Elon Musk", "Donald Trump"]

console = Console()


def positive_int(value: str) -> int:
    """argparse helper to require positive integers."""
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return ivalue


class Podcast(BaseModel):
    """Simple podcast data model."""

    person: str
    title: str
    url: str
    topics: str = "N/A"
    insights: str = "N/A"


async def summarize(llm_client: AsyncOpenAI, text: str) -> dict:
    """Extract topics and insights from transcript."""
    response = await llm_client.chat.completions.create(
        model="local",
        messages=[{
            "role": "user",
            "content": f"Extract 3-5 topics (comma-separated) and 2 key insights (brief) from:\n\n{text[:3000]}"
        }],
        temperature=0.3,
        max_tokens=200
    )
    
    content = response.choices[0].message.content
    
    # Simple parsing
    topics = "General discussion"
    insights = "Various topics discussed"
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'topic' in line.lower() and i + 1 < len(lines):
            topics = lines[i + 1].strip()[:80]
        elif 'insight' in line.lower() and i + 1 < len(lines):
            insights = '\n'.join(lines[i + 1:])[:150]
    
    return {"topics": topics, "insights": insights}


async def fetch_podcasts(
    session: ClientSession,
    llm_client: AsyncOpenAI,
    person: str,
    *,
    videos_per_person: int,
    max_search_results: int,
) -> List[Podcast]:
    """Fetch and analyze YouTube podcasts for a person."""
    podcasts = []

    # Search
    result = await session.call_tool(
        "search",
        arguments={"query": f"{person} YouTube podcast", "max_results": max_search_results}
    )
    
    # Extract YouTube URLs
    urls = []
    for block in result.content:
        if isinstance(block, types.TextContent):
            for line in block.text.split('\n'):
                if 'youtube.com/watch' in line.lower():
                    match = re.search(r'https?://[^\s]+', line)
                    if match:
                        urls.append((line.split('\n')[0], match.group(0)))
    
    if not urls:
        console.print(f"[yellow]No YouTube results found for {person}. Try another query.[/yellow]")
        return podcasts

    # Process videos
    for title, url in urls[:videos_per_person]:
        try:
            # Get transcript
            transcript_result = await session.call_tool("get_transcript", arguments={"url": url})
            
            transcript = ""
            for block in transcript_result.content:
                if isinstance(block, types.TextContent):
                    transcript += block.text
            
            if not transcript:
                continue
            
            # Summarize
            summary = await summarize(llm_client, transcript)
            
            podcasts.append(Podcast(
                person=person,
                title=title[:50] + "..." if len(title) > 50 else title,
                url=url,
                topics=summary['topics'],
                insights=summary['insights']
            ))
            
        except Exception as e:
            console.print(f"[dim red]Skipped {url[:30]}...: {str(e)[:50]}[/dim red]")
            continue
    
    return podcasts


async def verify_services(llm_client: AsyncOpenAI, mcp_endpoint: str) -> bool:
    """Confirm the LLM server and MCP gateway are reachable."""
    healthy = True

    try:
        await llm_client.chat.completions.create(
            model="local",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        console.print("[green]✓[/green] LLM connected")
    except Exception as e:
        healthy = False
        console.print(f"[bold red]✗ LLM connection failed:[/bold red] {e}")
        console.print("[yellow]Start it via 'scripts/start_llm_server.sh' (Docker required).[/yellow]")

    try:
        async with streamablehttp_client(mcp_endpoint) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.list_tools()
        console.print("[green]✓[/green] MCP gateway connected")
    except Exception as e:
        healthy = False
        console.print(f"[bold red]✗ MCP gateway unreachable:[/bold red] {e}")
        console.print("[yellow]Start it via 'scripts/start_mcp_gateway.sh'.[/yellow]")

    return healthy


def parse_args() -> argparse.Namespace:
    """CLI surface for beginners."""
    parser = argparse.ArgumentParser(
        description="Search YouTube for interviews, grab transcripts, and summarize them with a local LLM."
    )
    parser.add_argument(
        "--people",
        nargs="+",
        default=DEFAULT_PEOPLE,
        help="Names to search for (defaults to three tech figures)."
    )
    parser.add_argument(
        "--per-person",
        type=positive_int,
        default=2,
        help="How many videos to summarize per person (default: 2)."
    )
    parser.add_argument(
        "--max-search-results",
        type=positive_int,
        default=15,
        help="How many search hits to inspect for each person."
    )
    parser.add_argument(
        "--llm-endpoint",
        default=DEFAULT_LLM_ENDPOINT,
        help=f"llama.cpp REST endpoint (default: {DEFAULT_LLM_ENDPOINT})."
    )
    parser.add_argument(
        "--mcp-endpoint",
        default=DEFAULT_MCP_ENDPOINT,
        help=f"MCP gateway endpoint (default: {DEFAULT_MCP_ENDPOINT})."
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Only verify both services are alive, then exit."
    )
    return parser.parse_args()


async def main() -> None:
    """Main execution."""
    args = parse_args()
    console.print(Panel("[bold cyan]🎙️ YouTube Podcast Analyzer[/bold cyan]", border_style="cyan"))

    llm_client = AsyncOpenAI(base_url=args.llm_endpoint, api_key="not-needed")

    if not await verify_services(llm_client, args.mcp_endpoint):
        return

    if args.smoke_test:
        console.print("[bold green]Smoke test passed — you're ready to run without --smoke-test.[/bold green]")
        return

    try:
        async with streamablehttp_client(args.mcp_endpoint) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                all_podcasts: List[Podcast] = []

                with console.status("[bold green]Fetching podcasts...") as status:
                    for person in args.people:
                        status.update(f"[bold green]Processing {person}...")
                        podcasts = await fetch_podcasts(
                            session,
                            llm_client,
                            person,
                            videos_per_person=args.per_person,
                            max_search_results=args.max_search_results,
                        )
                        all_podcasts.extend(podcasts)
                        console.print(f"[green]✓[/green] {person}: {len(podcasts)} podcasts")

                if not all_podcasts:
                    console.print("[bold yellow]No podcasts were summarized. Try different names or raise --max-search-results.[/bold yellow]")
                    return

                console.print()
                table = Table(
                    title="📊 Podcast Analysis",
                    box=box.ROUNDED,
                    show_lines=True,
                    title_style="bold cyan"
                )

                table.add_column("Person", style="cyan bold", width=12)
                table.add_column("Title", style="white", width=30)
                table.add_column("Topics", style="yellow", width=35)
                table.add_column("Insights", style="green", width=40)

                for p in all_podcasts:
                    table.add_row(p.person, p.title, p.topics, p.insights)

                console.print(table)

                console.print()
                console.print(Panel(
                    f"[bold]Total Podcasts:[/bold] {len(all_podcasts)}\n"
                    + "\n".join([
                        f"• {name}: {sum(1 for p in all_podcasts if p.person == name)}"
                        for name in args.people
                    ]),
                    title="📈 Summary",
                    border_style="green"
                ))

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("\n[yellow]Make sure services are still running:[/yellow]")
        console.print(f"  MCP: {args.mcp_endpoint}")
        console.print(f"  LLM: {args.llm_endpoint}")
        console.print("\n[cyan]Restart scripts if needed:[/cyan]")
        console.print("  scripts/start_llm_server.sh")
        console.print("  scripts/start_mcp_gateway.sh")


if __name__ == "__main__":
    asyncio.run(main())
