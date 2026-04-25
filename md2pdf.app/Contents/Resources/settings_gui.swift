// md2pdf — unified settings dialog (native Cocoa)
// Compile: swiftc -o settings_gui settings_gui.swift -framework Cocoa -framework Quartz
// Usage: ./settings_gui [file1.md file2.md ...]
// Output: theme|cover|toc|watermark|subtitle|openPdf|outputDir|author|coverImage|customThemePath|tocDepth|margins|pageSize|template|html|title|coverTop|merge|h1Titles|imageDir|duplex|h2Break|justify|lineNumbers|renumber|chapterPage|qr|copyId|authorOnCover|coverPattern|fileOrder

import Cocoa
import Quartz
import UniformTypeIdentifiers

let bundleId = "com.local.md2pdf"

let themes = ["teal", "blue", "purple", "red", "green", "orange", "navy", "rose", "brown", "dark"]
let themeColors: [String: NSColor] = [
    "teal": NSColor(red: 0.10, green: 0.42, blue: 0.36, alpha: 1),
    "blue": NSColor(red: 0.10, green: 0.29, blue: 0.55, alpha: 1),
    "purple": NSColor(red: 0.36, green: 0.18, blue: 0.55, alpha: 1),
    "red": NSColor(red: 0.55, green: 0.10, blue: 0.18, alpha: 1),
    "green": NSColor(red: 0.18, green: 0.49, blue: 0.20, alpha: 1),
    "orange": NSColor(red: 0.90, green: 0.32, blue: 0.00, alpha: 1),
    "navy": NSColor(red: 0.10, green: 0.14, blue: 0.49, alpha: 1),
    "rose": NSColor(red: 0.68, green: 0.08, blue: 0.34, alpha: 1),
    "brown": NSColor(red: 0.31, green: 0.20, blue: 0.18, alpha: 1),
    "dark": NSColor(red: 0.18, green: 0.22, blue: 0.28, alpha: 1),
]

let tocDepths = [
    ("Sections only (##)", "2"),
    ("Subsections (###)", "3"),
    ("Paragraphs (####)", "4"),
]

let marginPresets = [
    ("Narrow", "narrow"),
    ("Medium", "medium"),
    ("Wide", "wide"),
]

let pageSizes = [
    ("A4", "a4"),
    ("A4 landscape", "a4-landscape"),
    ("Letter", "letter"),
    ("Letter landscape", "letter-landscape"),
    ("A3", "a3"),
    ("A3 landscape", "a3-landscape"),
]

let docTemplates = [
    ("No template", ""),
    ("Lecture", "lecture"),
    ("Notes", "notes"),
    ("Manual", "manual"),
    ("Report", "report"),
    ("Cheatsheet", "cheatsheet"),
]

let h2Breaks = [
    ("Every ## on a new page", "always"),
    ("Conditional break", "auto"),
    ("No break", "never"),
]

let coverPatterns = [
    ("Circles", "circles"),
    ("Diamonds", "diamonds"),
    ("Lines", "lines"),
    ("Dots", "dots"),
    ("None", "none"),
]

// --- Preferences ---

func readPref(_ key: String, _ fallback: String = "") -> String {
    UserDefaults.standard.addSuite(named: bundleId)
    let val = UserDefaults(suiteName: bundleId)?.string(forKey: key) ?? ""
    return val.isEmpty ? fallback : val
}

func writePref(_ key: String, _ val: String) {
    UserDefaults(suiteName: bundleId)?.set(val, forKey: key)
}

// --- Flipped view for scroll content (y=0 at top) ---

class FlippedView: NSView {
    override var isFlipped: Bool { true }
}

// --- Dialog ---

class SettingsDialog: NSObject, NSWindowDelegate {
    var window: NSWindow!
    var result = "CANCEL"

    // Theme swatches
    var themeSwatches: [NSView] = []
    var selectedThemeIdx: Int = 0
    var jsonThemeBtn: NSButton!

    // Controls
    var coverCheck: NSButton!
    var tocCheck: NSButton!
    var openCheck: NSButton!
    var duplexCheck: NSButton!
    var depthPopup: NSPopUpButton!
    var marginsPopup: NSPopUpButton!
    var pageSizePopup: NSPopUpButton!
    var templatePopup: NSPopUpButton!
    var h2BreakPopup: NSPopUpButton!
    var coverPatternPopup: NSPopUpButton!
    var htmlCheck: NSButton!
    var mergeCheck: NSButton!
    var justifyCheck: NSButton!
    var lineNumsCheck: NSButton!
    var previewImageView: NSImageView!
    var previewSpinner: NSProgressIndicator!
    var titleField: NSTextField!
    var coverTopField: NSTextField!
    var wmField: NSTextField!
    var subField: NSTextField!
    var authorField: NSTextField!
    var authorOnCoverCheck: NSButton!
    var folderLabel: NSTextField!
    var coverPathLabel: NSTextField!
    var imgDirLabel: NSTextField!
    var folderResetBtn: NSButton!
    var coverResetBtn: NSButton!
    var imgDirResetBtn: NSButton!
    var okButton: NSButton!

    var previewHeaderLabel: NSTextField!
    var previewShadowView: NSView!
    var h1TitleFields: [NSTextField] = []
    var mergeFileLabels: [NSTextField] = []
    var mergeScrollView: NSScrollView!
    var mergeHeaderLabel: NSTextField!
    var renumberCheck: NSButton!
    var chapterPageCheck: NSButton!
    var qrCheck: NSButton!
    var copyIdCheck: NSButton!
    var storedFiles: [String] = []

    var coverImagePath = ""
    var customThemePath = ""
    var outputDir = ""
    var imageDirPath = ""

    var selectedThemeName: String {
        if selectedThemeIdx >= 0 && selectedThemeIdx < themes.count {
            return themes[selectedThemeIdx]
        }
        return "custom"
    }

    var currentThemeColor: NSColor {
        if selectedThemeIdx >= 0 && selectedThemeIdx < themes.count {
            return themeColors[themes[selectedThemeIdx]] ?? .controlAccentColor
        }
        return .controlAccentColor
    }

    func run(files: [String]) -> String {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)

        // Restore persisted paths
        outputDir = readPref("outputDir", "")
        coverImagePath = readPref("coverImagePath", "")
        imageDirPath = readPref("imageDirPath", "")
        customThemePath = readPref("customThemePath", "")

        // Validate persisted paths
        let fm = FileManager.default
        if !outputDir.isEmpty && !fm.fileExists(atPath: outputDir) { outputDir = "" }
        if !coverImagePath.isEmpty && !fm.fileExists(atPath: coverImagePath) { coverImagePath = "" }
        if !imageDirPath.isEmpty && !fm.fileExists(atPath: imageDirPath) { imageDirPath = "" }
        if !customThemePath.isEmpty && !fm.fileExists(atPath: customThemePath) { customThemePath = "" }

        // Resolve saved theme
        let saved = readPref("theme", "teal")
        if saved == "custom" && !customThemePath.isEmpty {
            selectedThemeIdx = -1
        } else if let idx = themes.firstIndex(of: saved) {
            selectedThemeIdx = idx
        } else {
            selectedThemeIdx = 0
        }

        let w: CGFloat = 640
        let h: CGFloat = 700
        let screen = NSScreen.main!.frame
        let x = (screen.width - w) / 2
        let y = (screen.height - h) / 2

        window = NSWindow(
            contentRect: NSRect(x: x, y: y, width: w, height: h),
            styleMask: [.titled, .closable],
            backing: .buffered, defer: false
        )
        window.title = "md2pdf - Settings"
        window.delegate = self
        window.isReleasedWhenClosed = false

        let content = window.contentView!
        content.wantsLayer = true
        var yPos = h - 10

        // --- Files ---
        if !files.isEmpty {
            yPos -= 16
            let label = makeLabel("Files:", bold: true)
            label.frame = NSRect(x: 16, y: yPos, width: 380, height: 18)
            content.addSubview(label)

            let names = files.prefix(5).map { (URL(fileURLWithPath: $0).lastPathComponent) }
            var fileText = names.joined(separator: ", ")
            if files.count > 5 { fileText += " ... and \(files.count - 5) more" }
            yPos -= 18
            let fLabel = makeLabel(fileText, size: 11, color: .secondaryLabelColor)
            fLabel.frame = NSRect(x: 16, y: yPos, width: 388, height: 18)
            content.addSubview(fLabel)
            yPos -= 8
        }

        // --- Separator ---
        yPos -= 8
        content.addSubview(makeSeparator(y: yPos, width: w))

        // --- Style ---
        let styleSectionTop = yPos
        yPos -= 24
        let styleLabel = makeLabel("Style", bold: true, size: 12)
        styleLabel.frame = NSRect(x: 16, y: yPos, width: 200, height: 18)
        content.addSubview(styleLabel)

        // Theme - color swatches
        yPos -= 28
        content.addSubview(makeFieldLabel("Theme:", y: yPos))

        let swatchSize: CGFloat = 20
        let swatchGap: CGFloat = 4
        for (idx, themeName) in themes.enumerated() {
            let sx = 110 + CGFloat(idx) * (swatchSize + swatchGap)
            let swatch = NSView(frame: NSRect(x: sx, y: yPos, width: swatchSize, height: swatchSize))
            swatch.wantsLayer = true
            swatch.layer?.cornerRadius = swatchSize / 2
            swatch.layer?.backgroundColor = (themeColors[themeName] ?? NSColor.gray).cgColor
            let click = NSClickGestureRecognizer(target: self, action: #selector(swatchClicked(_:)))
            swatch.addGestureRecognizer(click)
            content.addSubview(swatch)
            themeSwatches.append(swatch)
        }
        updateSwatchBorders()

        let jsonX = 110 + CGFloat(themes.count) * (swatchSize + swatchGap) + 6
        jsonThemeBtn = NSButton(frame: NSRect(x: jsonX, y: yPos - 2, width: 48, height: 22))
        jsonThemeBtn.title = "JSON..."
        jsonThemeBtn.bezelStyle = .rounded
        jsonThemeBtn.font = NSFont.systemFont(ofSize: 10)
        jsonThemeBtn.target = self
        jsonThemeBtn.action = #selector(loadCustomTheme)
        if selectedThemeIdx == -1 {
            jsonThemeBtn.contentTintColor = .controlAccentColor
            jsonThemeBtn.toolTip = (customThemePath as NSString).lastPathComponent
        }
        content.addSubview(jsonThemeBtn)

        // Checkboxes 2x2
        yPos -= 30
        coverCheck = makeCheck("Cover", checked: readPref("cover", "yes") == "yes")
        coverCheck.frame = NSRect(x: 16, y: yPos, width: 90, height: 20)
        content.addSubview(coverCheck)

        coverPatternPopup = NSPopUpButton(frame: NSRect(x: 106, y: yPos - 2, width: 88, height: 22))
        coverPatternPopup.font = NSFont.systemFont(ofSize: 10)
        coverPatternPopup.controlSize = .small
        for (label, _) in coverPatterns { coverPatternPopup.addItem(withTitle: label) }
        let savedPattern = readPref("coverPattern", "circles")
        if let idx = coverPatterns.firstIndex(where: { $0.1 == savedPattern }) {
            coverPatternPopup.selectItem(at: idx)
        }
        content.addSubview(coverPatternPopup)

        tocCheck = makeCheck("Table of contents", checked: readPref("toc", "yes") == "yes")
        tocCheck.frame = NSRect(x: 200, y: yPos, width: 170, height: 20)
        content.addSubview(tocCheck)

        yPos -= 24
        openCheck = makeCheck("Open PDF", checked: readPref("openPdf", "yes") == "yes")
        openCheck.frame = NSRect(x: 16, y: yPos, width: 150, height: 20)
        content.addSubview(openCheck)

        duplexCheck = makeCheck("Duplex", checked: readPref("duplex", "no") == "yes")
        duplexCheck.frame = NSRect(x: 200, y: yPos, width: 100, height: 20)
        content.addSubview(duplexCheck)

        qrCheck = makeCheck("QR code", checked: readPref("qr", "no") == "yes")
        qrCheck.frame = NSRect(x: 310, y: yPos, width: 100, height: 20)
        content.addSubview(qrCheck)

        copyIdCheck = makeCheck("Copy ID", checked: readPref("copyId", "no") == "yes")
        copyIdCheck.frame = NSRect(x: 410, y: yPos, width: 100, height: 20)
        content.addSubview(copyIdCheck)

        // TOC depth
        yPos -= 30
        content.addSubview(makeFieldLabel("TOC:", y: yPos))

        depthPopup = NSPopUpButton(frame: NSRect(x: 110, y: yPos - 2, width: 220, height: 26))
        for (label, _) in tocDepths { depthPopup.addItem(withTitle: label) }
        let savedDepth = readPref("tocDepth", "2")
        if let idx = tocDepths.firstIndex(where: { $0.1 == savedDepth }) {
            depthPopup.selectItem(at: idx)
        }
        content.addSubview(depthPopup)

        // Margins
        yPos -= 30
        content.addSubview(makeFieldLabel("Margins:", y: yPos))

        marginsPopup = NSPopUpButton(frame: NSRect(x: 110, y: yPos - 2, width: 220, height: 26))
        for (label, _) in marginPresets { marginsPopup.addItem(withTitle: label) }
        let savedMargins = readPref("margins", "medium")
        if let idx = marginPresets.firstIndex(where: { $0.1 == savedMargins }) {
            marginsPopup.selectItem(at: idx)
        }
        content.addSubview(marginsPopup)

        // Page size
        yPos -= 30
        content.addSubview(makeFieldLabel("Page:", y: yPos))

        pageSizePopup = NSPopUpButton(frame: NSRect(x: 110, y: yPos - 2, width: 220, height: 26))
        for (label, _) in pageSizes { pageSizePopup.addItem(withTitle: label) }
        let savedPageSize = readPref("pageSize", "a4")
        if let idx = pageSizes.firstIndex(where: { $0.1 == savedPageSize }) {
            pageSizePopup.selectItem(at: idx)
        }
        content.addSubview(pageSizePopup)

        // Template
        yPos -= 30
        content.addSubview(makeFieldLabel("Template:", y: yPos))

        templatePopup = NSPopUpButton(frame: NSRect(x: 110, y: yPos - 2, width: 220, height: 26))
        for (label, _) in docTemplates { templatePopup.addItem(withTitle: label) }
        let savedTemplate = readPref("template", "")
        if let idx = docTemplates.firstIndex(where: { $0.1 == savedTemplate }) {
            templatePopup.selectItem(at: idx)
        }
        content.addSubview(templatePopup)

        // Break before ##
        yPos -= 30
        content.addSubview(makeFieldLabel("## break:", y: yPos))

        h2BreakPopup = NSPopUpButton(frame: NSRect(x: 110, y: yPos - 2, width: 220, height: 26))
        for (label, _) in h2Breaks { h2BreakPopup.addItem(withTitle: label) }
        let savedH2Break = readPref("h2Break", "always")
        if let idx = h2Breaks.firstIndex(where: { $0.1 == savedH2Break }) {
            h2BreakPopup.selectItem(at: idx)
        }
        content.addSubview(h2BreakPopup)

        // HTML version + Merge
        yPos -= 26
        htmlCheck = makeCheck("Also HTML version", checked: readPref("html", "no") == "yes")
        htmlCheck.frame = NSRect(x: 16, y: yPos, width: 200, height: 20)
        content.addSubview(htmlCheck)

        mergeCheck = makeCheck("Merge into one PDF", checked: readPref("merge", "no") == "yes")
        mergeCheck.frame = NSRect(x: 200, y: yPos, width: 200, height: 20)
        content.addSubview(mergeCheck)

        // Justify + line numbers
        yPos -= 24
        justifyCheck = makeCheck("Justify", checked: readPref("justify", "yes") == "yes")
        justifyCheck.frame = NSRect(x: 16, y: yPos, width: 150, height: 20)
        content.addSubview(justifyCheck)

        lineNumsCheck = makeCheck("Code line numbers", checked: readPref("lineNumbers", "yes") == "yes")
        lineNumsCheck.frame = NSRect(x: 200, y: yPos, width: 180, height: 20)
        content.addSubview(lineNumsCheck)

        let styleSectionBottom = yPos

        // --- Separator ---
        yPos -= 16
        content.addSubview(makeSeparator(y: yPos, width: w))

        // --- Texts ---
        let textSectionTop = yPos
        yPos -= 24
        let textLabel = makeLabel("Texts", bold: true, size: 12)
        textLabel.frame = NSRect(x: 16, y: yPos, width: 200, height: 18)
        content.addSubview(textLabel)

        yPos -= 28
        content.addSubview(makeFieldLabel("Title:", y: yPos))
        titleField = makeTextField(y: yPos, value: readPref("docTitle", ""))
        titleField.placeholderString = "from file (# Heading)"
        content.addSubview(titleField)

        yPos -= 28
        content.addSubview(makeFieldLabel("Super-title:", y: yPos))
        coverTopField = makeTextField(y: yPos, value: readPref("coverTop", ""))
        coverTopField.placeholderString = "from title (LECTURE 1)"
        content.addSubview(coverTopField)

        yPos -= 28
        content.addSubview(makeFieldLabel("Watermark:", y: yPos))
        wmField = makeTextField(y: yPos, value: readPref("watermark", ""))
        content.addSubview(wmField)

        yPos -= 28
        content.addSubview(makeFieldLabel("Subtitle:", y: yPos))
        subField = makeTextField(y: yPos, value: readPref("subtitle", "Tutorial"))
        content.addSubview(subField)

        yPos -= 28
        content.addSubview(makeFieldLabel("Author:", y: yPos))
        authorField = NSTextField(frame: NSRect(x: 116, y: yPos, width: 184, height: 24))
        authorField.stringValue = readPref("author", "")
        authorField.font = NSFont.systemFont(ofSize: 12)
        content.addSubview(authorField)

        authorOnCoverCheck = NSButton(checkboxWithTitle: "On cover", target: nil, action: nil)
        authorOnCoverCheck.state = readPref("authorOnCover", "yes") == "yes" ? .on : .off
        authorOnCoverCheck.font = NSFont.systemFont(ofSize: 10)
        authorOnCoverCheck.frame = NSRect(x: 306, y: yPos + 2, width: 100, height: 18)
        content.addSubview(authorOnCoverCheck)

        let textSectionBottom = yPos

        // --- Extra buttons ---
        yPos -= 36
        let folderBtn = makeSmallButton("Folder...", x: 16, y: yPos, action: #selector(pickFolder))
        content.addSubview(folderBtn)

        let coverBtn = makeSmallButton("Cover image...", x: 120, y: yPos, action: #selector(pickCoverImage))
        content.addSubview(coverBtn)

        let imgDirBtn = makeSmallButton("Image folder...", x: 224, y: yPos, action: #selector(pickImageDir))
        content.addSubview(imgDirBtn)

        // Path indicators + reset buttons
        yPos -= 16
        folderLabel = makeLabel("", size: 10, color: .secondaryLabelColor)
        folderLabel.frame = NSRect(x: 16, y: yPos, width: 86, height: 14)
        folderLabel.lineBreakMode = .byTruncatingMiddle
        content.addSubview(folderLabel)

        folderResetBtn = makeResetButton(x: 102, y: yPos, action: #selector(resetFolder))
        content.addSubview(folderResetBtn)

        coverPathLabel = makeLabel("", size: 10, color: .secondaryLabelColor)
        coverPathLabel.frame = NSRect(x: 120, y: yPos, width: 86, height: 14)
        coverPathLabel.lineBreakMode = .byTruncatingMiddle
        content.addSubview(coverPathLabel)

        coverResetBtn = makeResetButton(x: 206, y: yPos, action: #selector(resetCoverImage))
        content.addSubview(coverResetBtn)

        imgDirLabel = makeLabel("", size: 10, color: .secondaryLabelColor)
        imgDirLabel.frame = NSRect(x: 224, y: yPos, width: 86, height: 14)
        imgDirLabel.lineBreakMode = .byTruncatingMiddle
        content.addSubview(imgDirLabel)

        imgDirResetBtn = makeResetButton(x: 310, y: yPos, action: #selector(resetImageDir))
        content.addSubview(imgDirResetBtn)

        // Show persisted paths
        if !outputDir.isEmpty {
            folderLabel.stringValue = URL(fileURLWithPath: outputDir).lastPathComponent + "/"
            folderLabel.toolTip = outputDir
            folderResetBtn.isHidden = false
        }
        if !coverImagePath.isEmpty {
            coverPathLabel.stringValue = URL(fileURLWithPath: coverImagePath).lastPathComponent
            coverPathLabel.toolTip = coverImagePath
            coverResetBtn.isHidden = false
        }
        if !imageDirPath.isEmpty {
            imgDirLabel.stringValue = URL(fileURLWithPath: imageDirPath).lastPathComponent + "/"
            imgDirLabel.toolTip = imageDirPath
            imgDirResetBtn.isHidden = false
        }

        // --- OK / Cancel (fixed bottom bar) ---
        let bottomY: CGFloat = 16
        content.addSubview(makeSeparator(y: bottomY + 40, width: w))

        let cancelBtn = NSButton(frame: NSRect(x: 190, y: bottomY, width: 90, height: 30))
        cancelBtn.title = "Cancel"
        cancelBtn.bezelStyle = .rounded
        cancelBtn.keyEquivalent = "\u{1b}"
        cancelBtn.target = self
        cancelBtn.action = #selector(cancelAction)
        content.addSubview(cancelBtn)

        okButton = NSButton(frame: NSRect(x: 290, y: bottomY, width: 110, height: 30))
        okButton.title = "Create PDF"
        okButton.bezelStyle = .rounded
        okButton.keyEquivalent = "\r"
        okButton.target = self
        okButton.action = #selector(okAction)
        okButton.bezelColor = currentThemeColor
        content.addSubview(okButton)

        // --- Preview (right panel) ---
        let previewX: CGFloat = 420
        let previewY: CGFloat = 80
        let previewW: CGFloat = 200
        let previewH: CGFloat = 280

        previewHeaderLabel = makeLabel("Preview", bold: true, size: 11)
        previewHeaderLabel.frame = NSRect(x: previewX, y: previewY + previewH + 4, width: previewW, height: 16)
        previewHeaderLabel.alignment = .center
        content.addSubview(previewHeaderLabel)

        // Shadow under preview
        previewShadowView = NSView(frame: NSRect(x: previewX - 1, y: previewY - 2, width: previewW + 2, height: previewH + 3))
        let shadowView = previewShadowView!
        shadowView.wantsLayer = true
        shadowView.layer?.cornerRadius = 6
        shadowView.layer?.backgroundColor = NSColor.textBackgroundColor.cgColor
        shadowView.layer?.shadowColor = NSColor.black.cgColor
        shadowView.layer?.shadowOffset = NSSize(width: 0, height: -2)
        shadowView.layer?.shadowRadius = 8
        shadowView.layer?.shadowOpacity = 0.15
        content.addSubview(shadowView)

        // Preview
        previewImageView = NSImageView(frame: NSRect(x: previewX, y: previewY, width: previewW, height: previewH))
        previewImageView.imageScaling = .scaleProportionallyUpOrDown
        previewImageView.wantsLayer = true
        previewImageView.layer?.cornerRadius = 4
        previewImageView.layer?.masksToBounds = true
        previewImageView.layer?.backgroundColor = NSColor.textBackgroundColor.cgColor
        content.addSubview(previewImageView)

        // Loading spinner
        previewSpinner = NSProgressIndicator(frame: NSRect(
            x: previewX + (previewW - 32) / 2,
            y: previewY + (previewH - 32) / 2,
            width: 32, height: 32
        ))
        previewSpinner.style = .spinning
        previewSpinner.isDisplayedWhenStopped = false
        content.addSubview(previewSpinner)

        // Generate preview in the background
        storedFiles = files
        if !files.isEmpty {
            generatePreview(files: files)
        }

        // --- Merge panel (replaces preview when merge is on) ---
        let mergeTitle = files.count > 1 ? "Chapter titles (\(files.count))" : "Merge"
        mergeHeaderLabel = makeLabel(mergeTitle, bold: true, size: 11)
        mergeHeaderLabel.frame = NSRect(x: previewX, y: previewY + previewH + 4, width: previewW, height: 16)
        mergeHeaderLabel.alignment = .center
        mergeHeaderLabel.isHidden = true
        content.addSubview(mergeHeaderLabel)

        // Merge-option checkboxes (between scroll view and the button separator)
        let mergeCheckboxH: CGFloat = 40  // checkbox area height
        let mergeCheckY = previewY  // at the bottom of the preview area

        renumberCheck = makeCheck("Renumber ##", checked: readPref("renumber", "no") == "yes")
        renumberCheck.font = NSFont.systemFont(ofSize: 11)
        renumberCheck.frame = NSRect(x: previewX, y: mergeCheckY + 18, width: previewW, height: 16)
        renumberCheck.isHidden = true
        content.addSubview(renumberCheck)

        chapterPageCheck = makeCheck("Separator pages", checked: readPref("chapterPage", "no") == "yes")
        chapterPageCheck.font = NSFont.systemFont(ofSize: 11)
        chapterPageCheck.frame = NSRect(x: previewX, y: mergeCheckY, width: previewW, height: 16)
        chapterPageCheck.isHidden = true
        content.addSubview(chapterPageCheck)

        let mergeScrollBottom = mergeCheckY + mergeCheckboxH + 4  // above checkboxes + gap
        let mergeScrollTop = previewY + previewH  // top edge = top of preview area
        let mergeScrollH = mergeScrollTop - mergeScrollBottom
        mergeScrollView = NSScrollView(frame: NSRect(x: previewX, y: mergeScrollBottom, width: previewW, height: mergeScrollH))
        mergeScrollView.hasVerticalScroller = true
        mergeScrollView.borderType = .lineBorder
        mergeScrollView.isHidden = true
        mergeScrollView.drawsBackground = false

        content.addSubview(mergeScrollView)
        rebuildMergeList(scrollH: mergeScrollH)

        mergeCheck.target = self
        mergeCheck.action = #selector(mergeChanged)

        if mergeCheck.state == .on {
            mergeHeaderLabel.isHidden = false
            mergeScrollView.isHidden = false
            renumberCheck.isHidden = false
            chapterPageCheck.isHidden = false
            previewHeaderLabel.isHidden = true
            previewImageView.isHidden = true
            previewShadowView.isHidden = true
            previewSpinner.stopAnimation(nil)
        }

        // --- Section backgrounds ---
        let styleBoxY = styleSectionBottom - 4
        let styleBoxH = styleSectionTop - styleSectionBottom
        let styleBox = NSView(frame: NSRect(x: 8, y: styleBoxY, width: 398, height: styleBoxH))
        styleBox.wantsLayer = true
        styleBox.layer?.cornerRadius = 8
        styleBox.layer?.backgroundColor = NSColor(white: 0.5, alpha: 0.04).cgColor
        content.addSubview(styleBox, positioned: .below, relativeTo: content.subviews[0])

        let textBoxY = textSectionBottom - 4
        let textBoxH = textSectionTop - textSectionBottom
        let textBox = NSView(frame: NSRect(x: 8, y: textBoxY, width: 398, height: textBoxH))
        textBox.wantsLayer = true
        textBox.layer?.cornerRadius = 8
        textBox.layer?.backgroundColor = NSColor(white: 0.5, alpha: 0.04).cgColor
        content.addSubview(textBox, positioned: .below, relativeTo: content.subviews[0])

        window.makeKeyAndOrderFront(nil)
        app.activate(ignoringOtherApps: true)
        app.run()
        return result
    }

    // --- Theme ---

    func selectTheme(_ idx: Int) {
        selectedThemeIdx = idx
        customThemePath = ""
        jsonThemeBtn.contentTintColor = .labelColor
        jsonThemeBtn.toolTip = nil
        updateSwatchBorders()
        okButton.bezelColor = currentThemeColor
        if !storedFiles.isEmpty && !previewImageView.isHidden {
            generatePreview(files: storedFiles)
        }
    }

    func updateSwatchBorders() {
        for (idx, swatch) in themeSwatches.enumerated() {
            if idx == selectedThemeIdx {
                swatch.layer?.borderWidth = 3
                swatch.layer?.borderColor = NSColor.white.cgColor
                swatch.layer?.shadowColor = NSColor.black.cgColor
                swatch.layer?.shadowOffset = .zero
                swatch.layer?.shadowRadius = 3
                swatch.layer?.shadowOpacity = 0.4
            } else {
                swatch.layer?.borderWidth = 1
                swatch.layer?.borderColor = NSColor.separatorColor.cgColor
                swatch.layer?.shadowOpacity = 0
            }
        }
    }

    // --- Preview ---

    func generatePreview(files: [String]) {
        let firstFile = files[0]
        let theme = selectedThemeName == "custom" ? "teal" : selectedThemeName

        let execPath = ProcessInfo.processInfo.arguments[0]
        let execDir = (execPath as NSString).deletingLastPathComponent
        var resourcesDir = execDir

        let candidateScript = (execDir as NSString).appendingPathComponent("md2pdf.py")
        if !FileManager.default.fileExists(atPath: candidateScript) {
            let bundleDir = Bundle.main.bundlePath
            let altScript = ((bundleDir as NSString).appendingPathComponent("Contents/Resources") as NSString).appendingPathComponent("md2pdf.py")
            if FileManager.default.fileExists(atPath: altScript) {
                resourcesDir = (bundleDir as NSString).appendingPathComponent("Contents/Resources")
            } else {
                return
            }
        }

        let fontDir = (resourcesDir as NSString).appendingPathComponent("fonts")
        let pythonScript = (resourcesDir as NSString).appendingPathComponent("md2pdf.py")

        let fm = FileManager.default
        var pythonPath = "/usr/bin/python3"
        if !fm.isExecutableFile(atPath: pythonPath) {
            let altPaths = ["/usr/local/bin/python3", "/opt/homebrew/bin/python3"]
            pythonPath = altPaths.first(where: { fm.isExecutableFile(atPath: $0) }) ?? pythonPath
        }

        let customTheme = customThemePath
        previewSpinner.startAnimation(nil)

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let task = Process()
            task.executableURL = URL(fileURLWithPath: pythonPath)
            var args = [pythonScript, firstFile, "--font-dir", fontDir, "--theme", theme,
                        "--no-toc", "--preview"]
            if !customTheme.isEmpty {
                args += ["--custom-theme", customTheme]
            }
            task.arguments = args
            let pipe = Pipe()
            task.standardOutput = pipe
            task.standardError = FileHandle.nullDevice

            do {
                try task.run()
                task.waitUntilExit()
            } catch {
                DispatchQueue.main.async { self?.previewSpinner.stopAnimation(nil) }
                return
            }

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let output = String(data: data, encoding: .utf8) else {
                DispatchQueue.main.async { self?.previewSpinner.stopAnimation(nil) }
                return
            }

            for line in output.components(separatedBy: "\n") {
                if line.hasPrefix("PREVIEW:") {
                    let pdfPath = String(line.dropFirst("PREVIEW:".count)).trimmingCharacters(in: .whitespacesAndNewlines)
                    let pdfURL = URL(fileURLWithPath: pdfPath)
                    guard let pdfDoc = PDFDocument(url: pdfURL) else {
                        DispatchQueue.main.async { self?.previewSpinner.stopAnimation(nil) }
                        return
                    }
                    guard let page = pdfDoc.page(at: 0) else {
                        DispatchQueue.main.async { self?.previewSpinner.stopAnimation(nil) }
                        return
                    }
                    let thumb = page.thumbnail(of: NSSize(width: 400, height: 566), for: .mediaBox)

                    DispatchQueue.main.async {
                        self?.previewImageView.image = thumb
                        self?.previewSpinner.stopAnimation(nil)
                    }

                    try? FileManager.default.removeItem(at: pdfURL)
                    return
                }
            }

            DispatchQueue.main.async { self?.previewSpinner.stopAnimation(nil) }
        }
    }

    // --- UI helpers ---

    func makeLabel(_ text: String, bold: Bool = false, size: CGFloat = 12, color: NSColor = .labelColor) -> NSTextField {
        let label = NSTextField(labelWithString: text)
        label.font = bold ? NSFont.boldSystemFont(ofSize: size) : NSFont.systemFont(ofSize: size)
        label.textColor = color
        return label
    }

    func makeFieldLabel(_ text: String, y: CGFloat) -> NSTextField {
        let label = makeLabel(text, size: 12)
        label.frame = NSRect(x: 16, y: y + 2, width: 95, height: 18)
        label.alignment = .right
        return label
    }

    func makeTextField(y: CGFloat, value: String) -> NSTextField {
        let field = NSTextField(frame: NSRect(x: 116, y: y, width: 284, height: 24))
        field.stringValue = value
        field.font = NSFont.systemFont(ofSize: 12)
        return field
    }

    func makeCheck(_ title: String, checked: Bool) -> NSButton {
        let btn = NSButton(checkboxWithTitle: title, target: nil, action: nil)
        btn.state = checked ? .on : .off
        btn.font = NSFont.systemFont(ofSize: 12)
        return btn
    }

    func makeSmallButton(_ title: String, x: CGFloat, y: CGFloat, action: Selector) -> NSButton {
        let btn = NSButton(frame: NSRect(x: x, y: y, width: 100, height: 24))
        btn.title = title
        btn.bezelStyle = .rounded
        btn.font = NSFont.systemFont(ofSize: 11)
        btn.target = self
        btn.action = action
        return btn
    }

    func makeResetButton(x: CGFloat, y: CGFloat, action: Selector) -> NSButton {
        let btn = NSButton(frame: NSRect(x: x, y: y, width: 14, height: 14))
        btn.isBordered = false
        btn.title = "x"
        btn.font = NSFont.systemFont(ofSize: 12, weight: .medium)
        btn.contentTintColor = .tertiaryLabelColor
        btn.target = self
        btn.action = action
        btn.isHidden = true
        return btn
    }

    func makeSeparator(y: CGFloat, width: CGFloat) -> NSBox {
        let sep = NSBox(frame: NSRect(x: 10, y: y, width: width - 20, height: 1))
        sep.boxType = .separator
        return sep
    }

    // --- Actions ---

    @objc func swatchClicked(_ sender: NSClickGestureRecognizer) {
        guard let view = sender.view else { return }
        guard let idx = themeSwatches.firstIndex(of: view) else { return }
        selectTheme(idx)
    }

    @objc func loadCustomTheme() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.json]
        panel.title = "Choose a theme JSON file"
        if panel.runModal() == .OK, let url = panel.url {
            customThemePath = url.path
            selectedThemeIdx = -1
            jsonThemeBtn.contentTintColor = .controlAccentColor
            jsonThemeBtn.toolTip = url.lastPathComponent
            updateSwatchBorders()
            okButton.bezelColor = .controlAccentColor
            if !storedFiles.isEmpty && !previewImageView.isHidden {
                generatePreview(files: storedFiles)
            }
        }
    }

    func rebuildMergeList(scrollH: CGFloat = 0) {
        // Save current field values
        var savedTitles: [String] = []
        for f in h1TitleFields {
            savedTitles.append(f.stringValue)
        }
        h1TitleFields.removeAll()
        mergeFileLabels.removeAll()

        let files = storedFiles
        guard files.count > 0 else { return }

        let fieldW = (mergeScrollView.frame.width - 17)
        let rowH: CGFloat = 52
        let sh = scrollH > 0 ? scrollH : mergeScrollView.frame.height
        let docH = max(CGFloat(files.count) * rowH, sh)
        let docView = FlippedView(frame: NSRect(x: 0, y: 0, width: fieldW, height: docH))

        for (idx, file) in files.enumerated() {
            let filename = URL(fileURLWithPath: file).deletingPathExtension().lastPathComponent
            let rowY = CGFloat(idx) * rowH

            let label = makeLabel("\(idx + 1). \(filename)", size: 10, color: .secondaryLabelColor)
            label.frame = NSRect(x: 4, y: rowY + 2, width: fieldW - 52, height: 14)
            label.lineBreakMode = .byTruncatingTail
            docView.addSubview(label)
            mergeFileLabels.append(label)

            let field = NSTextField(frame: NSRect(x: 4, y: rowY + 18, width: fieldW - 52, height: 24))
            field.placeholderString = filename
            field.font = NSFont.systemFont(ofSize: 11)
            if idx < savedTitles.count {
                field.stringValue = savedTitles[idx]
            }
            h1TitleFields.append(field)
            docView.addSubview(field)

            // Up / Down buttons
            let btnW: CGFloat = 22
            let btnX: CGFloat = fieldW - 48

            let upBtn = NSButton(frame: NSRect(x: btnX, y: rowY + 4, width: btnW, height: 20))
            upBtn.title = "^"
            upBtn.font = NSFont.systemFont(ofSize: 9)
            upBtn.bezelStyle = .smallSquare
            upBtn.tag = idx
            upBtn.target = self
            upBtn.action = #selector(moveFileUp(_:))
            upBtn.isEnabled = idx > 0
            docView.addSubview(upBtn)

            let dnBtn = NSButton(frame: NSRect(x: btnX + btnW + 2, y: rowY + 4, width: btnW, height: 20))
            dnBtn.title = "v"
            dnBtn.font = NSFont.systemFont(ofSize: 9)
            dnBtn.bezelStyle = .smallSquare
            dnBtn.tag = idx
            dnBtn.target = self
            dnBtn.action = #selector(moveFileDown(_:))
            dnBtn.isEnabled = idx < files.count - 1
            docView.addSubview(dnBtn)
        }
        mergeScrollView.documentView = docView
    }

    @objc func moveFileUp(_ sender: NSButton) {
        let idx = sender.tag
        guard idx > 0 && idx < storedFiles.count else { return }
        // Save titles before swapping
        let titles = h1TitleFields.map { $0.stringValue }
        storedFiles.swapAt(idx, idx - 1)
        var newTitles = titles
        newTitles.swapAt(idx, idx - 1)
        // Apply
        rebuildMergeList()
        for (i, t) in newTitles.enumerated() where i < h1TitleFields.count {
            h1TitleFields[i].stringValue = t
        }
    }

    @objc func moveFileDown(_ sender: NSButton) {
        let idx = sender.tag
        guard idx >= 0 && idx < storedFiles.count - 1 else { return }
        let titles = h1TitleFields.map { $0.stringValue }
        storedFiles.swapAt(idx, idx + 1)
        var newTitles = titles
        newTitles.swapAt(idx, idx + 1)
        rebuildMergeList()
        for (i, t) in newTitles.enumerated() where i < h1TitleFields.count {
            h1TitleFields[i].stringValue = t
        }
    }

    @objc func mergeChanged() {
        let isMerge = mergeCheck.state == .on
        mergeHeaderLabel.isHidden = !isMerge
        mergeScrollView?.isHidden = !isMerge
        renumberCheck?.isHidden = !isMerge
        chapterPageCheck?.isHidden = !isMerge
        previewHeaderLabel.isHidden = isMerge
        previewImageView.isHidden = isMerge
        previewShadowView?.isHidden = isMerge
        if isMerge {
            previewSpinner.stopAnimation(nil)
        }
    }

    @objc func pickFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.title = "Output folder for PDF"
        if panel.runModal() == .OK, let url = panel.url {
            outputDir = url.path
            folderLabel.stringValue = url.lastPathComponent + "/"
            folderLabel.toolTip = url.path
            folderResetBtn.isHidden = false
        }
    }

    @objc func pickCoverImage() {
        let panel = NSOpenPanel()
        var coverTypes: [UTType] = [.png, .jpeg, .bmp]
        if let webp = UTType(filenameExtension: "webp") { coverTypes.append(webp) }
        panel.allowedContentTypes = coverTypes
        panel.title = "Cover image"
        if panel.runModal() == .OK, let url = panel.url {
            coverImagePath = url.path
            coverPathLabel.stringValue = url.lastPathComponent
            coverPathLabel.toolTip = url.path
            coverResetBtn.isHidden = false
        }
    }

    @objc func pickImageDir() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = false
        panel.title = "Image folder"
        if panel.runModal() == .OK, let url = panel.url {
            imageDirPath = url.path
            imgDirLabel.stringValue = url.lastPathComponent + "/"
            imgDirLabel.toolTip = url.path
            imgDirResetBtn.isHidden = false
        }
    }

    @objc func resetFolder() {
        outputDir = ""
        folderLabel.stringValue = ""
        folderLabel.toolTip = nil
        folderResetBtn.isHidden = true
    }

    @objc func resetCoverImage() {
        coverImagePath = ""
        coverPathLabel.stringValue = ""
        coverPathLabel.toolTip = nil
        coverResetBtn.isHidden = true
    }

    @objc func resetImageDir() {
        imageDirPath = ""
        imgDirLabel.stringValue = ""
        imgDirLabel.toolTip = nil
        imgDirResetBtn.isHidden = true
    }

    @objc func okAction() {
        let theme = selectedThemeName

        let cover = coverCheck.state == .on ? "yes" : "no"
        let toc = tocCheck.state == .on ? "yes" : "no"
        let wm = wmField.stringValue.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "|", with: " ")
        let sub = subField.stringValue.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "|", with: " ")
        let openPdf = openCheck.state == .on ? "yes" : "no"
        let author = authorField.stringValue.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "|", with: " ")
        let duplex = duplexCheck.state == .on ? "yes" : "no"
        let depthIdx = depthPopup.indexOfSelectedItem
        let tocDepthVal = depthIdx >= 0 && depthIdx < tocDepths.count ? tocDepths[depthIdx].1 : "2"
        let marginsIdx = marginsPopup.indexOfSelectedItem
        let marginsVal = marginsIdx >= 0 && marginsIdx < marginPresets.count ? marginPresets[marginsIdx].1 : "medium"
        let pageSizeIdx = pageSizePopup.indexOfSelectedItem
        let pageSizeVal = pageSizeIdx >= 0 && pageSizeIdx < pageSizes.count ? pageSizes[pageSizeIdx].1 : "a4"
        let templateIdx = templatePopup.indexOfSelectedItem
        let templateVal = templateIdx >= 0 && templateIdx < docTemplates.count ? docTemplates[templateIdx].1 : ""
        let h2BreakIdx = h2BreakPopup.indexOfSelectedItem
        let h2BreakVal = h2BreakIdx >= 0 && h2BreakIdx < h2Breaks.count ? h2Breaks[h2BreakIdx].1 : "always"
        let html = htmlCheck.state == .on ? "yes" : "no"
        let docTitle = titleField.stringValue.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "|", with: " ")
        let coverTop = coverTopField.stringValue.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "|", with: " ")
        let merge = mergeCheck.state == .on ? "yes" : "no"
        let justify = justifyCheck.state == .on ? "yes" : "no"
        let lineNumbers = lineNumsCheck.state == .on ? "yes" : "no"
        let renumber = renumberCheck.state == .on ? "yes" : "no"
        let chapterPage = chapterPageCheck.state == .on ? "yes" : "no"
        let qr = qrCheck.state == .on ? "yes" : "no"
        let copyId = copyIdCheck.state == .on ? "yes" : "no"
        let authorOnCover = authorOnCoverCheck.state == .on ? "yes" : "no"
        let patternIdx = coverPatternPopup.indexOfSelectedItem
        let coverPattern = patternIdx >= 0 && patternIdx < coverPatterns.count ? coverPatterns[patternIdx].1 : "circles"

        var h1Titles = ""
        if merge == "yes" && !h1TitleFields.isEmpty {
            let titles = h1TitleFields.map {
                $0.stringValue.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "|", with: " ")
            }
            h1Titles = titles.joined(separator: ";;;")
        }

        // Save
        writePref("theme", theme)
        writePref("cover", cover)
        writePref("toc", toc)
        writePref("watermark", wm)
        writePref("subtitle", sub)
        writePref("openPdf", openPdf)
        writePref("author", author)
        writePref("duplex", duplex)
        writePref("tocDepth", tocDepthVal)
        writePref("margins", marginsVal)
        writePref("pageSize", pageSizeVal)
        writePref("template", templateVal)
        writePref("h2Break", h2BreakVal)
        writePref("html", html)
        writePref("docTitle", docTitle)
        writePref("coverTop", coverTop)
        writePref("merge", merge)
        writePref("justify", justify)
        writePref("lineNumbers", lineNumbers)
        writePref("renumber", renumber)
        writePref("chapterPage", chapterPage)
        writePref("qr", qr)
        writePref("copyId", copyId)
        writePref("authorOnCover", authorOnCover)
        writePref("coverPattern", coverPattern)
        writePref("outputDir", outputDir)
        writePref("coverImagePath", coverImagePath)
        writePref("imageDirPath", imageDirPath)
        writePref("customThemePath", customThemePath)

        // File order (may have been changed via up/down buttons)
        let fileOrder = storedFiles.joined(separator: "<>")

        result = [theme, cover, toc, wm, sub, openPdf, outputDir, author,
                  coverImagePath, customThemePath, tocDepthVal, marginsVal, pageSizeVal,
                  templateVal, html, docTitle, coverTop, merge, h1Titles, imageDirPath,
                  duplex, h2BreakVal, justify, lineNumbers,
                  renumber, chapterPage, qr, copyId, authorOnCover, coverPattern, fileOrder].joined(separator: "|")
        NSApp.stop(nil)
    }

    @objc func cancelAction() {
        result = "CANCEL"
        NSApp.stop(nil)
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        cancelAction()
        return true
    }
}

// --- Main ---

let files = Array(CommandLine.arguments.dropFirst())
let dialog = SettingsDialog()
let result = dialog.run(files: files)
print(result)
