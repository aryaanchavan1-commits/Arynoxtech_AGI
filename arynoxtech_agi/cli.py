"""
Arynoxtech_AGI CLI - Command Line Interface

Provides command-line access to Arynoxtech_AGI functionality.

Usage:
    arynoxtech_agi [command] [options]

Commands:
    chat        Start interactive chat mode
    api         Start API server
    status      Show AGI status
    domains     List available domains
    process     Process a file
    search      Search knowledge base
    version     Show version

Examples:
    arynoxtech_agi chat
    arynoxtech_agi api --port 8080
    arynoxtech_agi status
    arynoxtech_agi domains
    arynoxtech_agi process document.pdf
    arynoxtech_agi search "machine learning"
"""

import argparse
import asyncio
import sys
import logging
from pathlib import Path

from arynoxtech_agi.config import Config


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def cmd_chat(args):
    """Start interactive chat mode."""
    from arynoxtech_agi import ArynoxtechAGI

    agi = ArynoxtechAGI(
        offline_mode=args.offline,
        cache_enabled=not args.no_cache,
    )

    print("\n" + "="*60)
    print("  Arynoxtech_AGI - Multi-Domain AGI")
    print("  Version: 2.0.0")
    print("="*60)
    print("\nCommands:")
    print("  quit/exit - Exit chat")
    print("  status    - Show AGI status")
    print("  domains   - List domains")
    print("  help      - Show help")
    print()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit']:
                print("\nGoodbye!")
                break
            elif user_input.lower() == 'status':
                status = agi.get_status()
                print(f"\nAGI Status:")
                print(f"  Uptime: {status['state']['uptime_seconds']:.1f}s")
                print(f"  Interactions: {status['state']['total_interactions']}")
                print(f"  Domain: {status['domain_adaptor']['current_domain']}")
            elif user_input.lower() == 'domains':
                domains = agi.list_domains()
                print("\nAvailable Domains:")
                for d in domains:
                    enabled = "✅" if d['enabled'] else "❌"
                    print(f"  {enabled} {d['display_name']}: {d['description']}")
            elif user_input.lower() == 'help':
                print("\nCommands: quit, status, domains, help")
                print("Or just type your message to chat!")
            else:
                print("\nArynoxtech_AGI is thinking...")
                response = agi.chat(user_input)
                print(f"\nArynoxtech_AGI: {response.text}")
                print(f"[Domain: {response.domain_name} | Confidence: {response.confidence:.0%}]")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")

    agi.shutdown()


def cmd_api(args):
    """Start API server."""
    from arynoxtech_agi import ArynoxtechAGI

    print(f"\nStarting Arynoxtech_AGI API server on {args.host}:{args.port}...")

    agi = ArynoxtechAGI(offline_mode=args.offline)
    agi.start_api_server(host=args.host, port=args.port)


def cmd_status(args):
    """Show AGI status."""
    from arynoxtech_agi import ArynoxtechAGI

    agi = ArynoxtechAGI(offline_mode=True)
    status = agi.get_status()

    print("\n" + "="*50)
    print("  Arynoxtech_AGI Status")
    print("="*50)
    print(f"\n  Name: {status['config']['name']}")
    print(f"  Version: {status['config']['version']}")
    print(f"  Offline Mode: {status['config']['offline_mode']}")
    print(f"\n  Uptime: {status['state']['uptime_seconds']:.1f} seconds")
    print(f"  Total Interactions: {status['state']['total_interactions']}")
    print(f"  Current Domain: {status['domain_adaptor']['current_domain']}")
    print(f"  Total Domains: {status['domain_adaptor']['total_domains']}")
    print(f"  Enabled Domains: {status['domain_adaptor']['enabled_domains']}")
    print(f"  Background Tasks: {status['background_tasks']}")
    print()

    agi.shutdown()


def cmd_domains(args):
    """List available domains."""
    from arynoxtech_agi import ArynoxtechAGI

    agi = ArynoxtechAGI(offline_mode=True)
    domains = agi.list_domains()

    print("\n" + "="*60)
    print("  Available Domains")
    print("="*60)

    for d in domains:
        enabled = "✅" if d['enabled'] else "❌"
        print(f"\n  {enabled} {d['display_name']}")
        print(f"     Description: {d['description']}")
        print(f"     Specializations: {', '.join(d['specializations'])}")

    print()


def cmd_process(args):
    """Process a file."""
    from arynoxtech_agi import ArynoxtechAGI

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    print(f"Processing {args.file}...")
    agi = ArynoxtechAGI(offline_mode=True)
    result = agi.load_file(args.file)

    if result.get('success'):
        print(f"\n✅ Successfully processed!")
        print(f"   File: {args.file}")
        print(f"   Chunks: {result.get('chunks', 0)}")
        if 'metadata' in result:
            print(f"   Metadata: {result['metadata']}")
    else:
        print(f"\n❌ Failed to process: {result.get('error', 'Unknown error')}")

    agi.shutdown()


def cmd_search(args):
    """Search knowledge base."""
    from arynoxtech_agi import ArynoxtechAGI

    print(f"Searching for: {args.query}")
    agi = ArynoxtechAGI(offline_mode=True)
    results = agi.search(args.query, limit=args.limit)

    print(f"\n{'='*60}")
    print(f"  Search Results for: {args.query}")
    print(f"{'='*60}")

    if results.get('memory'):
        print(f"\n  Memory ({len(results['memory'])} results):")
        for r in results['memory'][:3]:
            print(f"    - {r.get('content', '')[:100]}...")

    if results.get('data'):
        print(f"\n  Data ({len(results['data'])} results):")
        for r in results['data'][:3]:
            print(f"    - {r.get('source', 'Unknown')}: {r.get('content', '')[:80]}...")

    if results.get('web'):
        print(f"\n  Web ({len(results['web'])} results):")
        for r in results['web'][:3]:
            print(f"    - {r.get('title', 'Unknown')}: {r.get('summary', '')[:80]}...")

    print()


def cmd_version(args):
    """Show version."""
    from arynoxtech_agi import __version__
    print(f"Arynoxtech_AGI v{__version__}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='arynoxtech_agi',
        description='Arynoxtech_AGI - Multi-Domain Adaptive Artificial General Intelligence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  arynoxtech_agi chat                          # Start interactive chat
  arynoxtech_agi api --port 8080              # Start API on port 8080
  arynoxtech_agi status                        # Show AGI status
  arynoxtech_agi domains                       # List available domains
  arynoxtech_agi process document.pdf          # Load and learn from PDF
  arynoxtech_agi search "machine learning"     # Search knowledge base
  arynoxtech_agi version                       # Show version
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Start interactive chat mode')
    chat_parser.add_argument('--offline', action='store_true', default=True, help='Enable offline mode')
    chat_parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    chat_parser.add_argument('--voice', action='store_true', help='Enable voice')
    chat_parser.set_defaults(func=cmd_chat)

    # API command
    api_parser = subparsers.add_parser('api', help='Start API server')
    api_parser.add_argument('--host', default='0.0.0.0', help='Server host')
    api_parser.add_argument('--port', type=int, default=8000, help='Server port')
    api_parser.add_argument('--offline', action='store_true', default=True, help='Enable offline mode')
    api_parser.set_defaults(func=cmd_api)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show AGI status')
    status_parser.set_defaults(func=cmd_status)

    # Domains command
    domains_parser = subparsers.add_parser('domains', help='List available domains')
    domains_parser.set_defaults(func=cmd_domains)

    # Process command
    process_parser = subparsers.add_parser('process', help='Process a file')
    process_parser.add_argument('file', help='File to process')
    process_parser.set_defaults(func=cmd_process)

    # Search command
    search_parser = subparsers.add_parser('search', help='Search knowledge base')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Max results')
    search_parser.set_defaults(func=cmd_search)

    # Version command
    version_parser = subparsers.add_parser('version', help='Show version')
    version_parser.set_defaults(func=cmd_version)

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()