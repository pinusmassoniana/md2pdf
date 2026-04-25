-- doc2md Settings Dialog (AppleScript fallback)
-- Returns: outputDir|imageDir|extractImages|force|openResult

property bundleId : "com.local.doc2md"

on run argv
    try
        -- Read saved preferences
        set savedImageDir to readDefault("imageDir", "images")
        set savedExtract to readDefault("extractImages", "yes")
        set savedForce to readDefault("force", "yes")
        set savedOpenResult to readDefault("openResult", "yes")

        -- Build file list
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

        -- Step 1: Options checkboxes
        set optionList to {}
        if savedExtract is "yes" then
            set end of optionList to "[x] Extract images"
        else
            set end of optionList to "[ ] Extract images"
        end if
        if savedForce is "yes" then
            set end of optionList to "[x] Overwrite existing .md"
        else
            set end of optionList to "[ ] Overwrite existing .md"
        end if
        if savedOpenResult is "yes" then
            set end of optionList to "[x] Open result"
        else
            set end of optionList to "[ ] Open result"
        end if

        set chosenOptions to choose from list optionList with title "doc2md - Settings" with prompt ("Files to convert:" & linefeed & filePreview & linefeed & "Options:") default items optionList with multiple selections allowed
        if chosenOptions is false then return "CANCEL"

        set extractImages to "no"
        set forceOverwrite to "no"
        set openResult to "no"
        repeat with opt in chosenOptions
            if opt contains "Extract" then set extractImages to "yes"
            if opt contains "Overwrite" then set forceOverwrite to "yes"
            if opt contains "Open" then set openResult to "yes"
        end repeat

        -- Step 2: Image directory name
        set imgDirResult to display dialog "Image folder (relative to the source file):" default answer savedImageDir with title "doc2md - Images" buttons {"Cancel", "OK"} default button "OK"
        if button returned of imgDirResult is "Cancel" then return "CANCEL"
        set imageDir to text returned of imgDirResult

        -- Step 3: Output folder
        set outputDir to ""
        set folderChoice to display dialog "Where should Markdown be saved?" with title "doc2md - Folder" buttons {"Cancel", "Next to file", "Choose folder..."} default button "Next to file"
        if button returned of folderChoice is "Cancel" then return "CANCEL"
        if button returned of folderChoice is "Choose folder..." then
            try
                set chosenFolder to choose folder with prompt "Output folder for Markdown:"
                set outputDir to POSIX path of chosenFolder
            on error
                set outputDir to ""
            end try
        end if

        -- Save preferences
        writeDefault("imageDir", imageDir)
        writeDefault("extractImages", extractImages)
        writeDefault("force", forceOverwrite)
        writeDefault("openResult", openResult)

        -- Return: outputDir|imageDir|extractImages|force|openResult
        return outputDir & "|" & imageDir & "|" & extractImages & "|" & forceOverwrite & "|" & openResult

    on error number -128
        return "CANCEL"
    end try
end run

on readDefault(keyName, fallback)
    try
        set val to do shell script "/usr/libexec/PlistBuddy -c 'Print :" & keyName & "' \"$HOME/Library/Preferences/" & bundleId & ".plist\""
        if val is "" then return fallback
        return val
    on error
        return fallback
    end try
end readDefault

on writeDefault(keyName, val)
    try
        do shell script "defaults write " & bundleId & " " & keyName & " -string " & quoted form of val
    end try
end writeDefault

on minimum(a, b)
    if a < b then return a
    return b
end minimum
