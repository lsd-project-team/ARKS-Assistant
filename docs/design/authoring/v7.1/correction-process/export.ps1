$ErrorActionPreference = 'Stop'
$stagingBook = (Resolve-Path (Join-Path $PSScriptRoot '../../../../../output/design-publication-v7.1/correction-process')).Path
$documentPath = Join-Path $stagingBook '纠偏过程设计文档.docx'
$pdfPath = Join-Path $stagingBook '纠偏过程设计文档.pdf'
$wordApp = $null
$publicationDoc = $null
$ownedEmptyInstance = $false
function Set-BookTocFont($book) {
    foreach ($bookToc in $book.TablesOfContents) {
        $bookToc.Range.Paragraphs.Item(1).Range.Style=$book.Styles.Item(-20)
        $bookToc.Range.Font.Name='Microsoft YaHei'
        $bookToc.Range.Font.NameFarEast='Microsoft YaHei'
        $bookToc.Range.Font.NameAscii='Microsoft YaHei'
        $bookToc.Range.Font.NameOther='Microsoft YaHei'
        foreach ($bookTocParagraph in $bookToc.Range.Paragraphs) {
            $bookTocParagraph.Range.ParagraphFormat.FirstLineIndent=0
            $bookTocParagraph.Range.Font.Size=10.5
            $bookTocParagraph.Range.Font.Bold=0
            $bookTocParagraph.Range.ParagraphFormat.KeepWithNext=0
            if ($bookTocParagraph.Range.Style.NameLocal -eq $book.Styles.Item(-20).NameLocal) {
                $bookTocParagraph.Range.Font.Size=11
                $bookTocParagraph.Range.Font.Bold=1
                $bookTocParagraph.Range.ParagraphFormat.KeepWithNext=-1
            }
        }
        # The field-opening paragraph can retain Normal's classification even
        # after Word assigns the TOC style; format its visible first entry too.
        $bookToc.Range.Paragraphs.Item(1).Range.Font.Size=11
        $bookToc.Range.Paragraphs.Item(1).Range.Font.Bold=-1
    }
}
try {
    $wordApp = New-Object -ComObject Word.Application
    $ownedEmptyInstance = ($wordApp.Documents.Count -eq 0)
    if (-not $ownedEmptyInstance) { throw 'Automation instance contains other documents; refusing to change them.' }
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $publicationDoc = $wordApp.Documents.Open($documentPath, $false, $false)
    # Use built-in IDs, independent of the local Word UI language.
    foreach ($spec in @(@(-2,18.5,1),@(-3,13,1),@(-4,11.5,1),@(-63,27,1),@(-75,12,0),@(-20,11,1),@(-21,10.5,0))) {
        $bookStyle=$publicationDoc.Styles.Item([int]$spec[0])
        $bookStyle.AutomaticallyUpdate=$false
        $bookStyle.Font.Name='Microsoft YaHei'
        $bookStyle.Font.NameFarEast='Microsoft YaHei'
        $bookStyle.Font.NameAscii='Microsoft YaHei'
        $bookStyle.Font.NameOther='Microsoft YaHei'
        $bookStyle.Font.Size=[double]$spec[1]
        $bookStyle.Font.Bold=[int]$spec[2]
        $bookStyle.Font.Color=0
    }
    # Cover subtitles must not inherit Normal's two-character first-line indent.
    foreach ($coverStyleId in @(-63,-75)) {
        $coverStyle=$publicationDoc.Styles.Item($coverStyleId)
        $coverStyle.ParagraphFormat.FirstLineIndent=0
        $coverStyle.ParagraphFormat.LeftIndent=0
        $coverStyle.ParagraphFormat.Alignment=0
    }
    foreach ($tocStyleId in @(-20,-21)) {
        $tocStyle=$publicationDoc.Styles.Item($tocStyleId)
        $tocStyle.ParagraphFormat.FirstLineIndent=0
        $tocStyle.ParagraphFormat.LeftIndent=0
        if ($tocStyleId -eq -21) {$tocStyle.ParagraphFormat.LeftIndent=18}
        $tocStyle.ParagraphFormat.SpaceBefore=0
        $tocStyle.ParagraphFormat.SpaceAfter=1
        if ($tocStyleId -eq -20) {$tocStyle.ParagraphFormat.SpaceAfter=5}
        $tocStyle.ParagraphFormat.LineSpacingRule=4
        $tocStyle.ParagraphFormat.LineSpacing=18
    }
    $publicationDoc.EmbedTrueTypeFonts = $true
    $publicationDoc.SaveSubsetFonts = $true
    $publicationDoc.Fields.Update() | Out-Null
    foreach ($toc in $publicationDoc.TablesOfContents) { $toc.Update() }
    Set-BookTocFont $publicationDoc
    $publicationDoc.Repaginate()
    $publicationDoc.Fields.Update() | Out-Null
    Set-BookTocFont $publicationDoc
    $publicationDoc.Repaginate()
    foreach ($toc in $publicationDoc.TablesOfContents) { $toc.UpdatePageNumbers() }
    Set-BookTocFont $publicationDoc
    $publicationDoc.Repaginate()
    $pages = $publicationDoc.ComputeStatistics(2)
    $publicationDoc.Save()
    # Native PDF export includes heading bookmarks and accessibility tags.
    $publicationDoc.ExportAsFixedFormat($pdfPath,17,$false,0,0,1,9999,0,$true,$true,1,$true,$true,$true)
    Write-Output "Word export succeeded: pages=$pages; toc=$($publicationDoc.TablesOfContents.Count)"
} finally {
    if ($null -ne $publicationDoc) { $publicationDoc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($publicationDoc) }
    if ($null -ne $wordApp) {
        if ($ownedEmptyInstance) { $wordApp.Quit() }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp)
    }
}
