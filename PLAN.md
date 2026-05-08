# Quantifile Development Plan

## Version 1.0 - Completed Features
- Interactive treemap visualization with color-coded hierarchy
- Drill-down navigation (double-click, zoom out, backspace, enter)
- Arrow key navigation with smart adjacent selection
- Right-click context menu (Open, Color, Properties, Show in Explorer, Go Up)
- Quick zoom toggle for instant right-click zoom out
- Free space visualization toggle with gray blocks
- SVG export with correct fonts and positioning
- Persistent settings (fullscreen, window position, colors)
- Color customization with immediate application
- Context menu color editing for folder and file-type colors
- Organized tabbed Settings dialog with configurable UI and treemap label fonts
- Navigation animation settings with none, zoom, and collapse modes
- Log tab for scan warnings, permission errors, and non-blocking operation messages
- Access-denied folder placeholders with scan summary logging
- Visual indicators for recently modified files with stronger last-hour badges
- Shared scan worker pool capped by Maximum scan threads
- Split main.py into launcher, model, layout, scanner, app shell, and controller mixin modules
- Squarified-style treemap layout algorithm
- Dynamic text truncation based on window width
- Cross-platform file operations and properties
- Enhanced About dialog with license and support link
- MIT license and comprehensive documentation

## Future Enhancements
- Advanced search and filtering (name, type, size, date)
- Bookmark favorite directories
- Multi-selection and batch operations
- Undo/redo for file operations
- Improved error handling and user feedback
- Performance optimizations for large directories
- Plugin system for custom visualizations
- Export to additional formats (PNG, PDF)
- Network drive scanning support
- File type statistics and charts
- Add small tests for human_size, treemap, and temp-folder scanning
