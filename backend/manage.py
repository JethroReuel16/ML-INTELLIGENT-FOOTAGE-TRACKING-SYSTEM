"""
Administration commands for the ML Footage Tracking System backend.

    python manage.py create-user --email ana@example.org --name "Ana Phiri"
    python manage.py list-users
    python manage.py set-active --email ana@example.org --inactive

Passwords are prompted for (never passed on the command line, where they
would end up in shell history). For automation, set MLFT_NEW_PASSWORD.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy.exc import IntegrityError

MIN_PASSWORD_LENGTH = 8


def _session():
    from app.database import SessionLocal
    import app.models  # noqa: F401  (register models)

    return SessionLocal()


def _read_password() -> str:
    password = os.getenv("MLFT_NEW_PASSWORD")
    if password:
        return password

    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("error: passwords do not match")
    return password


def create_user(args) -> int:
    from app.api.routes.auth import normalize_email
    from app.models import User
    from app.security import hash_password

    email = normalize_email(args.email)
    if "@" not in email:
        sys.exit("error: invalid email address")

    password = _read_password()
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"error: password must have at least {MIN_PASSWORD_LENGTH} characters")

    db = _session()
    try:
        db.add(User(full_name=args.name.strip(), email=email, hashed_password=hash_password(password), is_active=True))
        db.commit()
    except IntegrityError:
        db.rollback()
        sys.exit(f"error: an account for {email} already exists")
    finally:
        db.close()

    print(f"Created account for {email}.")
    return 0


def list_users(_args) -> int:
    from app.models import User

    db = _session()
    try:
        for user in db.query(User).order_by(User.id):
            status = "active" if user.is_active else "inactive"
            print(f"{user.id:>4}  {status:<8}  {user.email:<40}  {user.full_name}")
    finally:
        db.close()
    return 0


def set_active(args) -> int:
    from app.api.routes.auth import normalize_email
    from app.models import AuthSession, User

    db = _session()
    try:
        user = db.query(User).filter(User.email == normalize_email(args.email)).first()
        if user is None:
            sys.exit("error: no such account")
        user.is_active = not args.inactive
        if args.inactive:
            # Sign the user out everywhere.
            db.query(AuthSession).filter(AuthSession.user_id == user.id).delete(synchronize_session=False)
        db.commit()
        print(f"{user.email} is now {'inactive' if args.inactive else 'active'}.")
    finally:
        db.close()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ML Footage Tracking System administration")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="create an investigator account")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True, help="full name")
    create.set_defaults(func=create_user)

    listing = commands.add_parser("list-users", help="list accounts")
    listing.set_defaults(func=list_users)

    active = commands.add_parser("set-active", help="activate or deactivate an account")
    active.add_argument("--email", required=True)
    active.add_argument("--inactive", action="store_true", help="deactivate (and sign out everywhere)")
    active.set_defaults(func=set_active)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
