# The Translation Table — Plain English → AppKit → SwiftUI

Source: https://namethatui.com/translate

The same Mac element has two real names, one per framework. Find the thing, take the column your project speaks.

| The Thing | AppKit | SwiftUI |
|-----------|--------|---------|
| Alert | NSAlert | `.alert(…)` or AlertScene |
| Alternating row backgrounds | NSTableView.usesAlternatingRowBackgroundColors | `.alternatingRowBackgrounds(_:)` |
| App menu bar | NSApplication.mainMenu | `.commands { … }` |
| Button | NSButton | Button |
| Checkbox | NSButton with switch type | Toggle + `.toggleStyle(.checkbox)` |
| Color well / color picker | NSColorWell + NSColorPanel | ColorPicker |
| Command group | inserted NSMenuItems | CommandGroup |
| Confirmation dialog | NSAlert | `.confirmationDialog(…)` |
| Context menu | NSView.menu / NSMenu | `.contextMenu { … }` |
| Date picker | NSDatePicker | DatePicker |
| Dialog icon | NSAlert.icon | `.dialogIcon(_:)` |
| Disclosure control | NSButton.BezelStyle.disclosure / NSOutlineView | DisclosureGroup |
| "Don't show again" checkbox | NSAlert.showsSuppressionButton | `.dialogSuppressionToggle(…)` |
| Gauge / level indicator | NSLevelIndicator | Gauge |
| Help button/link | NSHelpManager + NSButton | HelpLink |
| Hierarchical table row | NSOutlineView row | DisclosureTableRow |
| Inspector | NSSplitViewItem.Behavior.inspector / NSInspectorBar / NSPanel | `.inspector(…)` |
| List | NSTableView | List |
| Menu | NSMenu | Menu |
| Menu bar extra / status item | NSStatusItem | MenuBarExtra |
| Menu indicator arrow | NSPopUpButtonCell.arrowPosition | `.menuIndicator(_:)` |
| Menu item keyboard equivalent | NSMenuItem.keyEquivalent | `.keyboardShortcut(_:)` |
| Menu separator | NSMenuItem.separator() | Divider inside a menu |
| Menu-style status item | NSStatusItem + NSMenu | MenuBarExtra + `.menuBarExtraStyle(.menu)` |
| Multi-window scene | NSWindowController instances | WindowGroup |
| Navigation split view | NSSplitViewController | NavigationSplitView |
| Navigation stack (approximate) | NSPageController | NavigationStack |
| Open/import panel | NSOpenPanel | `.fileImporter(…)` |
| Outline / source list | NSOutlineView | OutlineGroup or hierarchical List |
| Palette picker | NSMatrix or NSSegmentedControl | Picker + `.pickerStyle(.palette)` |
| Paste button | NSButton + NSPasteboard | PasteButton |
| Pop-up button | NSPopUpButton with pullsDown = false | Picker + `.pickerStyle(.menu)` |
| Popover | NSPopover | `.popover(…)` |
| Progress bar / spinner | NSProgressIndicator | ProgressView |
| Pull-down button | NSPopUpButton with pullsDown = true | Menu + `.menuStyle(.button)` |
| Radio group | grouped radio-type NSButtons | Picker + `.pickerStyle(.radioGroup)` |
| Rename button | NSButton / responder-chain rename action | RenameButton |
| Resizable split view | NSSplitView | HSplitView / VSplitView |
| Save/export panel | NSSavePanel | `.fileExporter(…)` |
| Search field | NSSearchField | `.searchable(…)` |
| Segmented control | NSSegmentedControl | Picker + `.pickerStyle(.segmented)` |
| Settings window | preferences NSWindowController | Settings |
| Share button / share picker | NSSharingServicePicker | ShareLink |
| Sheet | NSWindow.beginSheet | `.sheet(…)` |
| Sidebar toggle | NSSplitViewController.toggleSidebar(_:) | SidebarCommands / system toolbar item |
| Single window | NSWindow | Window |
| Slider | NSSlider | Slider |
| Stepper | NSStepper | Stepper |
| Switch | NSSwitch | Toggle + `.toggleStyle(.switch)` |
| Tab view | NSTabViewController / NSTabView | TabView + Tab |
| Table | NSTableView | Table |
| Table column | NSTableColumn | TableColumn |
| Table header strip | NSTableHeaderView | `.tableColumnHeaders(_:)` |
| Table row | NSTableRowView | TableRow |
| Toolbar | NSToolbar | `.toolbar { … }` |
| Toolbar customization palette | NSToolbar customization | `.toolbar(id:content:)` |
| Toolbar item | NSToolbarItem | ToolbarItem |
| Toolbar item group | NSToolbarItemGroup | ToolbarItemGroup |
| Toolbar overflow menu | NSToolbar overflow menu | `.toolbarOverflowMenu { … }` |
| Top-level command menu | top-level NSMenuItem + NSMenu | CommandMenu |
| Utility window / tool palette | NSPanel | UtilityWindow |
| Web link | link-style NSTextField + NSWorkspace | Link |
| Window-style status item | NSStatusItem + NSPopover or panel | MenuBarExtra + `.menuBarExtraStyle(.window)` |