# Fixes for PR #9

## Issues to Address

### 1. Reaction Persistence (Critical)
- Current reactions are client-side only
- Need to save reactions to comment content with `[reaction:filename]` format
- Add update endpoint for comments

### 2. Dynamic Reaction Loading (Major)
- Replace hardcoded reaction list in /api/reactions
- Fetch from remote YAML at https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/config.yaml
- Cache for performance

### 3. Hardcoded Agent ID (Minor)
- Remove hardcoded 'demo_agent'
- Use random agent selection for demo
- Future: proper auth system

### 4. API Compatibility (Minor)
- Add /api/posts/<id>/flat endpoint for backward compatibility
- Returns flat comment list like original API
