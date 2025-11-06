#!/usr/bin/env python3
"""
Script to create a new super admin user.
"""

import asyncio
import sys
from getpass import getpass

from backend.db.init_db import create_admin_user


async def main():
    """Create a new super admin user interactively."""
    print("🔐 Creating new Super Admin User")
    print("=" * 40)
    
    # Get user input
    email = input("Email address: ").strip()
    if not email:
        print("❌ Email is required!")
        sys.exit(1)
    
    name = input("Full name: ").strip()
    if not name:
        print("❌ Name is required!")
        sys.exit(1)
    
    password = getpass("Password: ").strip()
    if not password:
        print("❌ Password is required!")
        sys.exit(1)
    
    password_confirm = getpass("Confirm password: ").strip()
    if password != password_confirm:
        print("❌ Passwords don't match!")
        sys.exit(1)
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        sys.exit(1)
    
    print(f"\n📝 Creating user: {name} ({email})")
    
    # Create the user
    try:
        user_id = await create_admin_user(
            email=email,
            password=password,
            name=name
        )
        
        if user_id:
            print(f"✅ Super Admin user created successfully!")
            print(f"   User ID: {user_id}")
            print(f"   Email: {email}")
            print(f"   Name: {name}")
            print(f"   Role: super_admin")
            print(f"\n🚀 You can now login with these credentials!")
        else:
            print("❌ Failed to create user (user might already exist)")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())