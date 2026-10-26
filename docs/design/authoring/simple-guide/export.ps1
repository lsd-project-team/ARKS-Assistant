param([ValidateSet('all','tu','correction')][string]$Book = 'all')
$ErrorActionPreference = 'Stop'
$designRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$books = @(
    @{Id='tu'; Folder='transport-unit/v8.2'; Stem='TransportUnit设计文档'},
    @{Id='correction'; Folder='correction-process/v4.2'; Stem='纠偏过程设计文档'}
)
$wordApp=$null
$ownsInstance=$false
try {
    # 只操作本次独立隐藏Word实例，避免接管用户已打开的文档。
    $wordApp = New-Object -ComObject Word.Application
    $ownsInstance = ($wordApp.Documents.Count -eq 0)
    if (-not $ownsInstance) {throw 'Word automation instance already contains documents.'}
    $wordApp.Visible=$false
    $wordApp.DisplayAlerts=0
    foreach ($spec in $books) {
        if ($Book -ne 'all' -and $Book -ne $spec.Id) {continue}
        $publicationDoc=$null
        $docxPath=Join-Path $designRoot ($spec.Folder+'/'+$spec.Stem+'.docx')
        $pdfPath=Join-Path $designRoot ($spec.Folder+'/'+$spec.Stem+'.pdf')
        try {
            $publicationDoc=$wordApp.Documents.Open($docxPath,$false,$false)
            foreach ($styleId in @(-1,-2,-63,-75,-20,-32,-33,-35)) {
                $style=$publicationDoc.Styles.Item([int]$styleId)
                $style.AutomaticallyUpdate=$false
                $style.Font.Name='Microsoft YaHei'
                $style.Font.NameFarEast='Microsoft YaHei'
                $style.Font.NameAscii='Microsoft YaHei'
                $style.Font.NameOther='Microsoft YaHei'
                $style.Font.Color=0
            }
            $tocStyle=$publicationDoc.Styles.Item(-20)
            $tocStyle.Font.Size=12.5
            $tocStyle.Font.Bold=0
            $tocStyle.ParagraphFormat.FirstLineIndent=0
            $tocStyle.ParagraphFormat.SpaceAfter=0
            $tocStyle.ParagraphFormat.LineSpacingRule=4
            $tocStyle.ParagraphFormat.LineSpacing=25
            $tocStyle.ParagraphFormat.KeepWithNext=0
            $publicationDoc.EmbedTrueTypeFonts=$true
            $publicationDoc.SaveSubsetFonts=$true
            $publicationDoc.Fields.Update() | Out-Null
            foreach ($toc in $publicationDoc.TablesOfContents) {$toc.Update()}
            $publicationDoc.Repaginate()
            foreach ($toc in $publicationDoc.TablesOfContents) {
                $toc.UpdatePageNumbers()
                $toc.Range.Font.Name='Microsoft YaHei'
                $toc.Range.Font.NameFarEast='Microsoft YaHei'
                $toc.Range.Font.NameAscii='Microsoft YaHei'
                $toc.Range.Font.NameOther='Microsoft YaHei'
                $toc.Range.Font.Size=12.5
                $toc.Range.Font.Bold=0
                $toc.Range.ParagraphFormat.KeepWithNext=0
                $toc.Range.ParagraphFormat.LineSpacingRule=4
                $toc.Range.ParagraphFormat.LineSpacing=25
            }
            $publicationDoc.Repaginate()
            $pages=$publicationDoc.ComputeStatistics(2)
            $publicationDoc.Save()
            $publicationDoc.ExportAsFixedFormat($pdfPath,17,$false,0,0,1,9999,0,$true,$true,1,$true,$true,$true)
            Write-Output "$($spec.Id): Word/PDF exported, pages=$pages"
        } finally {
            if ($null -ne $publicationDoc) {
                $publicationDoc.Close(0)
                [void][Runtime.InteropServices.Marshal]::ReleaseComObject($publicationDoc)
            }
        }
    }
} finally {
    if ($null -ne $wordApp) {
        if ($ownsInstance) {$wordApp.Quit()}
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp)
    }
}
