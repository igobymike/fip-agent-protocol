#!/usr/bin/env python3
"""FIP Agent Setup Wizard — interactive first-time configuration."""
import json
import os
import subprocess
import sys
from pathlib import Path

FIP_DIR = Path.home() / ".openclaw" / "fip"
KEYS_DIR = FIP_DIR / "keys"
CONFIG_PATH = FIP_DIR / "config.yaml"
DB_PATH = FIP_DIR / "fip.db"

def main():
    if CONFIG_PATH.exists():
        print(f"FIP already configured at {CONFIG_PATH}")
        print("Delete the config file to re-run setup.")
        return

    print("=" * 50)
    print("  FIP Agent Setup")
    print("  Agent-to-Agent Messaging")
    print("=" * 50)
    print()

    # Agent name
    agent_name = input("What should your agent be called on the FIP network?\n> ").strip().lower()
    if not agent_name:
        print("Error: agent name is required.")
        sys.exit(1)

    # Domain
    print()
    has_domain = input("Do you have your own domain? (y/n)\n> ").strip().lower()

    if has_domain in ("y", "yes"):
        domain = input("Enter your domain (e.g., marcus.baiteks.com):\n> ").strip()
        agent_address = f"{agent_name}@{domain}"
        hub_hosted = False
    else:
        agent_address = f"{agent_name}@hub.baiteks.com"
        hub_hosted = True
        domain = "hub.baiteks.com"

    # Generate keys
    print()
    print("Generating Ed25519 keypair...")
    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        private_key = Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        priv_bytes = private_key.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
            serialization.NoEncryption()
        )

        import base64
        pub_b64 = base64.b64encode(pub_bytes).decode()
        priv_b64 = base64.b64encode(priv_bytes).decode()

        (KEYS_DIR / "agent.pub").write_text(f"ed25519:{pub_b64}\n")
        (KEYS_DIR / "agent.key").write_text(f"ed25519:{priv_b64}\n")
        os.chmod(KEYS_DIR / "agent.key", 0o600)
        print(f"  ✓ Keys saved to {KEYS_DIR}/")

    except ImportError:
        # Fallback: use ssh-keygen
        subprocess.run([
            "ssh-keygen", "-t", "ed25519", "-f", str(KEYS_DIR / "agent"),
            "-N", "", "-q"
        ], check=True)
        print(f"  ✓ Keys generated via ssh-keygen at {KEYS_DIR}/")
        pub_b64 = (KEYS_DIR / "agent.pub").read_text().strip()

    # Write config
    FIP_DIR.mkdir(parents=True, exist_ok=True)
    config = f"""# FIP Agent Configuration
agent:
  address: "{agent_address}"
  name: "{agent_name}"

server:
  port: 8780
  host: "0.0.0.0"

database:
  path: "{DB_PATH}"

hub:
  enabled: {str(hub_hosted).lower()}
  url: "https://hub.baiteks.com"
  # token: ""  # Set after hub registration

keys:
  public: "{KEYS_DIR / 'agent.pub'}"
  private: "{KEYS_DIR / 'agent.key'}"

delivery:
  method: "forced_injection"
  banner: true
"""
    CONFIG_PATH.write_text(config)
    print(f"  ✓ Config saved to {CONFIG_PATH}")

    # Initialize database
    print()
    print("Initializing database...")
    # Import from skill's own modules
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    from fip_db import init_db
    init_db(str(DB_PATH))
    print(f"  ✓ Database created at {DB_PATH}")

    # Summary
    print()
    print("=" * 50)
    print("  ✅ FIP Setup Complete!")
    print("=" * 50)
    print()
    print(f"  Your agent address: {agent_address}")
    print(f"  Config: {CONFIG_PATH}")
    print(f"  Database: {DB_PATH}")
    print(f"  Keys: {KEYS_DIR}/")
    print()

    if hub_hosted:
        print("  Next step: Register with the hub")
        print("  Run: python3 scripts/fip_hub_register.py")
    else:
        print("  Next step: Add a route in your reverse proxy")
        print(f"  Route /fip → localhost:8780")
        print(f"  Route /.well-known/fip.json → FIP discovery doc")

    print()
    print("  Share your address with friends so their agents")
    print("  can message yours!")

if __name__ == "__main__":
    main()
