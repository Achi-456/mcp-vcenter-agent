# AgenticOps UI Design System

## Product Style

AgenticOps is a professional infrastructure operations console for vCenter, Agent Engine diagnostics, and safe tool execution. The UI should feel reliable, calm, technical, and clean.

Avoid:
- neon cyberpunk
- overloaded dashboards
- toy-like gradients
- raw JSON everywhere

Prefer:
- clean cards
- readable tables
- clear status badges
- calm operations colors
- strong hierarchy
- compact but not cramped layouts

## Color Palette

Primary navy: `#1B3B6F`

Secondary steel blue: `#2F6690`

Info light blue: `#A3CEF1`

Warm beige: `#F6E4C8`

Warm off-white: `#FFF8EE`

## Semantic Colors

Use the palette plus semantic status colors:

- Online / success: emerald
- Warning: amber
- Critical / blocked: red
- Neutral / disabled: slate
- Info: blue

## Recommended Usage

App background: use `#FFF8EE` or a very light neutral background.

Sidebar: use `#1B3B6F`.

Top bar: use white or `#FFF8EE` with bottom border.

Cards: use white or very soft `#FFF8EE` with subtle borders.

Primary buttons: use `#1B3B6F`.

Secondary buttons: use `#2F6690`.

Info highlights: use `#A3CEF1`.

Soft warning/background sections: use `#F6E4C8`.

## UI Meaning

| UI Element | Color |
| --- | --- |
| Sidebar | `#1B3B6F` |
| Active sidebar item | `#2F6690` |
| Main page background | `#FFF8EE` |
| Cards | white or `#FFF8EE` |
| Soft panels | `#F6E4C8` |
| Info badges | `#A3CEF1` |
| Primary button | `#1B3B6F` |
| Secondary button | `#2F6690` |
| Safe/read-only badge | emerald |
| Approval-required badge | amber |
| Destructive/blocked badge | red |

## Overall Layout

Use a normal infrastructure console layout:

```text
Top Bar: vCenter status | Agent status | Refresh | User
Sidebar: Dashboard, AI Assistant, Inventory, Diagnostics, Tools, System Health, Settings, Sessions
Main Content: page header, cards, tables, chat, forms
```

Sidebar:
- background `#1B3B6F`
- active item `#2F6690`
- bottom service status summary for FastAPI, vCenter, Agent, and MCP

Top bar:
- product name: AgenticOps Console
- vCenter target label, for example `core-infra-vc01.dclab.com`
- API Online
- Agent Online
- MCP Safe
- Last Updated
- Refresh action

## Typography

Use a modern sans-serif:
- Inter
- Geist
- system-ui fallback

Use mono font for:
- VM names
- hostnames
- IP addresses
- tool names
- session IDs

## Component Style

Cards:
- rounded-xl or rounded-2xl
- subtle border
- soft shadow
- good spacing

Tables:
- compact rows
- sticky header if possible
- horizontal scroll
- status badges
- row hover

Chat:
- final answers in readable markdown
- tool traces as collapsible cards
- raw JSON hidden behind "View raw"
- blocked actions visibly marked
- input fixed at the bottom and expands up to 6 lines
- no overlap with browser bottom or Windows taskbar

## Accessibility

- Do not rely on color alone.
- Use icons plus labels.
- Ensure sufficient contrast.
- Avoid tiny text for operational data.
