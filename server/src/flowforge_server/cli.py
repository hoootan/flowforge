"""CLI commands for FlowForge server."""

import argparse
import asyncio
import getpass
import sys

from flowforge_server.config import get_settings
from flowforge_server.db import get_session_context, init_db
from flowforge_server.db.models.user import UserRole
from flowforge_server.services.user import create_user, get_user_by_email


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

        print(f"Admin user created successfully!")
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

    if args.command == "create-admin":
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

    elif args.command == "run" or args.command is None:
        # Default to running the server
        from flowforge_server.main import run
        run()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
