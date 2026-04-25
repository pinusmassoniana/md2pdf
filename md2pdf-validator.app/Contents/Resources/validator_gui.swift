// md2pdf-validator — PDF authorship verification window (native Cocoa)
// Compile: swiftc -o validator_gui validator_gui.swift -framework Cocoa
// Usage: ./validator_gui 'JSON_DATA' '/path/to/file.pdf'
// Output (stdout): paths of .md files separated by ;;; (for --verify) or CLOSE

import Cocoa

// --- Application ---

class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    var result = "CLOSE"

    // Data extracted from JSON
    var pdfPath = ""
    var fileLabel: NSTextField!
    var uuidValue: NSTextField!
    var hashField: NSTextField!
    var authorValue: NSTextField!
    var stegoValue: NSTextField!
    var fpValue: NSTextField!

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Parse arguments
        let args = CommandLine.arguments
        guard args.count >= 3 else {
            print("CLOSE")
            NSApp.terminate(nil)
            return
        }
        let jsonStr = args[1]
        pdfPath = args[2]

        // Parse JSON
        var uuid = ""
        var hash = ""
        var author = ""
        var stego: [String] = []
        var stegoCount = 0
        var fingerprint = false
        var fileName = (pdfPath as NSString).lastPathComponent

        if let data = jsonStr.data(using: .utf8),
           let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            uuid = obj["uuid"] as? String ?? ""
            hash = obj["hash"] as? String ?? ""
            author = obj["author"] as? String ?? ""
            fileName = obj["file"] as? String ?? fileName
            stegoCount = obj["stego_count"] as? Int ?? 0
            fingerprint = obj["fingerprint"] as? Bool ?? false
            if let s = obj["stego"] as? [String] { stego = s }
        }

        // --- Window ---
        let w: CGFloat = 500
        let h: CGFloat = 340
        let screen = NSScreen.main!.frame
        let x = (screen.width - w) / 2
        let y = (screen.height - h) / 2

        window = NSWindow(
            contentRect: NSRect(x: x, y: y, width: w, height: h),
            styleMask: [.titled, .closable],
            backing: .buffered, defer: false
        )
        window.title = "md2pdf — Authorship verification"
        window.delegate = self
        window.isReleasedWhenClosed = false

        let content = NSView(frame: NSRect(x: 0, y: 0, width: w, height: h))
        window.contentView = content

        var yPos: CGFloat = h - 40
        let labelX: CGFloat = 20
        let valueX: CGFloat = 150
        let _ = 120 as CGFloat  // labelW unused
        let valueW: CGFloat = w - valueX - 20
        let rowH: CGFloat = 24

        // --- File name ---
        let fnLabel = makeLabel("File: " + fileName, bold: true, size: 13)
        fnLabel.frame = NSRect(x: labelX, y: yPos, width: w - 40, height: 22)
        content.addSubview(fnLabel)

        yPos -= 12
        let sep1 = makeSeparator(y: yPos, width: w)
        content.addSubview(sep1)

        // --- Data rows ---
        yPos -= rowH + 4

        // UUID
        content.addSubview(makeFieldLabel("Copy UUID", y: yPos))
        uuidValue = makeValueField(uuid.isEmpty ? "-" : uuid, y: yPos, x: valueX, w: valueW)
        if uuid.isEmpty { uuidValue.textColor = .secondaryLabelColor }
        content.addSubview(uuidValue)

        yPos -= rowH

        // SHA-256
        content.addSubview(makeFieldLabel("SHA-256", y: yPos))
        let hashDisplay = hash.isEmpty ? "-" : String(hash.dropFirst("sha256:".count).prefix(32)) + "..."
        hashField = makeValueField(hash.isEmpty ? "-" : hashDisplay, y: yPos, x: valueX, w: valueW)
        hashField.toolTip = hash
        if hash.isEmpty { hashField.textColor = .secondaryLabelColor }
        content.addSubview(hashField)

        yPos -= rowH

        // Author (metadata)
        content.addSubview(makeFieldLabel("Author (meta)", y: yPos))
        authorValue = makeValueField(author.isEmpty ? "-" : author, y: yPos, x: valueX, w: valueW)
        if author.isEmpty { authorValue.textColor = .secondaryLabelColor }
        content.addSubview(authorValue)

        yPos -= rowH

        // Steganography
        content.addSubview(makeFieldLabel("Steganography", y: yPos))
        let stegoText: String
        let stegoColor: NSColor
        if stegoCount > 0 {
            let uniqueAuthor = stego.first ?? ""
            stegoText = "OK  Found (\(stegoCount) image(s)) - \(uniqueAuthor)"
            stegoColor = .systemGreen
        } else {
            stegoText = "X  Not found"
            stegoColor = .systemRed
        }
        stegoValue = makeValueField(stegoText, y: yPos, x: valueX, w: valueW)
        stegoValue.textColor = stegoColor
        content.addSubview(stegoValue)

        yPos -= rowH

        // Fingerprint
        content.addSubview(makeFieldLabel("Fingerprint", y: yPos))
        let fpText = fingerprint ? "OK  Present" : "X  Not found"
        let fpColor: NSColor = fingerprint ? .systemGreen : .systemRed
        fpValue = makeValueField(fpText, y: yPos, x: valueX, w: valueW)
        fpValue.textColor = fpColor
        content.addSubview(fpValue)

        yPos -= 16
        let sep2 = makeSeparator(y: yPos, width: w)
        content.addSubview(sep2)

        // --- Buttons ---
        yPos -= 40

        let closeBtn = NSButton(frame: NSRect(x: w - 110, y: yPos, width: 90, height: 32))
        closeBtn.title = "Close"
        closeBtn.bezelStyle = .rounded
        closeBtn.target = self
        closeBtn.action = #selector(closeAction)
        closeBtn.keyEquivalent = "\u{1b}"  // Escape
        content.addSubview(closeBtn)

        let verifyBtn = NSButton(frame: NSRect(x: w - 260, y: yPos, width: 140, height: 32))
        verifyBtn.title = "Verify hash..."
        verifyBtn.bezelStyle = .rounded
        verifyBtn.target = self
        verifyBtn.action = #selector(verifyAction)
        verifyBtn.keyEquivalent = "\r"  // Enter
        if hash.isEmpty {
            verifyBtn.isEnabled = false
            verifyBtn.toolTip = "PDF does not contain a SHA-256 hash"
        }
        content.addSubview(verifyBtn)

        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    // --- Actions ---

    @objc func verifyAction() {
        let panel = NSOpenPanel()
        panel.title = "Choose source .md files"
        panel.allowsMultipleSelection = true
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        if #available(macOS 11.0, *) {
            panel.allowedContentTypes = [.init(filenameExtension: "md")!]
        } else {
            panel.allowedFileTypes = ["md"]
        }
        let resp = panel.runModal()
        if resp == .OK && !panel.urls.isEmpty {
            let paths = panel.urls.map { $0.path }
            result = paths.joined(separator: ";;;")
            print(result)
            NSApp.stop(nil)
        }
    }

    @objc func closeAction() {
        result = "CLOSE"
        print(result)
        NSApp.stop(nil)
    }

    func windowWillClose(_ notification: Notification) {
        closeAction()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    // --- UI helpers ---

    func makeLabel(_ text: String, bold: Bool = false, size: CGFloat = 12, color: NSColor = .labelColor) -> NSTextField {
        let f = NSTextField(labelWithString: text)
        f.font = bold ? NSFont.boldSystemFont(ofSize: size) : NSFont.systemFont(ofSize: size)
        f.textColor = color
        f.isEditable = false
        f.isBordered = false
        f.drawsBackground = false
        return f
    }

    func makeFieldLabel(_ text: String, y: CGFloat) -> NSTextField {
        let f = makeLabel(text, bold: false, size: 11, color: .secondaryLabelColor)
        f.frame = NSRect(x: 20, y: y, width: 120, height: 18)
        f.alignment = .right
        return f
    }

    func makeValueField(_ text: String, y: CGFloat, x: CGFloat, w: CGFloat) -> NSTextField {
        let f = NSTextField(labelWithString: text)
        f.frame = NSRect(x: x, y: y, width: w, height: 18)
        f.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        f.isEditable = false
        f.isSelectable = true
        f.isBordered = false
        f.drawsBackground = false
        f.lineBreakMode = .byTruncatingTail
        return f
    }

    func makeSeparator(y: CGFloat, width: CGFloat) -> NSBox {
        let box = NSBox(frame: NSRect(x: 10, y: y, width: width - 20, height: 1))
        box.boxType = .separator
        return box
    }
}

// --- Main ---

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
