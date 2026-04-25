// doc2md — settings dialog (native Cocoa)
// Compile: swiftc -o settings_gui settings_gui.swift -framework Cocoa
// Usage: ./settings_gui [file1.pdf file2.docx ...]
// Output: outputDir|imageDir|extractImages|force|openResult

import Cocoa

let bundleId = "com.local.doc2md"

// --- Preferences ---

func readPref(_ key: String, _ fallback: String = "") -> String {
    UserDefaults.standard.addSuite(named: bundleId)
    let val = UserDefaults(suiteName: bundleId)?.string(forKey: key) ?? ""
    return val.isEmpty ? fallback : val
}

func writePref(_ key: String, _ val: String) {
    UserDefaults(suiteName: bundleId)?.set(val, forKey: key)
}

// --- Dialog ---

class SettingsDialog: NSObject, NSWindowDelegate {
    var window: NSWindow!
    var result = "CANCEL"

    // Controls
    var extractImagesCheck: NSButton!
    var forceCheck: NSButton!
    var openResultCheck: NSButton!
    var imageDirField: NSTextField!
    var folderLabel: NSTextField!

    var outputDir = ""

    func run(files: [String]) -> String {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)

        let w: CGFloat = 480
        let h: CGFloat = 340
        let screen = NSScreen.main!.frame
        let x = (screen.width - w) / 2
        let y = (screen.height - h) / 2

        window = NSWindow(
            contentRect: NSRect(x: x, y: y, width: w, height: h),
            styleMask: [.titled, .closable],
            backing: .buffered, defer: false
        )
        window.title = "doc2md - Settings"
        window.delegate = self
        window.isReleasedWhenClosed = false

        let content = window.contentView!
        content.wantsLayer = true
        var yPos = h - 10

        // --- Files ---
        if !files.isEmpty {
            yPos -= 16
            let label = makeLabel("Files:", bold: true)
            label.frame = NSRect(x: 16, y: yPos, width: 440, height: 18)
            content.addSubview(label)

            let names = files.prefix(5).map { (URL(fileURLWithPath: $0).lastPathComponent) }
            var fileText = names.joined(separator: ", ")
            if files.count > 5 { fileText += " ... and \(files.count - 5) more" }
            yPos -= 18
            let fLabel = makeLabel(fileText, size: 11, color: .secondaryLabelColor)
            fLabel.frame = NSRect(x: 16, y: yPos, width: 440, height: 18)
            fLabel.lineBreakMode = .byTruncatingTail
            content.addSubview(fLabel)
            yPos -= 8
        }

        // --- Separator ---
        yPos -= 8
        content.addSubview(makeSeparator(y: yPos, width: w))

        // --- Options ---
        yPos -= 24
        let optLabel = makeLabel("Conversion options", bold: true, size: 12)
        optLabel.frame = NSRect(x: 16, y: yPos, width: 200, height: 18)
        content.addSubview(optLabel)

        yPos -= 28
        extractImagesCheck = makeCheck("Extract images", checked: readPref("extractImages", "yes") == "yes")
        extractImagesCheck.frame = NSRect(x: 16, y: yPos, width: 220, height: 20)
        content.addSubview(extractImagesCheck)

        yPos -= 24
        forceCheck = makeCheck("Overwrite existing .md", checked: readPref("force", "yes") == "yes")
        forceCheck.frame = NSRect(x: 16, y: yPos, width: 280, height: 20)
        content.addSubview(forceCheck)

        yPos -= 24
        openResultCheck = makeCheck("Open result after conversion", checked: readPref("openResult", "yes") == "yes")
        openResultCheck.frame = NSRect(x: 16, y: yPos, width: 300, height: 20)
        content.addSubview(openResultCheck)

        // --- Image folder ---
        yPos -= 34
        let imgLabel = makeLabel("Image folder:", size: 12)
        imgLabel.frame = NSRect(x: 16, y: yPos + 2, width: 170, height: 18)
        content.addSubview(imgLabel)

        imageDirField = NSTextField(frame: NSRect(x: 190, y: yPos, width: 200, height: 24))
        imageDirField.stringValue = readPref("imageDir", "images")
        imageDirField.placeholderString = "images"
        imageDirField.font = NSFont.systemFont(ofSize: 12)
        content.addSubview(imageDirField)

        // --- Separator ---
        yPos -= 24
        content.addSubview(makeSeparator(y: yPos, width: w))

        // --- Output folder ---
        yPos -= 30
        let folderBtn = NSButton(frame: NSRect(x: 16, y: yPos, width: 200, height: 24))
        folderBtn.title = "Output folder..."
        folderBtn.bezelStyle = .rounded
        folderBtn.font = NSFont.systemFont(ofSize: 11)
        folderBtn.target = self
        folderBtn.action = #selector(pickFolder)
        content.addSubview(folderBtn)

        folderLabel = makeLabel("Next to the source file", size: 11, color: .secondaryLabelColor)
        folderLabel.frame = NSRect(x: 224, y: yPos + 2, width: 240, height: 18)
        content.addSubview(folderLabel)

        // --- OK / Cancel ---
        let bottomY: CGFloat = 16
        content.addSubview(makeSeparator(y: bottomY + 40, width: w))

        let cancelBtn = NSButton(frame: NSRect(x: w - 250, y: bottomY, width: 90, height: 30))
        cancelBtn.title = "Cancel"
        cancelBtn.bezelStyle = .rounded
        cancelBtn.keyEquivalent = "\u{1b}"
        cancelBtn.target = self
        cancelBtn.action = #selector(cancelAction)
        content.addSubview(cancelBtn)

        let okBtn = NSButton(frame: NSRect(x: w - 150, y: bottomY, width: 130, height: 30))
        okBtn.title = "Convert"
        okBtn.bezelStyle = .rounded
        okBtn.keyEquivalent = "\r"
        okBtn.target = self
        okBtn.action = #selector(okAction)
        content.addSubview(okBtn)

        window.makeKeyAndOrderFront(nil)
        app.activate(ignoringOtherApps: true)
        app.run()
        return result
    }

    // --- UI helpers ---

    func makeLabel(_ text: String, bold: Bool = false, size: CGFloat = 12, color: NSColor = .labelColor) -> NSTextField {
        let label = NSTextField(labelWithString: text)
        label.font = bold ? NSFont.boldSystemFont(ofSize: size) : NSFont.systemFont(ofSize: size)
        label.textColor = color
        return label
    }

    func makeCheck(_ title: String, checked: Bool) -> NSButton {
        let btn = NSButton(checkboxWithTitle: title, target: nil, action: nil)
        btn.state = checked ? .on : .off
        btn.font = NSFont.systemFont(ofSize: 12)
        return btn
    }

    func makeSeparator(y: CGFloat, width: CGFloat) -> NSBox {
        let sep = NSBox(frame: NSRect(x: 10, y: y, width: width - 20, height: 1))
        sep.boxType = .separator
        return sep
    }

    // --- Actions ---

    @objc func pickFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.title = "Output folder for Markdown"
        if panel.runModal() == .OK, let url = panel.url {
            outputDir = url.path
            folderLabel.stringValue = "-> \(url.lastPathComponent)/"
        }
    }

    @objc func okAction() {
        let imageDir = imageDirField.stringValue.trimmingCharacters(in: .whitespaces)
        let extractImages = extractImagesCheck.state == .on ? "yes" : "no"
        let force = forceCheck.state == .on ? "yes" : "no"
        let openResult = openResultCheck.state == .on ? "yes" : "no"

        // Save preferences
        writePref("imageDir", imageDir)
        writePref("extractImages", extractImages)
        writePref("force", force)
        writePref("openResult", openResult)

        // outputDir|imageDir|extractImages|force|openResult
        result = [outputDir, imageDir, extractImages, force, openResult].joined(separator: "|")
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
