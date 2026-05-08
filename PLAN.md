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
- Shared scan worker pool capped by Maximum scan threads
- Dynamic text truncation based on window width
- Cross-platform file operations and properties
- Enhanced About dialog with license and support link
- MIT license and comprehensive documentation

## Future Enhancements
- Squarified treemap algorithm for better aspect ratios
- Advanced search and filtering (name, type, size, date)
- Visual indicators for recently modified or accessed files
- Bookmark favorite directories
- Multi-selection and batch operations
- Undo/redo for file operations
- Improved error handling and user feedback
- Performance optimizations for large directories
- Plugin system for custom visualizations
- Export to additional formats (PNG, PDF)
- Network drive scanning support
- File type statistics and charts
- Move scan error dialogs onto the Tk main thread using self.after(...)
- Split main.py into scanner, treemap, settings, and UI modules
- Add small tests for human_size, treemap, and temp-folder scanning
