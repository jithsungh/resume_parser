"""
Build roles mapping from CANONICAL_ROLES configuration
"""

import os
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from config.roles import CANONICAL_ROLES


def build_roles_map():
    """Build a flat mapping from all variants to canonical roles"""
    roles_map = {}
    
    for canonical, variants in CANONICAL_ROLES.items():
        # Add canonical role itself
        roles_map[canonical.lower()] = canonical
        
        # Add all variants
        for variant in variants:
            roles_map[variant.lower()] = canonical
    
    return roles_map


def get_canonical_role(role_text: str, roles_map: dict) -> str:
    """Get canonical role from role text"""
    role_lower = role_text.lower().strip()
    
    # Direct match
    if role_lower in roles_map:
        return roles_map[role_lower]
    
    # Partial match
    for variant, canonical in roles_map.items():
        if variant in role_lower or role_lower in variant:
            return canonical
    
    # Return original cleaned
    return ' '.join(word.capitalize() for word in role_text.split())


if __name__ == "__main__":
    roles_map = build_roles_map()
    print(f"Built roles map with {len(roles_map)} entries")
    
    # Test some examples
    test_roles = [
        "software engineer",
        "react developer",
        "full stack dev",
        "sde-2",
        "frontend engineer"
    ]
    
    for role in test_roles:
        canonical = get_canonical_role(role, roles_map)
        print(f"{role:30} -> {canonical}")
