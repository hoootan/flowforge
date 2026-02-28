"""CLI commands for FlowForge server."""

import argparse
import asyncio
import getpass
import sys

from flowforge_server.config import get_settings
from flowforge_server.db import get_session_context, init_db
from flowforge_server.db.models.user import UserRole
from flowforge_server.services.user import create_user, get_user_by_email


async def run_retention_async(
    dry_run: bool = False,
    completed_days: int = 30,
    failed_days: int = 90,
    event_days: int = 30,
    audit_days: int = 365,
) -> None:
    """Run data retention cleanup."""
    from flowforge_server.services.retention import RetentionConfig, RetentionService

    await init_db()

    config = RetentionConfig(
        completed_run_days=completed_days,
        failed_run_days=failed_days,
        processed_event_days=event_days,
        audit_log_days=audit_days,
    )

    async with get_session_context() as session:
        service = RetentionService(session, config)

        if dry_run:
            print("Dry run mode - no data will be deleted\n")
            stats = await service.get_retention_stats()
            print("Eligible for cleanup:")
            for key, value in stats["eligible_for_cleanup"].items():
                print(f"  {key}: {value}")
            print("\nRetention policy:")
            for key, value in stats["retention_config"].items():
                print(f"  {key}: {value} days")
        else:
            print("Running retention cleanup...")
            result = await service.run_cleanup()
            print("\nCleanup complete:")
            print(f"  Runs deleted: {result.runs_deleted}")
            print(f"  Steps deleted: {result.steps_deleted}")
            print(f"  Events deleted: {result.events_deleted}")
            print(f"  Audit logs deleted: {result.audit_logs_deleted}")
            print(f"  Total deleted: {result.total_deleted}")
            if result.errors:
                print(f"\nErrors ({len(result.errors)}):")
                for error in result.errors:
                    print(f"  - {error}")


async def create_admin_async(email: str, password: str, name: str) -> None:
    """Create an admin user."""
    settings = get_settings()

    # Initialize database
    await init_db()

    # Get default tenant ID
    from flowforge_server.api.deps import DEFAULT_TENANT_ID

    async with get_session_context() as session:
        # Check if user already exists
        existing = await get_user_by_email(session, DEFAULT_TENANT_ID, email)
        if existing:
            print(f"Error: User with email {email} already exists")
            sys.exit(1)

        # Create admin user
        user = await create_user(
            session=session,
            tenant_id=DEFAULT_TENANT_ID,
            email=email,
            password=password,
            name=name,
            role=UserRole.ADMIN,
        )

        await session.commit()

        print("Admin user created successfully!")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.name}")
        print(f"  Role: {user.role}")


def create_admin() -> None:
    """CLI command to create an admin user."""
    parser = argparse.ArgumentParser(
        description="Create an admin user for the FlowForge dashboard"
    )
    parser.add_argument(
        "--email",
        "-e",
        required=True,
        help="Admin email address",
    )
    parser.add_argument(
        "--password",
        "-p",
        help="Admin password (will prompt if not provided)",
    )
    parser.add_argument(
        "--name",
        "-n",
        default="Admin",
        help="Admin display name (default: Admin)",
    )

    args = parser.parse_args()

    # Get password interactively if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("Error: Passwords do not match")
            sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)

    asyncio.run(create_admin_async(args.email, password, args.name))


def main() -> None:
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="FlowForge server CLI",
        prog="flowforge-server",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run subcommand (default)
    run_parser = subparsers.add_parser("run", help="Run the FlowForge server")

    # migrate subcommand
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Run database migrations",
    )
    migrate_parser.add_argument(
        "--revision",
        "-r",
        default="head",
        help="Target revision (default: head)",
    )
    migrate_parser.add_argument(
        "--downgrade",
        "-d",
        action="store_true",
        help="Downgrade instead of upgrade",
    )

    # retention subcommand
    retention_parser = subparsers.add_parser(
        "retention",
        help="Run data retention cleanup",
    )
    retention_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    retention_parser.add_argument(
        "--completed-days",
        type=int,
        default=30,
        help="Days to keep completed runs (default: 30)",
    )
    retention_parser.add_argument(
        "--failed-days",
        type=int,
        default=90,
        help="Days to keep failed runs (default: 90)",
    )
    retention_parser.add_argument(
        "--event-days",
        type=int,
        default=30,
        help="Days to keep processed events (default: 30)",
    )
    retention_parser.add_argument(
        "--audit-days",
        type=int,
        default=365,
        help="Days to keep audit logs (default: 365)",
    )

    # create-admin subcommand
    admin_parser = subparsers.add_parser(
        "create-admin",
        help="Create an admin user for the dashboard",
    )
    admin_parser.add_argument(
        "--email",
        "-e",
        required=True,
        help="Admin email address",
    )
    admin_parser.add_argument(
        "--password",
        "-p",
        help="Admin password (will prompt if not provided)",
    )
    admin_parser.add_argument(
        "--name",
        "-n",
        default="Admin",
        help="Admin display name (default: Admin)",
    )

    args = parser.parse_args()

    if args.command == "migrate":
        import os
        import subprocess

        # Change to server directory for alembic
        server_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        if args.downgrade:
            cmd = ["alembic", "downgrade", args.revision]
        else:
            cmd = ["alembic", "upgrade", args.revision]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=server_dir)
        sys.exit(result.returncode)

    elif args.command == "create-admin":
        # Get password interactively if not provided
        password = args.password
        if not password:
            password = getpass.getpass("Enter password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("Error: Passwords do not match")
                sys.exit(1)

        if len(password) < 8:
            print("Error: Password must be at least 8 characters")
            sys.exit(1)

        asyncio.run(create_admin_async(args.email, password, args.name))

    elif args.command == "retention":
        asyncio.run(run_retention_async(
            dry_run=args.dry_run,
            completed_days=args.completed_days,
            failed_days=args.failed_days,
            event_days=args.event_days,
            audit_days=args.audit_days,
        ))

    elif args.command == "run" or args.command is None:
        # Default to running the server
        from flowforge_server.main import run
        run()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
