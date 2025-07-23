#!/usr/bin/env python3
"""
Test script to demonstrate different edge styling options for ERD generation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pypgsvg import generate_erd

def test_edge_styles():
    """Test different edge styling configurations."""
    
    # Test configurations with different edge styles
    edge_configs = {
        'current': {
            'description': 'Current styling (gradient colors, diamond tail)',
            'style': 'solid',
            'penwidth': '3',
            'arrowsize': '3', 
            'arrowhead': 'normal',
            'arrowtail': 'diamond',
            'color_mode': 'gradient'
        },
        
        'professional': {
            'description': 'Professional look (solid colors, clean arrows)',
            'style': 'solid',
            'penwidth': '2',
            'arrowsize': '2',
            'arrowhead': 'normal', 
            'arrowtail': 'none',
            'color_mode': 'solid',
            'color': '#2E4F99'
        },
        
        'database_notation': {
            'description': 'Database notation (crow\'s foot)',
            'style': 'solid',
            'penwidth': '2',
            'arrowsize': '2',
            'arrowhead': 'crow',
            'arrowtail': 'tee',
            'color_mode': 'solid',
            'color': '#000000'
        },
        
        'subtle': {
            'description': 'Subtle styling (dashed lines, smaller arrows)',
            'style': 'dashed',
            'penwidth': '1.5',
            'arrowsize': '1.5',
            'arrowhead': 'open',
            'arrowtail': 'none', 
            'color_mode': 'solid',
            'color': '#666666'
        },
        
        'bold': {
            'description': 'Bold styling (thick lines, large arrows)',
            'style': 'solid',
            'penwidth': '4',
            'arrowsize': '4',
            'arrowhead': 'normal',
            'arrowtail': 'diamond',
            'color_mode': 'solid',
            'color': '#CC0000'
        }
    }
    
    print("Testing different edge styling configurations...")
    
    for config_name, config in edge_configs.items():
        print(f"\nGenerating ERD with {config['description']}")
        output_file = f"edge_test_{config_name}"
        
        # This would need to be integrated into the main generate_erd function
        # For now, just print the configuration
        print(f"  Output: {output_file}.svg")
        print(f"  Style: {config['style']}")
        print(f"  Pen width: {config['penwidth']}")
        print(f"  Arrow size: {config['arrowsize']}")
        print(f"  Arrow head: {config['arrowhead']}")
        print(f"  Arrow tail: {config['arrowtail']}")
        print(f"  Color mode: {config['color_mode']}")
        if 'color' in config:
            print(f"  Color: {config['color']}")

if __name__ == "__main__":
    test_edge_styles()
