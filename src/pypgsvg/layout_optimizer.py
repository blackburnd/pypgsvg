"""
Layout optimizer for Graphviz ERD diagrams.

Provides both heuristic-based and AI-powered optimization for Graphviz layout settings
to prevent node overlaps and improve readability.
"""
import os
import json
from typing import Dict, Any, Tuple, Optional


def analyze_schema_complexity(tables: Dict, foreign_keys: list, views: Dict, triggers: Dict) -> Dict[str, Any]:
    """
    Analyze schema to determine complexity metrics.

    Returns:
        Dict with metrics like table_count, fk_count, avg_columns, etc.
    """
    table_count = len(tables)
    fk_count = len(foreign_keys)
    view_count = len(views)
    trigger_count = sum(len(t) for t in triggers.values())

    # Calculate average columns per table
    total_columns = sum(len(t.get('columns', [])) for t in tables.values())
    avg_columns = total_columns / table_count if table_count > 0 else 0

    # Calculate connectivity (average FK per table)
    connectivity = fk_count / table_count if table_count > 0 else 0

    # Determine if schema is densely connected
    is_dense = connectivity > 2.0

    # Estimate graph dimensions based on table count
    is_large = table_count > 20
    is_very_large = table_count > 50

    return {
        'table_count': table_count,
        'fk_count': fk_count,
        'view_count': view_count,
        'trigger_count': trigger_count,
        'avg_columns': avg_columns,
        'connectivity': connectivity,
        'is_dense': is_dense,
        'is_large': is_large,
        'is_very_large': is_very_large
    }


def heuristic_optimize_layout(current_settings: Dict[str, Any], complexity: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Use heuristic rules to optimize Graphviz layout settings.
    STARTS with user's current settings and only suggests improvements.

    Args:
        current_settings: User's current Graphviz settings (their defaults)
        complexity: Schema complexity metrics from analyze_schema_complexity

    Returns:
        Tuple of (optimized_settings dict, explanation string)
    """
    # START with user's current settings (DO NOT CHANGE THE DEFAULT)
    settings = current_settings.copy()
    direction = settings.get('rankdir', 'TB')

    explanations = []

    # Base settings
    table_count = complexity['table_count']
    fk_count = complexity['fk_count']
    connectivity = complexity['connectivity']
    is_dense = complexity['is_dense']
    is_large = complexity['is_large']
    is_very_large = complexity['is_very_large']

    # Pack mode based on direction and density
    if direction in ['LR', 'RL']:
        # Horizontal layouts benefit from cluster packing
        settings['packmode'] = 'cluster'
        explanations.append("Using cluster packmode for horizontal layout")
    elif is_dense:
        settings['packmode'] = 'graph'
        explanations.append("Using graph packmode for densely connected schema")
    else:
        settings['packmode'] = 'array'
        explanations.append("Using array packmode for clean alignment")

    # Edge separation - critical for preventing overlap
    if is_dense:
        settings['esep'] = '12' if fk_count > 50 else '10'
        explanations.append(f"Increased edge separation to {settings['esep']} to prevent overlap")
    elif fk_count > 20:
        settings['esep'] = '8'
    else:
        settings['esep'] = '6'

    # Node and rank separation based on direction and size
    if direction in ['TB', 'BT']:
        # Vertical layout - prioritize node separation
        if is_very_large:
            settings['node_sep'] = '0.8'
            settings['rank_sep'] = '1.5'
            explanations.append("Increased separations for very large schema")
        elif is_large:
            settings['node_sep'] = '0.6'
            settings['rank_sep'] = '1.3'
            explanations.append("Moderate separations for large schema")
        else:
            settings['node_sep'] = '0.5'
            settings['rank_sep'] = '1.0'
    else:
        # Horizontal layout - prioritize rank separation
        if is_very_large:
            settings['node_sep'] = '0.6'
            settings['rank_sep'] = '2.0'
            explanations.append("Increased rank separation for horizontal layout")
        elif is_large:
            settings['node_sep'] = '0.5'
            settings['rank_sep'] = '1.6'
        else:
            settings['node_sep'] = '0.5'
            settings['rank_sep'] = '1.3'

    # Font sizes based on schema size
    if is_very_large:
        settings['fontsize'] = 14
        settings['node_fontsize'] = 11
        settings['edge_fontsize'] = 9
        explanations.append("Reduced font sizes for large schema visibility")
    elif is_large:
        settings['fontsize'] = 16
        settings['node_fontsize'] = 12
        settings['edge_fontsize'] = 10
    else:
        settings['fontsize'] = 18
        settings['node_fontsize'] = 14
        settings['edge_fontsize'] = 12

    # Node style and shape
    settings['node_style'] = 'rounded,filled'
    settings['node_shape'] = 'rect'
    settings['fontname'] = 'Arial'

    explanation = "; ".join(explanations)
    return settings, explanation


def ai_optimize_layout(current_settings: Dict[str, Any], complexity: Dict[str, Any],
                       heuristic_settings: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Use AI (Claude API) to enhance layout optimization.
    STARTS with user's current settings.

    Args:
        current_settings: User's current Graphviz settings (their defaults)
        complexity: Schema complexity metrics
        heuristic_settings: Settings from heuristic optimizer

    Returns:
        Tuple of (enhanced_settings dict, explanation string) or None if API unavailable
    """
    # Check if Anthropic API key is available
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        direction = current_settings.get('rankdir', 'TB')

        # Prepare analysis prompt for Claude
        prompt = f"""Analyze this database schema structure and recommend optimal Graphviz layout settings for maximum human readability.

CRITICAL REQUIREMENTS:
1. **No Overlapping Nodes**: Nodes (tables/views) must NEVER overlap. This is the #1 priority.
2. **No Overlapping Edges**: Relationship lines must not overlap nodes or be hidden behind them.
3. **Intentional Whitespace**: Generous whitespace improves readability. Don't be afraid of larger separations.
4. **Human-First Design**: This diagram will be read by humans, not machines. Clarity > compactness.
5. **Clear Relationships**: Edge paths should be easy to trace visually.
6. **PRESERVE USER DEFAULTS**: Start from the user's current settings. Only suggest changes to prevent overlaps.

User's Current Settings (their defaults - preserve these unless changes are needed):
{json.dumps(current_settings, indent=2)}

Schema Complexity:
- Tables: {complexity['table_count']}
- Foreign Keys: {complexity['fk_count']} relationships
- Views: {complexity['view_count']}
- Connectivity: {complexity['connectivity']:.2f} (avg FKs per table)
- Dense Schema: {complexity['is_dense']}
- Large Schema: {complexity['is_large']}

Current Direction: {direction} ({{'TB': 'Top to Bottom', 'LR': 'Left to Right', 'BT': 'Bottom to Top', 'RL': 'Right to Left'}}[direction])

Heuristic Baseline (you can improve on this):
{json.dumps(heuristic_settings, indent=2)}

OPTIMIZATION GUIDELINES:
- For densely connected schemas (connectivity > 2.0): Increase esep significantly (10-15)
- For large schemas (>20 tables): Use smaller fonts but maintain readability
- For horizontal layouts (LR/RL): Increase rank_sep more than node_sep
- For vertical layouts (TB/BT): Increase node_sep more than rank_sep
- Whitespace is GOOD - err on the side of more separation rather than less

Respond with ONLY a JSON object in this exact format:
{{
  "packmode": "array|cluster|graph",
  "esep": "number",
  "node_sep": "number",
  "rank_sep": "number",
  "fontsize": number,
  "node_fontsize": number,
  "edge_fontsize": number,
  "explanation": "Brief explanation of key optimizations"
}}"""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse Claude's response
        response_text = message.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()

        ai_result = json.loads(response_text)

        # Merge with heuristic settings (AI enhancements take precedence)
        enhanced_settings = heuristic_settings.copy()
        enhanced_settings.update({k: v for k, v in ai_result.items() if k != 'explanation'})

        explanation = ai_result.get('explanation', 'AI-enhanced optimization applied')

        return enhanced_settings, f"AI-Enhanced: {explanation}"

    except Exception as e:
        print(f"AI optimization failed: {e}")
        return None


def optimize_layout(current_settings: Dict[str, Any], tables: Dict, foreign_keys: list,
                   views: Dict, triggers: Dict, use_ai: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Main entry point for layout optimization.
    STARTS with user's current settings and only suggests improvements.

    Args:
        current_settings: User's current Graphviz settings (THEIR DEFAULTS - DO NOT CHANGE)
        tables: Table definitions
        foreign_keys: Foreign key relationships
        views: View definitions
        triggers: Trigger definitions
        use_ai: Whether to attempt AI enhancement

    Returns:
        Tuple of (optimized_settings dict, explanation string)
    """
    # Analyze schema complexity
    complexity = analyze_schema_complexity(tables, foreign_keys, views, triggers)

    # Start with heuristic optimization (using user's current settings as baseline)
    heuristic_settings, heuristic_explanation = heuristic_optimize_layout(current_settings, complexity)

    # Try AI enhancement if enabled (also starts from user's current settings)
    if use_ai:
        ai_result = ai_optimize_layout(current_settings, complexity, heuristic_settings)
        if ai_result:
            return ai_result

    # Fall back to heuristic optimization
    return heuristic_settings, heuristic_explanation
