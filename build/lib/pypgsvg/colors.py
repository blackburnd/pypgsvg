import colorsys

# Predefined accessible colors (muted/desaturated versions).
color_palette = [
    "#E8A8A8", "#E8B093", "#E8C093", "#E8D8A8", "#B8D1A8",
    "#93C4B8", "#9BB0C0", "#7BB0C0", "#98B8B8", "#E8B8A8",
    "#C4D8A8", "#E8D8A8", "#7BB8B0", "#6B8B73"
]

def saturate_color(hex_color, saturation_factor=1.8, brightness_factor=1.0):
    """
    Increase the saturation and optionally brightness of a hex color.
    """
    if hex_color and hex_color.startswith('#'):
        hex_color = hex_color[1:]

    # Convert hex to RGB
    r, g, b = int(hex_color[0:2], 16) / 255.0, int(hex_color[2:4], 16) / 255.0, int(hex_color[4:6], 16) / 255.0

    # Convert RGB to HLS
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Increase saturation and brightness, clamping to valid ranges
    s = min(1, s * saturation_factor)
    l = min(1, l * brightness_factor)

    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    # Convert RGB to hex
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))


def desaturate_color(hex_color, desaturation_factor=0.2):
    """
    Heavily desaturate a color for dimming non-highlighted elements.
    """
    if hex_color and hex_color.startswith('#'):
        hex_color = hex_color[1:]

    # Convert hex to RGB
    r, g, b = int(hex_color[0:2], 16) / 255.0, int(hex_color[2:4], 16) / 255.0, int(hex_color[4:6], 16) / 255.0

    # Convert RGB to HLS
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Reduce saturation, clamping to valid range
    s = max(0, s * desaturation_factor)

    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    # Convert back to hex
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))