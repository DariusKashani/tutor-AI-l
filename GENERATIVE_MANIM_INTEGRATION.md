# Generative-Manim Integration

This document describes the integration of the generative-manim approach into our Math Tutorial Generator system.

## Overview

The generative-manim integration enhances our ability to generate high-quality Manim animations without relying on LaTeX, which can be problematic due to dependency issues. This approach uses a more robust prompting strategy and post-processing to ensure the generated code works correctly.

## Key Components

1. **src/backend/generative_manim_integration.py**: The main integration module that provides functions to generate Manim code using the generative-manim approach.

2. **Modified manim_generator.py**: Updated to use the generative-manim integration when available.

3. **Updated test_video_generator.py**: Added support for toggling the generative-manim approach.

## How It Works

1. The integration loads Manim documentation from the generative-manim project to provide better context for the AI model.

2. It uses a carefully crafted system prompt that includes specific guidance on common Manim issues:
   - Using Text() instead of Tex() to avoid LaTeX dependencies
   - Proper usage of RightAngle, Sector, and Angle objects
   - Creating custom shapes for checkmarks
   - Positioning objects explicitly to avoid overlaps

3. Post-processing is applied to the generated code to fix common issues:
   - RightAngle usage with polygons
   - Sector parameter naming (radius vs outer_radius)
   - Angle constructor parameter issues
   - Tex/MathTex replacement with Text

## Usage

To use the generative-manim integration:

```bash
# Use generative-manim (default)
python test_video_generator.py --topic "Simple Triangle" --duration 1

# Disable generative-manim
python test_video_generator.py --topic "Simple Triangle" --duration 1 --no-generative-manim
```

## Benefits

1. **No LaTeX Dependencies**: By using Text() instead of Tex(), we avoid LaTeX compilation issues.

2. **Better Error Handling**: Post-processing catches and fixes common errors before they cause rendering failures.

3. **Improved Code Quality**: The enhanced prompting strategy results in more consistent and reliable Manim code.

## Limitations

1. **Text Rendering**: Without LaTeX, mathematical expressions are limited to what can be represented with plain text.

2. **Rendering Issues**: Some complex animations may still fail to render due to Manim version differences or other issues.

## Future Improvements

1. **Enhanced Post-Processing**: Add more patterns to catch and fix common issues.

2. **Custom Manim Subclasses**: Create simplified versions of common Manim objects that are less error-prone.

3. **Fallback Rendering**: Implement a more robust fallback rendering system for when animations fail. 