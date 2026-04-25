-- md2pdf Settings Dialog (unified, v4)
-- Reads saved preferences, shows single dialog, saves choices
-- Returns: theme|cover|toc|watermark|subtitle|openPdf|outputDir|author|coverImage|customThemePath|tocDepth|margins|pageSize|template|html|title|coverTop|merge
-- Empty fields = not set

property bundleId : "com.local.md2pdf"

on run argv
    try
        -- Read saved preferences (or use defaults)
        set savedTheme to readDefault("theme", "teal")
        set savedCover to readDefault("cover", "yes")
        set savedToc to readDefault("toc", "yes")
        set savedWatermark to readDefault("watermark", "")
        set savedSubtitle to readDefault("subtitle", "Tutorial")
        set savedOpenPdf to readDefault("openPdf", "yes")
        set savedOutputDir to readDefault("outputDir", "")
        set savedAuthor to readDefault("author", "")
        set savedDocTitle to readDefault("docTitle", "")
        set savedCoverTop to readDefault("coverTop", "")
        set savedDuplex to readDefault("duplex", "no")
        set savedTocDepth to readDefault("tocDepth", "2")
        set savedMargins to readDefault("margins", "medium")
        set savedPageSize to readDefault("pageSize", "a4")

        -- Build file list for preview (passed as args)
        set fileCount to count of argv
        set filePreview to ""
        if fileCount > 0 then
            repeat with i from 1 to (minimum(fileCount, 5))
                set fName to do shell script "basename " & quoted form of (item i of argv)
                set filePreview to filePreview & "  - " & fName & linefeed
            end repeat
            if fileCount > 5 then
                set filePreview to filePreview & "  ... and " & (fileCount - 5) & " more file(s)" & linefeed
            end if
        end if

        -- === SINGLE DIALOG: all settings ===

        -- Step 1: Theme selection (with custom theme option)
        set themeList to {"teal", "blue", "purple", "red", "green", "orange", "navy", "rose", "brown", "dark", "Load theme..."}
        set defaultTheme to {savedTheme}
        set chosenTheme to choose from list themeList with title "md2pdf - Settings" with prompt ("Files to convert:" & linefeed & filePreview & linefeed & "Color theme:") default items defaultTheme
        if chosenTheme is false then return "CANCEL"
        set themeName to item 1 of chosenTheme
        set customThemePath to ""

        if themeName is "Load theme..." then
            try
                set themeFile to choose file with prompt "Choose a theme JSON file:" of type {"json", "public.json"}
                set customThemePath to POSIX path of themeFile
                writeDefault("customThemePath", customThemePath)
                set themeName to "custom"
            on error
                set themeName to savedTheme
            end try
        end if

        -- Step 2: All other settings in one dialog
        set optionList to {}
        if savedCover is "yes" then
            set end of optionList to "[x] Cover"
        else
            set end of optionList to "[ ] Cover"
        end if
        if savedToc is "yes" then
            set end of optionList to "[x] Table of contents"
        else
            set end of optionList to "[ ] Table of contents"
        end if
        if savedOpenPdf is "yes" then
            set end of optionList to "[x] Open PDF after creation"
        else
            set end of optionList to "[ ] Open PDF after creation"
        end if
        if savedDuplex is "yes" then
            set end of optionList to "[x] Duplex (two-sided printing)"
        else
            set end of optionList to "[ ] Duplex (two-sided printing)"
        end if

        set chosenOptions to choose from list optionList with title "md2pdf - Options" with prompt "Choose options:" default items optionList with multiple selections allowed
        if chosenOptions is false then return "CANCEL"

        set showCover to "no"
        set showToc to "no"
        set openPdf to "no"
        set duplexMode to "no"
        repeat with opt in chosenOptions
            if opt contains "Cover" then set showCover to "yes"
            if opt contains "Table of contents" then set showToc to "yes"
            if opt contains "Open PDF" then set openPdf to "yes"
            if opt contains "Duplex" then set duplexMode to "yes"
        end repeat

        -- Step 2.5: TOC depth (only if TOC enabled)
        set tocDepth to savedTocDepth
        if showToc is "yes" then
            set depthList to {"Sections only (##)", "Subsections (###)", "Paragraphs (####)"}
            if savedTocDepth is "3" then
                set defaultDepth to {item 2 of depthList}
            else if savedTocDepth is "4" then
                set defaultDepth to {item 3 of depthList}
            else
                set defaultDepth to {item 1 of depthList}
            end if
            set chosenDepth to choose from list depthList with title "md2pdf - Table of contents" with prompt "TOC depth:" default items defaultDepth
            if chosenDepth is not false then
                set depthChoice to item 1 of chosenDepth
                if depthChoice contains "###)" then
                    set tocDepth to "3"
                else if depthChoice contains "####)" then
                    set tocDepth to "4"
                else
                    set tocDepth to "2"
                end if
            end if
        end if

        -- Step 2.7: Margins
        set marginsList to {"Narrow", "Medium", "Wide"}
        if savedMargins is "narrow" then
            set defaultMargin to {item 1 of marginsList}
        else if savedMargins is "wide" then
            set defaultMargin to {item 3 of marginsList}
        else
            set defaultMargin to {item 2 of marginsList}
        end if
        set chosenMargin to choose from list marginsList with title "md2pdf - Margins" with prompt "Margin width:" default items defaultMargin
        set marginsVal to savedMargins
        if chosenMargin is not false then
            set marginChoice to item 1 of chosenMargin
            if marginChoice is "Narrow" then
                set marginsVal to "narrow"
            else if marginChoice is "Wide" then
                set marginsVal to "wide"
            else
                set marginsVal to "medium"
            end if
        end if

        -- Step 2.8: Page size
        set pageSizeList to {"A4", "A4 landscape", "Letter", "Letter landscape", "A3", "A3 landscape"}
        set pageSizeValues to {"a4", "a4-landscape", "letter", "letter-landscape", "a3", "a3-landscape"}
        set defaultPageSize to {"A4"}
        repeat with i from 1 to count of pageSizeValues
            if item i of pageSizeValues is savedPageSize then
                set defaultPageSize to {item i of pageSizeList}
                exit repeat
            end if
        end repeat
        set chosenPageSize to choose from list pageSizeList with title "md2pdf - Page" with prompt "Page format:" default items defaultPageSize
        set pageSizeVal to savedPageSize
        if chosenPageSize is not false then
            set psChoice to item 1 of chosenPageSize
            repeat with i from 1 to count of pageSizeList
                if item i of pageSizeList is psChoice then
                    set pageSizeVal to item i of pageSizeValues
                    exit repeat
                end if
            end repeat
        end if

        -- Step 2.9: Template
        set savedTemplate to readDefault("template", "")
        set templateList to {"No template", "Lecture", "Notes", "Manual", "Report", "Cheatsheet"}
        set templateValues to {"", "lecture", "notes", "manual", "report", "cheatsheet"}
        set defaultTemplate to {"No template"}
        repeat with i from 1 to count of templateValues
            if item i of templateValues is savedTemplate then
                set defaultTemplate to {item i of templateList}
                exit repeat
            end if
        end repeat
        set chosenTemplate to choose from list templateList with title "md2pdf - Template" with prompt "Document template:" default items defaultTemplate
        set templateVal to savedTemplate
        if chosenTemplate is not false then
            set tmplChoice to item 1 of chosenTemplate
            repeat with i from 1 to count of templateList
                if item i of templateList is tmplChoice then
                    set templateVal to item i of templateValues
                    exit repeat
                end if
            end repeat
        end if

        -- Step 2.95: HTML
        set savedHtml to readDefault("html", "no")
        set htmlVal to savedHtml
        set htmlDialog to display dialog "Also create an HTML version?" buttons {"No", "Yes"} default button savedHtml
        if button returned of htmlDialog is "Yes" then
            set htmlVal to "yes"
        else
            set htmlVal to "no"
        end if

        -- Step 3: Title + CoverTop + Watermark + subtitle + author + cover image + output dir
        set promptText to "Line 1: Title (empty = from file)" & linefeed & "Line 2: Cover super-title (empty = auto)" & linefeed & "Line 3: Watermark (empty = none)" & linefeed & "Line 4: Cover subtitle" & linefeed & "Line 5: Author"
        set defaultText to savedDocTitle & linefeed & savedCoverTop & linefeed & savedWatermark & linefeed & savedSubtitle & linefeed & savedAuthor
        set dialogResult to display dialog promptText default answer defaultText with title "md2pdf - Texts" buttons {"Next to file", "Choose folder...", "Cover..."} default button "Next to file"

        set rawText to text returned of dialogResult
        set btnChoice to button returned of dialogResult

        -- Parse five lines from the text field
        set {docTitleText, coverTopText, wmText, subText, authorText} to parseFiveLines(rawText, savedDocTitle, savedCoverTop, savedWatermark, savedSubtitle, savedAuthor)

        -- Output directory / cover image
        set outputDir to ""
        set coverImage to ""
        if btnChoice is "Choose folder..." then
            try
                set chosenFolder to choose folder with prompt "Output folder for the PDF:"
                set outputDir to POSIX path of chosenFolder
            on error
                set outputDir to ""
            end try
        else if btnChoice is "Cover..." then
            try
                set imgFile to choose file with prompt "Choose an image for the cover:" of type {"public.image"}
                set coverImage to POSIX path of imgFile
                writeDefault("coverImage", coverImage)
            on error
                set coverImage to ""
            end try
        end if

        -- Save preferences
        writeDefault("theme", themeName)
        writeDefault("cover", showCover)
        writeDefault("toc", showToc)
        writeDefault("watermark", wmText)
        writeDefault("subtitle", subText)
        writeDefault("openPdf", openPdf)
        writeDefault("author", authorText)
        writeDefault("duplex", duplexMode)
        writeDefault("tocDepth", tocDepth)
        writeDefault("margins", marginsVal)
        writeDefault("pageSize", pageSizeVal)
        writeDefault("template", templateVal)
        writeDefault("html", htmlVal)
        writeDefault("docTitle", docTitleText)
        writeDefault("coverTop", coverTopText)
        if outputDir is not "" then writeDefault("outputDir", outputDir)

        -- Return result (18 fields)
        return themeName & "|" & showCover & "|" & showToc & "|" & wmText & "|" & subText & "|" & openPdf & "|" & outputDir & "|" & authorText & "|" & coverImage & "|" & customThemePath & "|" & tocDepth & "|" & marginsVal & "|" & pageSizeVal & "|" & templateVal & "|" & htmlVal & "|" & docTitleText & "|" & coverTopText & "|no"

    on error number -128
        return "CANCEL"
    end try
end run

-- Helper: read from defaults, return fallback if not set
-- Uses PlistBuddy to correctly read UTF-8 text
on readDefault(keyName, fallback)
    try
        set val to do shell script "/usr/libexec/PlistBuddy -c 'Print :" & keyName & "' \"$HOME/Library/Preferences/" & bundleId & ".plist\""
        if val is "" then return fallback
        return val
    on error
        return fallback
    end try
end readDefault

-- Helper: write to defaults
on writeDefault(keyName, val)
    try
        do shell script "defaults write " & bundleId & " " & keyName & " -string " & quoted form of val
    end try
end writeDefault

-- Helper: minimum
on minimum(a, b)
    if a < b then return a
    return b
end minimum

-- Helper: parse five-line text field (title, coverTop, watermark, subtitle, author)
on parseFiveLines(rawText, defaultTitle, defaultCoverTop, defaultWm, defaultSub, defaultAuthor)
    set oldDelims to AppleScript's text item delimiters
    set AppleScript's text item delimiters to linefeed
    set parts to text items of rawText
    set AppleScript's text item delimiters to oldDelims

    set titleText to defaultTitle
    set coverTopText to defaultCoverTop
    set wmText to defaultWm
    set subText to defaultSub
    set authorText to defaultAuthor

    if (count of parts) >= 1 then set titleText to item 1 of parts
    if (count of parts) >= 2 then set coverTopText to item 2 of parts
    if (count of parts) >= 3 then set wmText to item 3 of parts
    if (count of parts) >= 4 then set subText to item 4 of parts
    if (count of parts) >= 5 then set authorText to item 5 of parts

    set titleText to trimText(titleText)
    set coverTopText to trimText(coverTopText)
    set wmText to trimText(wmText)
    set subText to trimText(subText)
    set authorText to trimText(authorText)

    return {titleText, coverTopText, wmText, subText, authorText}
end parseFiveLines

-- Helper: trim whitespace
on trimText(str)
    if str is "" then return str
    set str to do shell script "echo " & quoted form of str & " | xargs"
    return str
end trimText
